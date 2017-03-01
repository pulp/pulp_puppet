import os

import mock

from nectar.report import DownloadReport

import base_downloader
from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.downloaders import exceptions, web
from pulp_puppet.plugins.importers.downloaders.web import HttpDownloader


TEST_SOURCE = 'http://forge.puppetlabs.com/'


class HttpDownloaderTests(base_downloader.BaseDownloaderTests):

    def setUp(self):
        super(HttpDownloaderTests, self).setUp()
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE
        self.downloader = HttpDownloader(self.repo, None, self.config)

    @mock.patch('nectar.config.DownloaderConfig.finalize')
    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_retrieve_metadata(self, mock_get_working_dir, mock_downloader_download, mock_finalize):
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        self.assertEqual(len(docs), 1)

        self.assertEqual(mock_downloader_download.call_count, 1)
        mock_finalize.assert_called_once()

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_retrieve_metadata_multiple_queries(self, mock_get_working_dir,
                                                mock_downloader_download):
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        self.assertEqual(2, len(docs))

        self.assertEqual(mock_downloader_download.call_count, 1)

    @mock.patch('pulp_puppet.plugins.importers.downloaders.web.HTTPMetadataDownloadEventListener')
    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_retrieve_metadata_with_error(self, mock_get_working_dir, mock_downloader_download,
                                          mock_listener_constructor):
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

    @mock.patch.object(HttpDownloader, 'retrieve_modules')
    def test_retrieve_module(self, mock_retrieve_modules):
        mock_retrieve_modules.return_value = ['foo', 'bar']
        try:
            stored_filename = self.downloader.retrieve_module(self.mock_progress_report,
                                                              self.module)
        except:
            self.fail()

        mock_retrieve_modules.assert_called_once_with(self.mock_progress_report, [self.module])
        self.assertEqual(stored_filename, 'foo')

    @mock.patch('pulp_puppet.plugins.importers.downloaders.web.HTTPModuleDownloadEventListener')
    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_retrieve_module_missing_module(self, mock_get_working_dir, mock_downloader_download,
                                            mock_listener_constructor):
        # Setup
        self.module.author = 'asdf'
        self.module.puppet_standard_filename.return_value = 'puppet-filename.tar.gz'
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

    @mock.patch('nectar.downloaders.threaded.HTTPThreadedDownloader.download')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_cleanup_module(self, mock_get_working_dir, mock_downloader_download):
        self.module.author = 'asdf'
        self.module.puppet_standard_filename.return_value = 'puppet-filename.tar.gz'
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
        # Setup
        self.module.author = 'asdf'
        self.module.puppet_standard_filename.return_value = 'puppet-filename.tar.gz'
        self.module.filename.return_value = 'puppet-filename.tar.gz'

        # Test

        # Strip the trailing / off to make sure that branch is followed
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE[:-1]
        url = self.downloader._create_module_url(self.module)

        # Verify
        path = constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (self.module.author[0],
                                                             self.module.author)
        expected = TEST_SOURCE + path + self.module.filename()
        self.assertEqual(url, expected)

    def test_create_download_tmp_dir(self):
        # Test
        created = web._create_download_tmp_dir(self.working_dir)

        # Verify
        self.assertTrue(os.path.exists(created))
        self.assertEqual(created, os.path.join(self.working_dir, web.DOWNLOAD_TMP_DIR))
