from contextlib import closing
from gettext import gettext as _
from StringIO import StringIO
from tempfile import mkdtemp
from time import time
from urlparse import urlparse, urljoin
import json
import logging
import os
import shutil
import tarfile

from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest
from pulp.plugins.util import publish_step
from pulp.plugins.util.nectar_config import importer_config_to_nectar_config
from pulp.server.controllers import repository as repo_controller

from pulp_puppet.common import constants
from pulp_puppet.common.sync_progress import SyncProgressReport
from pulp_puppet.plugins.db.models import Module


_logger = logging.getLogger(__name__)


URL_TO_DOWNLOADER = {
    'http': HTTPThreadedDownloader,
    'https': HTTPThreadedDownloader,
    'file': LocalFileDownloader,
}

FETCH_SUCCEEDED = _('Fetched URL: %(url)s destination: %(dst)s')
FETCH_FAILED = _('Fetch URL: %(url)s failed: %(msg)s')
IMPORT_MODULE = _('Importing module: %(mod)s')


class SynchronizeWithDirectory(object):
    """
    A callable object used to synchronize with a directory of packaged puppet modules.
    The source of the import is a directory containing a PULP_MANIFEST and
    multiple puppet built puppet modules.

    :ivar repo: A Pulp repository object
    :type repo: pulp.plugins.model.Repository
    :ivar conduit: Provides access to relevant Pulp functionality.
    :type conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit
    :ivar config: Plugin configuration.
    :type config: pulp.plugins.config.PluginCallConfiguration
    :ivar report: An import report.
    :type report: SyncProgressReport
    :ivar canceled: The operation canceled flag.
    :type canceled: bool
    :ivar tmp_dir: The path to the temporary directory used to download files.
    :type tmp_dir: str
    """

    @staticmethod
    def _extract_metadata(module_path):
        """
        Extract the puppet module metadata from the tarball at the specified path.
        Search the tarball content for a file named: */metadata.json and extract
        it into temporary directory. Then read the file and return the json decoded content.

        :param module_path: The fully qualified path to the module.
        :type module_path: str

        :return: The puppet module metadata.
        :rtype: dict
        """
        tmp_dir = mkdtemp(dir=os.path.dirname(module_path))
        try:
            with closing(tarfile.open(module_path)) as tarball:
                for member in tarball.getmembers():
                    path = member.name.split('/')
                    if path[-1] == constants.MODULE_METADATA_FILENAME:
                        tarball.extract(member, tmp_dir)
                        with open(os.path.join(tmp_dir, member.name)) as fp:
                            return json.load(fp)
        finally:
            shutil.rmtree(tmp_dir)

    def __init__(self, repo, conduit, config):
        """
        :param repo: A Pulp repository object
        :type repo: pulp.plugins.model.Repository
        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config: Plugin configuration.
        :type config: pulp.plugins.config.PluginCallConfiguration
        """
        self.repo = repo
        self.conduit = conduit
        self.config = config
        self.report = None
        self.canceled = False
        self.tmp_dir = None

    def feed_url(self):
        """
        Get the feed URL from the configuration and ensure it has a trailing '/' so urljoin will
        work correctly.

        :return: The feed URL.
        :rtype: str
        """
        url = self.config.get(constants.CONFIG_FEED)
        if not url.endswith('/'):
            url += '/'
        return url

    def cancel(self):
        """
        Cancel puppet module import.
        """
        self.canceled = True

    def _download(self, urls):
        """
        Download files by URL.

        Encapsulates nectar details and provides a simplified method of downloading files.

        :param urls: A list of tuples: (url, destination).  The *url* and *destination* are both
                     strings.  The *destination* is the fully qualified path to where the file is
                     to be downloaded.
        :type urls: list

        :return: The nectar reports.  Tuple of: (succeeded_reports, failed_reports)
        :rtype: tuple
        """
        feed_url = self.feed_url()
        nectar_config = importer_config_to_nectar_config(self.config.flatten())
        nectar_class = URL_TO_DOWNLOADER[urlparse(feed_url).scheme]
        downloader = nectar_class(nectar_config)
        listener = DownloadListener(self, downloader)

        request_list = []
        for url, destination in urls:
            request_list.append(DownloadRequest(url, destination))
        downloader.download(request_list)
        nectar_config.finalize()

        for report in listener.succeeded_reports:
            _logger.info(FETCH_SUCCEEDED, dict(url=report.url, dst=report.destination))
        for report in listener.failed_reports:
            _logger.error(FETCH_FAILED, dict(url=report.url, msg=report.error_msg))

        return listener.succeeded_reports, listener.failed_reports

    def _fetch_manifest(self):
        """
        Fetch the PULP_MANIFEST.

        After the manifest is fetched, the file is parsed into a list of tuples.

        :return: The manifest content.  List of: (name,checksum,size).
        :rtype: list
        """
        started = time()

        # report progress: started
        self.report.metadata_state = constants.STATE_RUNNING
        self.report.metadata_query_total_count = 1
        self.report.metadata_query_finished_count = 0
        self.report.update_progress()

        # download manifest
        destination = StringIO()
        feed_url = self.feed_url()
        url = urljoin(feed_url, constants.MANIFEST_FILENAME)
        succeeded_reports, failed_reports = self._download([(url, destination)])

        # report download failed
        if failed_reports:
            report = failed_reports[0]
            self.report.metadata_state = constants.STATE_FAILED
            self.report.metadata_error_message = report.error_msg
            self.report.metadata_execution_time = time() - started
            return None

        # report download succeeded
        self.report.metadata_state = constants.STATE_SUCCESS
        self.report.metadata_query_finished_count = 1
        self.report.metadata_current_query = None
        self.report.metadata_execution_time = time() - started
        self.report.update_progress()

        # return parsed manifest
        entries = destination.getvalue().split('\n')
        manifest = [tuple(e.split(',')) for e in entries if e]
        return manifest

    def _fetch_modules(self, manifest):
        """
        Fetch all of the modules referenced in the manifest.

        :param manifest: A parsed PULP_MANIFEST. List of: (name,checksum,size).
        :type manifest: list

        :return: A list of paths to the fetched module files.
        :rtype: list
        """
        self.started_fetch_modules = time()

        # report progress: started
        self.report.modules_state = constants.STATE_RUNNING
        self.report.modules_total_count = len(manifest)
        self.report.modules_finished_count = 0
        self.report.modules_error_count = 0
        self.report.update_progress()

        # download modules
        urls = []
        feed_url = self.feed_url()
        for path, checksum, size in manifest:
            url = urljoin(feed_url, path)
            destination = os.path.join(self.tmp_dir, os.path.basename(path))
            urls.append((url, destination))
        succeeded_reports, failed_reports = self._download(urls)

        # report failed downloads
        if failed_reports:
            self.report.modules_state = constants.STATE_FAILED
            self.report.modules_error_count = len(failed_reports)
            self.report.modules_individual_errors = []

        for report in failed_reports:
            self.report.modules_individual_errors.append(report.error_msg)
        self.report.update_progress()

        return [r.destination for r in succeeded_reports]

    def _import_modules(self, module_paths):
        """
        Import the puppet modules (tarballs) at the specified paths. This will also handle
        removing any modules in the local repository if they are no longer present on remote
        repository and the 'remove_missing' config value is True.

        :param module_paths: A list of paths to puppet module files.
        :type module_paths: list
        """
        existing_module_ids_by_key = {}
        for module in Module.objects.only(*Module.unit_key_fields).all():
            existing_module_ids_by_key[module.unit_key_str] = module.id

        remote_unit_keys = []

        list_of_modules = []
        for module_path in module_paths:
            puppet_manifest = self._extract_metadata(module_path)
            module = Module.from_metadata(puppet_manifest)
            remote_unit_keys.append(module.unit_key_str)
            list_of_modules.append(module)

        pub_step = publish_step.GetLocalUnitsStep(constants.IMPORTER_TYPE_ID, available_units=list_of_modules, repo=self.repo)
        pub_step.process_main()
        self.report.modules_total_count = len(pub_step.units_to_download)

        for module in pub_step.units_to_download:
            if self.canceled:
                return
            _logger.debug(IMPORT_MODULE, dict(mod=module_path))

            module.set_storage_path(os.path.basename(module_path))
            module.save()
            module.import_content(module_path)

            repo_controller.associate_single_unit(self.repo.repo_obj, module)

            self.report.modules_finished_count += 1
            self.report.update_progress()

        # Write the report, making sure we don't overwrite a failure in _fetch_modules
        if self.report.modules_state not in constants.COMPLETE_STATES:
            self.report.modules_state = constants.STATE_SUCCESS
        self.report.modules_execution_time = time() - self.started_fetch_modules
        self.report.update_progress()

        remove_missing = self.config.get_boolean(constants.CONFIG_REMOVE_MISSING)
        if remove_missing is None:
            remove_missing = constants.DEFAULT_REMOVE_MISSING
        if remove_missing:
            self._remove_missing(existing_module_ids_by_key, remote_unit_keys)

    def _remove_missing(self, existing_module_ids_by_key, remote_unit_keys):
        """
        Removes units from the local repository if they are missing from the remote repository.

        :param existing_module_ids_by_key: A dict keyed on Module unit key associated with the
            current repository. The values are the mongoengine id of the corresponding Module.
        :type existing_module_ids_by_key: dict of Module.id values keyed on unit_key_str
        :param remote_unit_keys: A list of all the Module keys in the remote repository
        :type remote_unit_keys: list of strings
        """
        keys_to_remove = list(set(existing_module_ids_by_key.keys()) - set(remote_unit_keys))
        doomed_ids = [existing_module_ids_by_key[key] for key in keys_to_remove]
        doomed_module_iterator = Module.objects.in_bulk(doomed_ids).itervalues()
        repo_controller.disassociate_units(self.repo, doomed_module_iterator)

    def __call__(self):
        """
        Invoke the callable object.

        All work is performed in the repository working directory and cleaned up after the call.

        :return: The final synchronization report.
        :rtype: SyncProgressReport
        """
        self.canceled = False
        self.report = SyncProgressReport(self.conduit)
        self.tmp_dir = mkdtemp(dir=self.repo.working_dir)
        try:
            manifest = self._fetch_manifest()
            if manifest is not None:
                module_paths = self._fetch_modules(manifest)
                self._import_modules(module_paths)
        finally:
            # Update the progress report one last time
            self.report.update_progress()

            shutil.rmtree(self.tmp_dir)
            self.tmp_dir = None

        return self.report


class DownloadListener(AggregatingEventListener):
    """
    An extension of the nectar AggregatingEventListener used primarily to detect cancellation and
    cancel the associated nectar downloader.

    :ivar synchronizer: The object performing the synchronization.
    :type synchronizer: SynchronizeWithDirectory
    :ivar downloader: A nectar downloader.
    :type downloader: nectar.downoaders.base.Downloader
    """

    def __init__(self, synchronizer, downloader):
        """
        :param synchronizer: The object performing the synchronization.
        :type synchronizer: SynchronizeWithDirectory
        :param downloader: A nectar downloader.
        :type downloader: nectar.downoaders.base.Downloader
        """
        AggregatingEventListener.__init__(self)
        self.synchronizer = synchronizer
        self.downloader = downloader
        downloader.event_listener = self

    def download_progress(self, report):
        """
        A download progress event.

        Cancel the download if the import_function call has been canceled.

        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        if self.synchronizer.canceled:
            self.downloader.cancel()
