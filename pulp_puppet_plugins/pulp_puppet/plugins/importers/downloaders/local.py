# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
from StringIO import StringIO

from nectar.downloaders.local import LocalFileDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp.plugins.util.nectar_config import importer_config_to_nectar_config

from pulp_puppet.plugins.importers.downloaders.base import BaseDownloader
from pulp_puppet.plugins.importers.downloaders.exceptions import FileNotFoundException, FileRetrievalException
from pulp_puppet.common import constants


class LocalDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a directory local to the Pulp
    server.
    """

    def retrieve_metadata(self, progress_report):
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

        self.downloader = None

        for report in listener.failed_reports:
            raise FileRetrievalException(report.error_msg)

        return [destination.getvalue()]

    def retrieve_module(self, progress_report, module):

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
        return [self.retrieve_module(progress_report, module) for module in module_list]

    def cancel(self, progress_report):
        downloader = self.downloader
        if downloader is None:
            return
        downloader.cancel()

    def cleanup_module(self, module):
        # We don't want to delete the original location on disk, so do
        # nothing here.
        pass


class LocalMetadataDownloadEventListener(AggregatingEventListener):

    def __init__(self, progress_report):
        super(LocalMetadataDownloadEventListener, self).__init__()
        self.progress_report = progress_report

    def download_succeeded(self, report):
        super(LocalMetadataDownloadEventListener, self).download_succeeded(report)
        self.progress_report.metadata_query_finished_count += 1
        self.progress_report.update_progress()

