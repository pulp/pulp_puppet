import os

from unittest import TestCase
from collections import namedtuple
from urlparse import urljoin

from mock import patch, Mock, ANY

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.directory import SynchronizeWithDirectory, DownloadListener
from pulp_puppet.common.sync_progress import SyncProgressReport


class TestSynchronizeWithDirectory(TestCase):

    def test_constructor(self):
        mock_repo = Mock()
        conduit = Mock()
        config = {}

        # testing

        method = SynchronizeWithDirectory(mock_repo, conduit, config)

        # validation

        self.assertEqual(method.conduit, conduit)
        self.assertEqual(method.config, config)

    def test_feed_url(self):
        feed_url = 'http://abc.com/repository'
        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        # testing

        method = SynchronizeWithDirectory(mock_repo, conduit, config)

        # validation

        self.assertEqual(method.feed_url(), feed_url + '/')

    def test_cancel(self):
        mock_repo = Mock()
        conduit = Mock()
        config = {}

        # testing

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        method.cancel()

        # validation

        self.assertTrue(method.canceled)

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._remove_missing')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._import_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_manifest')
    @patch('shutil.rmtree')
    @patch('pulp_puppet.plugins.importers.directory.mkdtemp')
    def test_call(self, mock_mkdtemp, mock_rmtree, mock_fetch_manifest, mock_fetch_modules,
                  mock_import_modules, mock_remove_missing):
        mock_fetch_manifest.return_value = 'manifest_destiny'
        mock_fetch_modules.return_value = 'some modules'
        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: 'http://host/root/PULP_MANAFEST'}
        repository = Mock()
        repository.working_dir = 'working'
        mock_mkdtemp.return_value = '/abc'

        # testing
        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        report = method()

        # validation
        self.assertEqual(1, mock_fetch_manifest.call_count)
        mock_fetch_modules.assert_called_once_with('manifest_destiny')
        mock_import_modules.assert_called_once_with('some modules')
        self.assertEqual(0, mock_remove_missing.call_count)
        self.assertFalse(method.canceled)
        self.assertTrue(isinstance(method.report, SyncProgressReport))
        self.assertTrue(isinstance(report, SyncProgressReport))
        mock_mkdtemp.assert_called_with(dir=mock_repo.working_dir)
        mock_rmtree.assert_called_with(os.path.join(repository.working_dir, mock_mkdtemp()))

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._import_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_manifest')
    @patch('shutil.rmtree')
    @patch('pulp_puppet.plugins.importers.directory.mkdtemp')
    def test_call_no_manifest(self, mock_mkdtemp, mock_rmtree, mock_fetch_manifest, *mocks):
        mock_fetch_manifest.return_value = None
        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: 'http://host/root/PULP_MANAFEST'}
        repository = Mock()
        repository.working_dir = 'working'
        mock_mkdtemp.return_value = '/abc'

        # testing
        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        report = method()

        # validation
        self.assertEqual(1, mock_fetch_manifest.call_count)
        self.assertEqual(0, mocks[0].call_count)
        self.assertEqual(0, mocks[1].call_count)
        self.assertFalse(method.canceled)
        self.assertTrue(isinstance(method.report, SyncProgressReport))
        self.assertTrue(isinstance(report, SyncProgressReport))
        mock_mkdtemp.assert_called_with(dir=mock_repo.working_dir)
        mock_rmtree.assert_called_with(os.path.join(repository.working_dir, mock_mkdtemp()))

    @patch('pulp_puppet.plugins.importers.directory.URL_TO_DOWNLOADER')
    @patch('pulp_puppet.plugins.importers.directory.importer_config_to_nectar_config')
    @patch('pulp_puppet.plugins.importers.directory.DownloadListener')
    def test_download(self, mock_listener, mock_nectar_config, mock_downloader_mapping):
        mock_nectar_config.return_value = Mock()

        mock_http_downloader = Mock()
        mock_http_class = Mock(return_value=mock_http_downloader)
        mock_downloader_mapping.__getitem__.return_value = mock_http_class

        mock_repo = Mock()
        conduit = Mock()
        config = Mock()
        config.get = Mock(side_effect={constants.CONFIG_FEED: 'http://host/root/PULP_MANAFEST'})
        config.flatten = Mock(return_value={})

        urls = [
            ('http://host/root/path_1', '/tmp/path_1'),
            ('http://host/root/path_2', '/tmp/path_1'),
        ]

        report = namedtuple('Report', ['url', 'destination', 'error_msg'])
        _listener = Mock()
        _listener.succeeded_reports = [report(urls[0][0], urls[0][1], None)]
        _listener.failed_reports = [report(urls[1][0], urls[1][1], 'File Not Found')]
        mock_listener.return_value = _listener

        # test

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        succeeded_reports, failed_reports = method._download(urls)

        # validation

        method.config.flatten.assert_called_with()
        mock_nectar_config.assert_called_with(method.config.flatten())

        self.assertTrue(mock_http_downloader.download.called)
        self.assertEqual(mock_http_downloader.download.call_count, 1)
        self.assertEqual(mock_http_downloader.download.call_args[0][0][0].url, urls[0][0])
        self.assertEqual(mock_http_downloader.download.call_args[0][0][0].destination, urls[0][1])
        self.assertEqual(mock_http_downloader.download.call_args[0][0][1].url, urls[1][0])
        self.assertEqual(mock_http_downloader.download.call_args[0][0][0].destination, urls[1][1])

        self.assertTrue(isinstance(succeeded_reports, list))
        self.assertEqual(len(succeeded_reports), 1)
        self.assertEqual(succeeded_reports[0].url, urls[0][0])
        self.assertEqual(succeeded_reports[0].destination, urls[0][1])
        self.assertTrue(isinstance(succeeded_reports, list))

        self.assertTrue(isinstance(failed_reports, list))
        self.assertEqual(len(failed_reports), 1)
        self.assertEqual(failed_reports[0].url, urls[1][0])
        self.assertEqual(failed_reports[0].destination, urls[1][1])
        self.assertTrue(isinstance(failed_reports, list))

    @patch('pulp_puppet.plugins.importers.directory.StringIO.getvalue')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._download')
    def test_fetch_manifest(self, mock_download, mock_get_value):
        feed_url = 'http://host/root/'

        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}
        succeeded_report = Mock()

        mock_download.return_value = [succeeded_report], []
        mock_get_value.return_value = 'A,B,C\nD,E,F\n'

        # test

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        method.report = Mock()
        manifest = method._fetch_manifest()

        # validation

        mock_download.assert_called_with([(urljoin(feed_url, constants.MANIFEST_FILENAME), ANY)])

        self.assertEqual(manifest, [('A', 'B', 'C'), ('D', 'E', 'F')])

        self.assertTrue(method.report.update_progress.called)
        self.assertEqual(method.report.metadata_state, constants.STATE_SUCCESS)
        self.assertEqual(method.report.metadata_query_finished_count, 1)
        self.assertEqual(method.report.metadata_query_total_count, 1)
        self.assertEqual(method.report.metadata_current_query, None)
        self.assertTrue(method.report.metadata_execution_time > 0)

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._download')
    def test_fetch_manifest_failed(self, mock_download):
        feed_url = 'http://host/root/'

        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}
        failed_report = Mock()
        failed_report.error_msg = 'just up and failed'

        mock_download.return_value = [], [failed_report]

        # test

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        method.report = Mock()
        manifest = method._fetch_manifest()

        # validation

        mock_download.assert_called_with([(urljoin(feed_url, constants.MANIFEST_FILENAME), ANY)])

        self.assertTrue(manifest is None)

        self.assertTrue(method.report.update_progress.called)
        self.assertEqual(method.report.metadata_state, constants.STATE_FAILED)
        self.assertEqual(method.report.metadata_error_message, failed_report.error_msg)
        self.assertTrue(method.report.metadata_execution_time > 0)

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._download')
    def test_fetch_modules(self, mock_download):
        tmp_dir = '/tmp/puppet-testing'
        feed_url = 'http://host/root/'

        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        manifest = [('path1', 'AA', 10), ('path2', 'BB', 20)]

        report_1 = Mock()
        report_1.destination = os.path.join(tmp_dir, manifest[0][0])
        report_2 = Mock()
        report_2.destination = os.path.join(tmp_dir, manifest[1][0])
        mock_download.return_value = [report_1, report_2], []

        # test

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        method.report = Mock()
        method.tmp_dir = '/tmp/puppet-testing'
        module_paths = method._fetch_modules(manifest)

        # validation

        url_1 = os.path.join(feed_url, manifest[0][0])
        url_2 = os.path.join(feed_url, manifest[1][0])

        mock_download.assert_any_with([(url_1, report_1.destination)])
        mock_download.assert_any_with([(url_2, report_2.destination)])

        self.assertEqual(len(module_paths), 2)
        self.assertEqual(module_paths[0], report_1.destination)
        self.assertEqual(module_paths[1], report_2.destination)

        # Assert the progress report was updated and the report is still in the running state.
        # The _import_modules method must be called to complete the task.
        self.assertTrue(method.report.update_progress.called)
        self.assertEqual(method.report.modules_state, constants.STATE_RUNNING)

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._download')
    def test_fetch_modules_failures(self, mock_download):
        tmp_dir = '/tmp/puppet-testing'
        feed_url = 'http://host/root/'

        mock_repo = Mock()
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        manifest = [('path1', 'AA', 10), ('path2', 'BB', 20)]

        report_1 = Mock()
        report_1.destination = os.path.join(tmp_dir, manifest[0][0])
        report_2 = Mock()
        report_2.destination = os.path.join(tmp_dir, manifest[1][0])
        report_2.error_msg = 'it just dont work'
        mock_download.return_value = [report_1], [report_2]

        # test

        method = SynchronizeWithDirectory(mock_repo, conduit, config)
        method.report = Mock()
        method.tmp_dir = '/tmp/puppet-testing'
        module_paths = method._fetch_modules(manifest)

        # validation

        url_1 = os.path.join(feed_url, manifest[0][0])
        url_2 = os.path.join(feed_url, manifest[1][0])

        mock_download.assert_any_with([(url_1, report_1.destination)])
        mock_download.assert_any_with([(url_2, report_2.destination)])

        self.assertEqual(len(module_paths), 1)
        self.assertEqual(module_paths[0], report_1.destination)

        self.assertTrue(method.report.update_progress.called)
        self.assertEqual(method.report.modules_state, constants.STATE_FAILED)
        self.assertEqual(method.report.modules_error_count, 1)
        self.assertEqual(len(method.report.modules_individual_errors), 1)
        self.assertEqual(method.report.modules_individual_errors[0], report_2.error_msg)

    @patch('__builtin__.open')
    @patch('pulp_puppet.plugins.importers.directory.shutil')
    @patch('pulp_puppet.plugins.importers.directory.json')
    @patch('pulp_puppet.plugins.importers.directory.tarfile')
    @patch('pulp_puppet.plugins.importers.directory.mkdtemp')
    def test_extract_metadata(self, *mocks):
        mock_mkdtemp, mock_tarfile, mock_json, mock_shutil, mock_open = mocks
        Member = namedtuple('Member', ['name'])
        module_path = '/build/modules/puppet-module.tar.gz'
        mock_mkdtemp.return_value = '/tmp/xx'
        members = [
            Member(name='puppet-module'),
            Member(name='puppet-module/manifests'),
            Member(name='puppet-module/spec'),
            Member(name='puppet-module/templates'),
            Member(name='puppet-module/tests'),
            Member(name='puppet-module/CHANGELOG'),
            Member(name='puppet-module/%s' % constants.MODULE_METADATA_FILENAME),
            Member(name='puppet-module/README'),
        ]
        tarball = Mock()
        tarball.getmembers = Mock(return_value=members)
        mock_tarfile.open = Mock(return_value=tarball)

        mock_fp = Mock()
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp
        mock_json.load.return_value = '12345'

        # test

        SynchronizeWithDirectory._extract_metadata(module_path)

        # validation

        mock_mkdtemp.assert_called_with(dir=os.path.dirname(module_path))
        mock_tarfile.open.assert_called_with(module_path)
        tarball.getmembers.assert_called_with()
        tarball.extract.assert_called_with(members[6], mock_mkdtemp())
        mock_open.assert_called_with(os.path.join(mock_mkdtemp(), members[6].name))
        mock_json.load.assert_called_with(mock_fp)
        mock_shutil.rmtree.assert_called_with(mock_mkdtemp())


class TestListener(TestCase):

    def test_constructor(self):
        synchronizer = Mock()
        downloader = Mock()

        listener = DownloadListener(synchronizer, downloader)

        self.assertEqual(listener.synchronizer, synchronizer)
        self.assertEqual(listener.downloader, downloader)

    def test_progress(self):
        request = Mock()
        request.canceled = False
        downloader = Mock()
        report = Mock()

        # test

        listener = DownloadListener(request, downloader)
        listener.download_progress(report)

        # validation

        self.assertFalse(downloader.cancel.called)

    def test_progress_with_canceled(self):
        request = Mock()
        request.canceled = True
        downloader = Mock()
        report = Mock()

        # test

        listener = DownloadListener(request, downloader)
        listener.download_progress(report)

        # validation

        self.assertTrue(downloader.cancel.called)
