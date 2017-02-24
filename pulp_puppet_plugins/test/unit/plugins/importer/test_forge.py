import os
import shutil
import tempfile
import unittest

import mock

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, SyncReport, Unit

from pulp_puppet.common import constants, sync_progress
from pulp_puppet.plugins.importers.forge import SynchronizeWithPuppetForge


DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../../../data'
FEED = 'file://' + os.path.join(DATA_DIR, 'repos', 'valid')
INVALID_FEED = 'file://' + os.path.join(DATA_DIR, 'repos', 'invalid')

# Simulated location where Pulp will store synchronized units
MOCK_PULP_STORAGE_LOCATION = tempfile.mkdtemp(prefix='var-lib')


class MockConduit(mock.MagicMock):

    def build_success_report(self, summary, details):
        return SyncReport(True, -1, -1, -1, summary, details)

    def build_failure_report(self, summary, details):
        return SyncReport(False, -1, -1, -1, summary, details)

    def init_unit(self, type_id, unit_key, unit_metadata, relative_path):
        storage_path = os.path.join(MOCK_PULP_STORAGE_LOCATION, relative_path)
        return Unit(type_id, unit_key, unit_metadata, storage_path)


class UnitsMockConduit(MockConduit):

    def get_units(self, criteria=None):
        units = [
            Unit(constants.TYPE_PUPPET_MODULE, {'name': 'valid',
                                                'version': '1.1.0',
                                                'author': 'jdob'}, {}, ''),
            Unit(constants.TYPE_PUPPET_MODULE, {'name': 'good', 'version': '2.0.0',
                                                'author': 'adob'}, {}, ''),
        ]
        return units


class TestSynchronizeWithPuppetForge(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='puppet-sync-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)
        self.conduit = MockConduit()
        self.config = PluginCallConfiguration({}, {
            constants.CONFIG_FEED: FEED,
        })

        self.method = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MOCK_PULP_STORAGE_LOCATION)

    def test___init__(self):
        """
        Ensure the __init__() method works properly.
        """
        swpf = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)

        self.assertEqual(swpf.repo, self.repo)
        self.assertEqual(swpf.sync_conduit, self.conduit)
        self.assertEqual(swpf.config, self.config)
        self.assertTrue(isinstance(swpf.progress_report, sync_progress.SyncProgressReport))
        self.assertEqual(swpf.progress_report.conduit, self.conduit)
        self.assertEqual(swpf.downloader, None)
        self.assertEqual(swpf._canceled, False)

    def test_cancel_downloader_none(self):
        """
        Ensure correct operation of the cancel() method when the downloader is None.
        """
        swpf = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)

        # This should not blow up due to the downloader being None
        swpf.cancel()

        self.assertEqual(swpf._canceled, True)

    def test_cancel_downloader_set(self):
        """
        Ensure correct operation of the cancel() method when the downloader is set.
        """
        swpf = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)
        swpf.downloader = mock.MagicMock()

        swpf.cancel()

        self.assertEqual(swpf._canceled, True)
        swpf.downloader.cancel.assert_called_once_with()

    def test_synchronize_metadata_error(self):
        # Setup
        self.config.repo_plugin_config[constants.CONFIG_FEED] = INVALID_FEED

        # Test
        report = self.method().build_final_report()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 0)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)

    def test_synchronize_no_feed(self):
        # Setup
        del self.config.repo_plugin_config[constants.CONFIG_FEED]

        # Test
        report = self.method()

        # Verify
        self.assertTrue(not report.success_flag)
        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertTrue(len(pr.metadata_error_message) > 0)
        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._parse_metadata')
    def test_synchronize_no_metadata(self, mock_parse):
        # Setup
        mock_parse.return_value = None

        # Test
        report = self.method().build_final_report()

        # Verify
        self.assertTrue(report is not None)
        self.assertTrue(not report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._create_downloader')
    def test_parse_metadata_retrieve_exception(self, mock_create):
        # Setup
        mock_create.side_effect = Exception()

        # Test
        report = self.method().build_final_report()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertEqual(pr.metadata_query_total_count, None)
        self.assertEqual(pr.metadata_query_finished_count, None)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is not None)
        self.assertTrue(pr.metadata_exception is not None)
        self.assertTrue(pr.metadata_traceback is not None)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._create_downloader')
    def test_parse_metadata_retrieve_exception_canceled(self, mock_create):
        # Setup
        swpf = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)

        def _side_effect(*args, **kwargs):
            swpf.cancel()
            raise Exception("some download error")

        mock_create.side_effect = _side_effect

        # Test
        report = swpf().build_final_report()

        # Verify
        self.assertTrue(report.canceled_flag)

        pr = swpf.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_CANCELED)
        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.plugins.importers.downloaders.local.LocalDownloader.retrieve_metadata')
    def test_parse_metadata_parse_exception(self, mock_retrieve):
        # Setup
        mock_retrieve.return_value = ['not parsable json']

        # Test
        report = self.method().build_final_report()

        # Test
        self.assertTrue(not report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is not None)
        self.assertTrue(pr.metadata_exception is not None)
        self.assertTrue(pr.metadata_traceback is not None)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._do_import_modules')
    @mock.patch('pulp.server.managers.repo._common.get_working_directory', return_value='/tmp/')
    def test_import_modules_exception(self, mock_get_working_dir, mock_import):
        # Setup
        mock_import.side_effect = Exception()

        # Test
        report = self.method().build_final_report()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 1)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is None)
        self.assertTrue(pr.metadata_exception is None)
        self.assertTrue(pr.metadata_traceback is None)

        self.assertEqual(pr.modules_state, constants.STATE_FAILED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertTrue(pr.modules_error_message is not None)
        self.assertTrue(pr.modules_exception is not None)
        self.assertTrue(pr.modules_traceback is not None)
