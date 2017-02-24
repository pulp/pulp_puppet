import os
from StringIO import StringIO

from nectar.downloaders.local import LocalFileDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp.plugins.util.nectar_config import importer_config_to_nectar_config

from pulp_puppet.plugins.importers.downloaders.base import BaseDownloader
from pulp_puppet.plugins.importers.downloaders.exceptions import (FileNotFoundException,
                                                                  FileRetrievalException)
from pulp_puppet.common import constants


class LocalDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a directory local to the Pulp
    server.
    """

    def retrieve_metadata(self, progress_report):
        """
        Retrieves all metadata documents needed to fulfill the configuration
        set for the repository. The progress report will be updated as the
        downloads take place.

        :param progress_report: used to communicate the progress of this operation
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :return: list of JSON documents describing all modules to import
        :rtype:  list
        """
        feed = self.config.get(constants.CONFIG_FEED)
        source_dir = feed[len('file://'):]
        metadata_filename = os.path.join(source_dir, constants.REPO_METADATA_FILENAME)

        # Only do one query for this implementation
        progress_report.metadata_query_finished_count = 0
        progress_report.metadata_query_total_count = 1
        progress_report.metadata_current_query = metadata_filename
        progress_report.update_progress()

        config = importer_config_to_nectar_config(self.config.flatten())
        listener = LocalMetadataDownloadEventListener(progress_report)
        self.downloader = LocalFileDownloader(config, listener)

        url = os.path.join(feed, constants.REPO_METADATA_FILENAME)
        destination = StringIO()
        request = DownloadRequest(url, destination)

        self.downloader.download([request])
        config.finalize()

        self.downloader = None

        for report in listener.failed_reports:
            raise FileRetrievalException(report.error_msg)

        return [destination.getvalue()]

    def retrieve_module(self, progress_report, module):
        """
        Retrieves the given module and returns where on disk it can be
        found. It is the caller's job to copy this file to where Pulp
        wants it to live as its final resting place. This downloader will
        then be allowed to clean up the downloaded file in the
        cleanup_module call.

        :param progress_report: used if any updates need to be made as the
               download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module: module to download
        :type  module: pulp_puppet.common.model.Module

        :return: full path to the temporary location where the module file is
        :rtype:  str
        """
        # Determine the full path to the existing module on disk. This assumes
        # a structure where the modules are located in the same directory as
        # specified in the feed.

        feed = self.config.get(constants.CONFIG_FEED)
        source_dir = feed[len('file://'):]
        module_filename = module.filename()
        full_filename = os.path.join(source_dir, module_filename)

        if not os.path.exists(full_filename):
            raise FileNotFoundException(full_filename)

        return full_filename

    def retrieve_modules(self, progress_report, module_list):
        """
        Batch version of the retrieve_module method

        :param progress_report: used if any updates need to be made as the
               download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module_list: list of modules to be downloaded
        :type  module_list: iterable

        :return: list of full paths to the temporary locations where the modules are
        :rtype:  list
        """
        return [self.retrieve_module(progress_report, module) for module in module_list]

    def cancel(self):
        """
        Cancel the current operation.
        """
        downloader = self.downloader
        if downloader is None:
            return
        downloader.cancel()
        downloader.config.finalize()

    def cleanup_module(self, module):
        """
        Called once the unit has been copied into Pulp's storage location to
        let the downloader do any post-processing it needs (for instance,
        deleting any temporary copies of the file).

        :param module: module to clean up
        :type  module: pulp_puppet.common.model.Module
        """
        # We don't want to delete the original location on disk, so do
        # nothing here.
        pass


class LocalMetadataDownloadEventListener(AggregatingEventListener):
    """
    Nectar event listener that updates the progress report when downloading
    local metadata.
    """

    def __init__(self, progress_report):
        """
        :param progress_report: used if any updates need to be made as the
               download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport
        """
        super(LocalMetadataDownloadEventListener, self).__init__()
        self.progress_report = progress_report

    def download_succeeded(self, report):
        """
        :param report: download report for a specific download
        :type  report: nectar.report.DownloadReport
        """
        super(LocalMetadataDownloadEventListener, self).download_succeeded(report)
        self.progress_report.metadata_query_finished_count += 1
        self.progress_report.update_progress()
