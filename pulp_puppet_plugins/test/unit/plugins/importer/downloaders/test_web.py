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
import pycurl
import shutil
import tempfile
import unittest

import mock

from nectar.report import DownloadReport

import base_downloader
from pulp_puppet.common import constants, model
from pulp_puppet.plugins.importers.downloaders import exceptions, web
from pulp_puppet.plugins.importers.downloaders.web import HttpDownloader

TEST_SOURCE = 'http://forge.puppetlabs.com/'


class HttpDownloaderTests(base_downloader.BaseDownloaderTests):

    def setUp(self):
        super(HttpDownloaderTests, self).setUp()
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE
        self.downloader = HttpDownloader(self.repo, None, self.config)

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_retrieve_metadata(self, mock_downloader_download):
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        self.assertEqual(len(docs), 1)

        self.assertEqual(mock_downloader_download.call_count, 1)

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_retrieve_metadata_multiple_queries(self, mock_downloader_download):
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        self.assertEqual(2, len(docs))

        self.assertEqual(mock_downloader_download.call_count, 1)

    @mock.patch('pulp_puppet.plugins.importers.downloaders.web.HTTPMetadataDownloadEventListener')
    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_retrieve_metadata_with_error(self, mock_downloader_download, mock_listener_constructor):
        # Setup
        mock_listener = mock.MagicMock()
        report = DownloadReport(None, None)
        report.error_msg = 'oops'
        mock_listener.failed_reports = [report]
        mock_listener_constructor.return_value = mock_listener

        # Test
        try:
            self.downloader.retrieve_metadata(self.mock_progress_report)
            self.fail()
        except exceptions.FileRetrievalException:
            pass

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_retrieve_module(self, mock_downloader_download):
        try:
            stored_filename = self.downloader.retrieve_module(self.mock_progress_report, self.module)
        except:
            self.fail()

    @mock.patch('pulp_puppet.plugins.importers.downloaders.web.HTTPModuleDownloadEventListener')
    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_retrieve_module_missing_module(self, mock_downloader_download, mock_listener_constructor):
        # Setup
        mock_listener = mock.MagicMock()
        report = DownloadReport(None, None)
        report.error_msg = 'oops'
        mock_listener.failed_reports = [report]
        mock_listener_constructor.return_value = mock_listener

        # Test
        try:
            self.downloader.retrieve_module(self.mock_progress_report, self.module)
            self.fail()
        except exceptions.FileRetrievalException:
            expected_filename = web._create_download_tmp_dir(self.working_dir)
            expected_filename = os.path.join(expected_filename, self.module.filename())
            self.assertFalse(os.path.exists(os.path.join(expected_filename)))

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    def test_cleanup_module(self, mock_downloader_download):
        stored_filename = self.downloader.retrieve_module(self.mock_progress_report, self.module)
        self.downloader.cleanup_module(self.module)
        self.assertTrue(not os.path.exists(stored_filename))


    def test_create_metadata_download_urls(self):
        # Setup
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(2, len(urls))
        self.assertEqual(urls[0], TEST_SOURCE + 'modules.json?q=a')
        self.assertEqual(urls[1], TEST_SOURCE + 'modules.json?q=b&q=c')

    def test_create_metadata_download_urls_no_queries(self):
        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(1, len(urls))
        self.assertEqual(urls[0], TEST_SOURCE + 'modules.json')

    def test_create_module_url(self):
        # Test

        # Strip the trailing / off to make sure that branch is followed
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE[:-1]
        url = self.downloader._create_module_url(self.module)

        # Verify
        expected = TEST_SOURCE + \
                   constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (self.module.author[0], self.module.author) + \
                   self.module.filename()
        self.assertEqual(url, expected)

    def test_create_download_tmp_dir(self):
        # Test
        created = web._create_download_tmp_dir(self.working_dir)

        # Verify
        self.assertTrue(os.path.exists(created))
        self.assertEqual(created, os.path.join(self.working_dir, web.DOWNLOAD_TMP_DIR))

