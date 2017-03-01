import copy
import errno
import os

from cStringIO import StringIO

from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp.plugins.util.nectar_config import importer_config_to_nectar_config

from pulp_puppet.plugins.importers.downloaders.base import BaseDownloader
from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.downloaders import exceptions


DOWNLOAD_TMP_DIR = 'http-downloads'


class HttpDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a remote source over HTTP.
    """

    def retrieve_metadata(self, progress_report):
        """
        Retrieves all metadata documents needed to fulfill the configuration set for the
        repository. The progress report will be updated as the downloads take place.

        :param progress_report: used to communicate the progress of this operation
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :return: list of JSON documents describing all modules to import
        :rtype: list
        """
        urls = self._create_metadata_download_urls()

        # Update the progress report to reflect the number of queries it will take
        progress_report.metadata_query_finished_count = 0
        progress_report.metadata_query_total_count = len(urls)

        listener = HTTPMetadataDownloadEventListener(progress_report)
        self.downloader = self._create_and_configure_downloader(listener)

        request_list = [DownloadRequest(url, StringIO()) for url in urls]

        # Let any exceptions from this bubble up, the caller will update
        # the progress report as necessary
        try:
            self.downloader.download(request_list)
        finally:
            self.downloader.config.finalize()
            self.downloader = None

        for report in listener.failed_reports:
            raise exceptions.FileRetrievalException(report.error_msg)

        return [r.destination.getvalue() for r in request_list]

    def retrieve_module(self, progress_report, module):
        """
        Retrieves the given module and returns where on disk it can be found.

        :param progress_report: used if any updates need to be made as the download runs
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module: module to download
        :type module: pulp_puppet.plugins.db.models.Module

        :return: full path to the temporary location where the module file is
        :rtype:  str
        """
        return self.retrieve_modules(progress_report, [module])[0]

    def retrieve_modules(self, progress_report, module_list):
        """
        Batch version of the retrieve_module method.

        :param progress_report: used if any updates need to be made as the download runs
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module_list: list of modules to be downloaded
        :type module_list: list of pulp_puppet.plugins.db.models.Module objects

        :return: list of full paths to the temporary locations where the modules are
        :rtype: list
        """
        listener = HTTPModuleDownloadEventListener(progress_report)
        self.downloader = self._create_and_configure_downloader(listener)

        request_list = []

        for module in module_list:
            url = self._create_module_url(module)
            module_tmp_dir = _create_download_tmp_dir(self.repo.working_dir)
            module_tmp_filename = os.path.join(module_tmp_dir, module.puppet_standard_filename())
            request = DownloadRequest(url, module_tmp_filename)
            request_list.append(request)

        try:
            self.downloader.download(request_list)
        finally:
            self.downloader.config.finalize()
            self.downloader = None

        for report in listener.failed_reports:
            raise exceptions.FileRetrievalException(report.error_msg)

        return [r.destination for r in request_list]

    def cancel(self):
        """
        Cancel the current operation.
        """
        if self.downloader is None:
            return
        self.downloader.cancel()

    def cleanup_module(self, module):
        """
        Cleanup up after the module has been moved into place.

        Called once the unit has been copied into Pulp's storage location. This allows the
        downloader do any post-processing it needs such as deleting any temporary copies of the
        file.

        :param module: module to clean up
        :type  module: pulp_puppet.plugins.db.models.Module
        """
        module_tmp_dir = _create_download_tmp_dir(self.repo.working_dir)
        module_tmp_filename = os.path.join(module_tmp_dir, module.puppet_standard_filename())

        try:
            os.remove(module_tmp_filename)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def _create_metadata_download_urls(self):
        """
        Uses the plugin configuration to determine a list of URLs for all metadata documents
        that should be used in the sync.

        :return: list of URLs to be downloaded
        :rtype: list
        """
        feed = self.config.get(constants.CONFIG_FEED)
        # Puppet forge is sensitive about a double slash, so strip the trailing here
        if feed.endswith('/'):
            feed = feed[:-1]
        base_url = feed + '/' + constants.REPO_METADATA_FILENAME

        all_urls = []

        queries = self.config.get(constants.CONFIG_QUERIES)
        if queries:
            for query in queries:
                query_url = copy.copy(base_url)
                query_url += '?'

                # The config supports either single queries or tuples of them.
                # If it's a single, wrap it in a list so we can handle them the same
                if not isinstance(query, (list, tuple)):
                    query = [query]

                for query_term in query:
                    query_url += 'q=%s&' % query_term

                # Chop off the last & that was added
                query_url = query_url[:-1]
                all_urls.append(query_url)
        else:
            all_urls.append(base_url)

        return all_urls

    def _create_module_url(self, module):
        """
        Generates the URL for a module at the configured source.

        :param module: module instance being downloaded
        :type module: pulp_puppet.plugins.db.models.Module

        :return: full URL to download the module
        :rtype: str
        """
        url = self.config.get(constants.CONFIG_FEED)
        if not url.endswith('/'):
            url += '/'

        url += constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (module.author[0], module.author)
        url += module.puppet_standard_filename()
        return url

    def _create_and_configure_downloader(self, listener):
        config = importer_config_to_nectar_config(self.config.flatten())
        return HTTPThreadedDownloader(config, listener)


class HTTPMetadataDownloadEventListener(AggregatingEventListener):
    """
    Nectar event listener that updates the progress report when downloading
    metadata from the web.
    """

    def __init__(self, progress_report):
        """
        :param progress_report: used if any updates need to be made as the download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport
        """
        super(HTTPMetadataDownloadEventListener, self).__init__()
        self.progress_report = progress_report

    def download_started(self, report):
        """
        :param report: download report for a specific download
        :type report: nectar.report.DownloadReport
        """
        self.progress_report.metadata_current_query = report.url
        self.progress_report.update_progress()

    def download_succeeded(self, report):
        """
        :param report: download report for a specific download
        :type report: nectar.report.DownloadReport
        """
        super(HTTPMetadataDownloadEventListener, self).download_succeeded(report)
        self.progress_report.metadata_query_finished_count += 1
        self.progress_report.update_progress()


class HTTPModuleDownloadEventListener(AggregatingEventListener):
    """
    Nectar event listener that updates the progress report when downloading modules from the web.
    """

    def __init__(self, progress_report):
        """
        :param progress_report: used if any updates need to be made as the download runs
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport
        """
        super(HTTPModuleDownloadEventListener, self).__init__()
        self.progress_report = progress_report


def _create_download_tmp_dir(repo_working_dir):
    tmp_dir = os.path.join(repo_working_dir, DOWNLOAD_TMP_DIR)
    try:
        os.mkdir(tmp_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return tmp_dir
