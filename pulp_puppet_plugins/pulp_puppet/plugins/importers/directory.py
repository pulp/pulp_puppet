# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import logging
import shutil
import tarfile
import json

from time import time
from gettext import gettext as _
from urlparse import urlparse, urljoin
from StringIO import StringIO
from tempfile import mkdtemp
from contextlib import closing

from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp.plugins.util.nectar_config import importer_config_to_nectar_config
from pulp.plugins.conduits.mixins import UnitAssociationCriteria

from pulp_puppet.common import constants
from pulp_puppet.common.model import Module
from pulp_puppet.common.sync_progress import SyncProgressReport


_LOG = logging.getLogger(__name__)


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
        it into temporary directory.  Then read the file and return the json decoded content.

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

    def __init__(self, conduit, config):
        """
        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config: Plugin configuration.
        :type config: pulp.plugins.config.PluginCallConfiguration
        """
        self.conduit = conduit
        self.config = config
        self.report = None
        self.canceled = False
        self.tmp_dir = None

    def feed_url(self):
        """
        Get the feed URL from the configuration and ensure it has a
        trailing '/' so urljoin will work correctly.
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
        Encapsulates nectar details and provides a simplified method
        of downloading files.

        :param urls: A list of tuples: (url, destination).  The *url* and
            *destination* are both strings.  The *destination* is the fully
            qualified path to where the file is to be downloaded.
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
            _LOG.info(FETCH_SUCCEEDED % dict(url=report.url, dst=report.destination))
        for report in listener.failed_reports:
            _LOG.error(FETCH_FAILED % dict(url=report.url, msg=report.error_msg))

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
        :type  manifest: list

        :return: A list of paths to the fetched module files.
        :rtype:  list
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
        criteria = UnitAssociationCriteria(type_ids=[constants.TYPE_PUPPET_MODULE],
                                           unit_fields=Module.UNIT_KEY_NAMES)
        local_units = self.conduit.get_units(criteria=criteria)
        local_unit_keys = [unit.unit_key for unit in local_units]
        remote_unit_keys = []

        for module_path in module_paths:
            if self.canceled:
                return
            puppet_manifest = self._extract_metadata(module_path)
            module = Module.from_json(puppet_manifest)
            remote_unit_keys.append(module.unit_key())

            # Even though we've already basically processed this unit, not doing this makes the
            # progress reporting confusing because it shows Pulp always importing all the modules.
            if module.unit_key() in local_unit_keys:
                self.report.modules_total_count -= 1
                continue
            _LOG.debug(IMPORT_MODULE % dict(mod=module_path))
            self._add_module(module_path, module)
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
            self._remove_missing(local_units, remote_unit_keys)

    def _remove_missing(self, local_units, remote_unit_keys):
        """
        Removes units from the local repository if they are missing from the remote repository.

        :param local_units:         A list of units associated with the current repository
        :type  local_units:         list of AssociatedUnit
        :param remote_unit_keys:    a list of all the unit keys in the remote repository
        :type  remote_unit_keys:    list of dict
        """
        for missing in [unit for unit in local_units if unit.unit_key not in remote_unit_keys]:
            if self.canceled:
                return
            self.conduit.remove_unit(missing)

    def _add_module(self, path, module):
        """
        Add the specified module to Pulp using the conduit. This will both create the module
        and associate it to a repository. The module tarball is copied to the *storage path*
        only if it does not already exist at the *storage path*.

        :param path: The path to the downloaded module tarball.
        :type path: str
        :param module: A puppet module model object.
        :type module: Module
        """
        type_id = constants.TYPE_PUPPET_MODULE
        unit_key = module.unit_key()
        unit_metadata = module.unit_metadata()
        relative_path = constants.STORAGE_MODULE_RELATIVE_PATH % module.filename()
        unit = self.conduit.init_unit(type_id, unit_key, unit_metadata, relative_path)
        if not os.path.exists(unit.storage_path):
            shutil.copy(path, unit.storage_path)
        self.conduit.save_unit(unit)

    def __call__(self, repository):
        """
        Invoke the callable object.
        All work is performed in the repository working directory and
        cleaned up after the call.

        :param repository: A Pulp repository object.
        :type repository: pulp.server.plugins.model.Repository
        :return: The final synchronization report.
        :rtype: SyncProgressReport
        """
        self.canceled = False
        self.report = SyncProgressReport(self.conduit)
        self.tmp_dir = mkdtemp(dir=repository.working_dir)
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
    An extension of the nectar AggregatingEventListener used primarily
    to detect cancellation and cancel the associated nectar downloader.

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