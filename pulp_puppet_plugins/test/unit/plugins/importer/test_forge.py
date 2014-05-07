# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
import shutil
import tempfile
import unittest

import mock

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, SyncReport, Unit

from pulp_puppet.common import constants, model, sync_progress
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
            constants.CONFIG_FEED : FEED,
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

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._add_new_module')
    def test__do_import_modules_handles_cancel(self, _add_new_module):
        """
        Make sure _do_import_modules() handles the cancel signal correctly. We'll do this by setting
        up a side effect with the first module to call cancel so the second never happens.
        """
        swpf = SynchronizeWithPuppetForge(self.repo, self.conduit, self.config)

        def _side_effect(*args, **kwargs):
            swpf.cancel()

        _add_new_module.side_effect = _side_effect
        metadata = model.RepositoryMetadata()
        module_1 = model.Module('module_1', '1.0.0', 'simon')
        module_2 = model.Module('module_2', '2.0.3', 'garfunkel')
        metadata.modules = [module_1, module_2]

        swpf._do_import_modules(metadata)

        # If _add_new_module was called exactly once, then our cancel was successful because the
        # first call to _add_new_module set the cancel flag, and the loop exited the next time.
        # Because dictionaries are involved in the order in which the modules get downloaded, we
        # don't have a documented guarantee about which module will be the one. Therefore, we'll
        # just assert that only one was downloaded and that it was one of the two.
        self.assertEqual(_add_new_module.call_count, 1)
        downloaded_module = _add_new_module.mock_calls[0][1][1]
        self.assertTrue(downloaded_module in [module_1, module_2])

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

    def test_synchronize(self):
        # Test
        report = self.method().build_final_report()

        # Verify

        # Units copied to simulated Pulp storage
        expected_module_filenames = ['adob-good-2.0.0.tar.gz', 'jdob-valid-1.1.0.tar.gz']
        for f in expected_module_filenames:
            expected_path = os.path.join(MOCK_PULP_STORAGE_LOCATION, f)
            self.assertTrue(os.path.exists(expected_path))

        # Final Report
        self.assertTrue(report.success_flag)
        self.assertTrue(report.summary['total_execution_time'] is not None)
        self.assertTrue(report.summary['total_execution_time'] > -1)

        self.assertEqual(report.details['total_count'], 2)
        self.assertEqual(report.details['finished_count'], 2)
        self.assertEqual(report.details['error_count'], 0)

        # Progress Reporting
        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 1)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertEqual(pr.metadata_error_message, None)
        self.assertEqual(pr.metadata_exception, None)
        self.assertEqual(pr.metadata_traceback, None)

        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_error_count, 0)
        self.assertEqual(pr.modules_finished_count, 2)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertEqual(pr.modules_error_message, None)
        self.assertEqual(pr.modules_exception, None)
        self.assertEqual(pr.modules_traceback, None)
        self.assertEqual(pr.modules_individual_errors, [])

        # Number of times update was called on the progress report
        self.assertEqual(self.conduit.set_progress.call_count, 9)

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

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._resolve_remove_units')
    def test_synchronize_with_remove_units(self, mock_resolve):
        # Setup
        remove_me = 'valid-1.1.0-jdob'
        mock_resolve.return_value = [remove_me]

        self.conduit = UnitsMockConduit()
        self.method.sync_conduit = self.conduit

        self.config.repo_plugin_config[constants.CONFIG_REMOVE_MISSING] = 'true'

        # Test
        report = self.method()

        # Verify
        self.assertEqual(1, self.conduit.remove_unit.call_count)

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
    def test_import_modules_exception(self, mock_import):
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

    @mock.patch('pulp_puppet.plugins.importers.forge.SynchronizeWithPuppetForge._add_new_module')
    def test_do_import_add_exception(self, mock_add):
        # Setup
        mock_add.side_effect = Exception()

        # Test
        report = self.method().build_final_report()

        # Verify

        # Failed modules still represent a successful sync and import modules
        # step as far as states are concerned. But at the individual module
        # level, the errors should be stored per failed module and the counts
        # accurately reflect successes v. failures.

        self.assertTrue(report.success_flag)

        pr = self.method.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)

        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_finished_count, 0)
        self.assertEqual(pr.modules_error_count, 2)
        self.assertEqual(len(pr.modules_individual_errors), 2)
        # Make sure the individual_errors are the correct format
        for error in pr.modules_individual_errors:
            self.assertEqual(set(error.keys()), set(['exception', 'traceback', 'module', 'author']))
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertTrue(pr.modules_error_message is None)
        self.assertTrue(pr.modules_exception is None)
        self.assertTrue(pr.modules_traceback is None)
