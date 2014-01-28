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
from urlparse import urlparse, urljoin, urlunparse
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


url_to_downloader = {
    'http': HTTPThreadedDownloader,
    'https': HTTPThreadedDownloader,
    'file': LocalFileDownloader,
}


class SynchronizeWithDirectory(object):
    """
    A callable object used to synchronize with a directory of packaged puppet modules.
    The source of the import is a directory containing a PULP_MANIFEST and
    multiple puppet built puppet modules.

    :ivar conduit: Provides access to relevant Pulp functionality.
    :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
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
        :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param config: Plugin configuration.
        :type config: pulp.plugins.config.PluginCallConfiguration
        """
        self.conduit = conduit
        self.config = config
        self.report = None
        self.canceled = False
        self.tmp_dir = None

    def cancel(self):
        """
        Cancel puppet module import.
        """
        self.canceled = True

    def base_url(self):
        """
        Get the base URL from feed URL.
        Basically, this is just the feed URL without the PULP_MANIFEST.

        :return: The base URL.
        :rtype: str
        """
        feed_url = self.config.get(constants.CONFIG_FEED)
        scheme, netloc, path, params, query, fragment = urlparse(feed_url)
        path = os.path.dirname(path)
        if not path.endswith('/'):
            # must end with / for use with urljoin
            path += '/'
        parts = (scheme, netloc, path, params, query, fragment)
        return urlunparse(parts)

    def _run(self, inventory):
        """
        Perform the synchronization using the supplied inventory.

        :param inventory: An inventory object.
        :type inventory: Inventory
        """
        manifest = self._fetch_manifest()
        module_paths = self._fetch_modules(manifest)
        imported_modules = self._import_modules(inventory, module_paths)
        self._purge_unwanted_modules(inventory, imported_modules)

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
        feed_url = self.config.get(constants.CONFIG_FEED)
        nectar_config = importer_config_to_nectar_config(self.config.flatten())
        nectar_class = url_to_downloader[urlparse(feed_url).scheme]
        downloader = nectar_class(nectar_config)
        listener = DownloadListener(self, downloader)
        self_list = []
        for url, destination in urls:
            self_list.append(DownloadRequest(url, destination))
        downloader.download(self_list)
        nectar_config.finalize()
        return listener.succeeded_reports, listener.failed_reports

    def _fetch_manifest(self):
        """
        Fetch the PULP_MANAFEST.
        After the manifest is fetched, the file is parsed into a list of tuples.

        :return: The manifest content.  List of: (name,checksum,size).
        :rtype: list
        """
        started = time()

        # report progress: started
        self.report.metadata_state = constants.STATE_RUNNING
        self.report.update_progress()

        # download manifest
        destination = StringIO()
        feed_url = self.config.get(constants.CONFIG_FEED)
        succeeded_reports, failed_reports = self._download([(feed_url, destination)])

        # report download failed
        if failed_reports:
            report = failed_reports[0]
            self.report.metadata_state = constants.STATE_FAILED
            self.report.metadata_error_message = report.error_msg
            self.report.metadata_execution_time = time() - started
            return []

        # report download succeeded
        self.report.metadata_state = constants.STATE_SUCCESS
        self.report.metadata_query_finished_count = 1
        self.report.metadata_query_total_count = 1
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
        started = time()

        # report progress: started
        self.report.modules_state = constants.STATE_RUNNING
        self.report.update_progress()

        # download modules
        urls = []
        base_url = self.base_url()
        for path, checksum, size in manifest:
            url = urljoin(base_url, path)
            destination = os.path.join(self.tmp_dir, os.path.basename(path))
            urls.append((url, destination))
        succeeded_reports, failed_reports = self._download(urls)

        # report failed downloads
        if failed_reports:
            self.report.module_state = constants.STATE_FAILED
            self.report.modules_error_count = len(failed_reports)
            self.report.modules_individual_errors = []
        else:
            self.report.module_state = constants.STATE_SUCCESS
        for report in failed_reports:
            self.report.modules_individual_errors.append(report.error_msg)

        # report succeeded
        self.report.modules_execution_time = time() - started
        self.report.modules_total_count = len(succeeded_reports)
        self.report.modules_finished_count = len(succeeded_reports)

        # return module paths
        return [r.destination for r in succeeded_reports]

    def _import_modules(self, inventory, module_paths):
        """
        Import the puppet modules (tarballs) at the specified paths.

        :param inventory: A module inventory object.
        :type inventory: Inventory
        :param module_paths: A list of paths to puppet module files.
        :type module_paths: list
        :return: A list of the imported module unit keys.
        :rtype: list
        """
        imported_modules = []
        for module_path in module_paths:
            if self.canceled:
                return []
            puppet_manifest = self._extract_metadata(module_path)
            module = Module.from_dict(puppet_manifest)
            if inventory.already_associated(module):
                continue
            imported_modules.append(module.unit_key())
            self._add_module(module_path, module)
        return imported_modules

    def _add_module(self, path, module):
        """
        Add the specified module to Pulp using the conduit.
        This will both create the module and associate it to a repository.
        The module tarball is copied to the *storage path* only if it does
        not already exist at the *storage path*.

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

    def _purge_unwanted_modules(self, inventory, imported_modules):
        """
        Purge unwanted puppet modules.
        Unwanted modules are those modules associated with the repository but
        not imported during this operation.  Skipped when the configuration does
        not specify do perform it.  The inventory is used to determine which
        modules should be removed.

        :param inventory: A module inventory object.
        :type inventory: Inventory
        :param imported_modules: List of modules import.  List of: Module.
        :type imported_modules: list
        """
        purge_option = self.config.get_boolean(constants.CONFIG_REMOVE_MISSING)
        if purge_option is None:
            purge_option = constants.DEFAULT_REMOVE_MISSING
        if not purge_option:
            # no purge requested
            return
        for unit_key in inventory.unwanted_modules(imported_modules):
            if self.canceled:
                return
            self.conduit.remove_unit(unit_key)

    def __call__(self, repository):
        """
        Invoke the callable object.
        All work is performed in the repository working directory and
        cleaned up after the call.

        :param repository: A Pulp repository object.
        :type repository: pulp.server.plugins.model.Repository
        :return: The final synchronization report.
        :rtype: pulp.plugins.model.SyncReport
        """
        self.canceled = False
        self.report = SyncProgressReport(self.conduit)
        self.tmp_dir = mkdtemp(dir=repository.working_dir)
        try:
            inventory = Inventory(self.conduit)
            self._run(inventory)
            self.report.build_final_report()
            return self.report
        finally:
            shutil.rmtree(self.tmp_dir)
            self.tmp_dir = None


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


class Inventory(object):
    """
    Represents the Pulp inventory of puppet modules currently
    associated to a directory.  Retrieves the inventory and provides useful
    methods for working with it.

    :ivar associated: A set of puppet module unit keys associated with a repository.
    :type associated: set
    """

    @staticmethod
    def _associated(conduit):
        """
        Retrieve the modules associated with a repository, build a set containing
        the unit_key for each and return it.

        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
        :return: The set of unit keys.
        :rtype: set
        """
        key_set = set()
        criteria = UnitAssociationCriteria(type_ids=[constants.TYPE_PUPPET_MODULE])
        units = conduit.get_units(criteria=criteria, as_generator=True)
        for unit in units:
            module = Module.from_unit(unit)
            key_set.add(tuple(module.unit_key().items()))
        return key_set

    def __init__(self, conduit):
        """
        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
        """
        self.associated = Inventory._associated(conduit)

    def already_associated(self, module):
        """
        Get whether the specified module is already associated with the
        inventory of modules associated with a repository.

        :param module: A puppet module.
        :type module: Module
        :return: True if already associated.
        :rtype: bool
        """
        return tuple(module.unit_key().items()) in self.associated

    def unwanted_modules(self, wanted_modules):
        """
        Get a set of unit keys for those modules that are deemed to
        be *unwanted*.  Unwanted modules are those modules that are
        associated with a repository but not included in the specified
        list of *wanted* modules.  The *wanted* modules are those that
        should be associated with the repository.  Thus, any modules associated
        with the inventory that are not included in the *wanted* list are
        deemed *unwanted*.
        :param wanted_modules: A list of module unit keys.
        :type wanted_modules: list
        :return: A list of unwanted module unit keys.
        :rtype: list
        """
        wanted_set = set()
        for unit_key in wanted_modules:
            wanted_set.add(tuple(unit_key.items()))
        unwanted = [dict(k) for k in self.associated - wanted_set]
        return unwanted

