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

from uuid import uuid4
from unittest import TestCase
from collections import namedtuple
from urlparse import urljoin

from mock import patch, Mock, ANY

from pulp_puppet.common import constants
from pulp_puppet.common.model import Module
from pulp_puppet.plugins.importers.directory import SynchronizeWithDirectory, DownloadListener, Inventory
from pulp_puppet.common.sync_progress import SyncProgressReport


class TestSynchronizeWithDirectory(TestCase):

    def test_constructor(self):
        conduit = Mock()
        config = {}

        # testing

        method = SynchronizeWithDirectory(conduit, config)

        # validation

        self.assertEqual(method.conduit, conduit)
        self.assertEqual(method.config, config)

    def test_feed_url(self):
        feed_url = 'http://abc.com/repository'
        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        # testing

        method = SynchronizeWithDirectory(conduit, config)

        # validation

        self.assertEqual(method.feed_url(), feed_url + '/')

    def test_cancel(self):
        conduit = Mock()
        config = {}

        # testing

        method = SynchronizeWithDirectory(conduit, config)
        method.cancel()

        # validation

        self.assertTrue(method.canceled)

    @patch('shutil.rmtree')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._run')
    @patch('pulp_puppet.plugins.importers.directory.mkdtemp')
    @patch('pulp_puppet.plugins.importers.directory.Inventory')
    def test_call(self, mock_inventory, mock_mkdtemp, mock_run, mock_rmtree):
        conduit = Mock()
        config = {constants.CONFIG_FEED: 'http://host/root/PULP_MANAFEST'}
        repository = Mock()
        repository.working_dir = 'working'

        mock_mkdtemp.return_value = '/abc'

        # testing

        method = SynchronizeWithDirectory(conduit, config)
        report = method(repository)

        # validation

        self.assertFalse(method.canceled)
        self.assertTrue(isinstance(method.report, SyncProgressReport))
        self.assertTrue(isinstance(report, SyncProgressReport))
        mock_inventory.assert_called_with(conduit)
        mock_mkdtemp.assert_called_with(dir=repository.working_dir)
        mock_run.assert_called_with(mock_inventory())
        mock_rmtree.assert_called_with(os.path.join(repository.working_dir, mock_mkdtemp()))

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_manifest')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._import_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._purge_unwanted_modules')
    def test_run(self, *mocks):
        config = {}
        conduit = Mock()
        inventory = Mock()

        _purge_unwanted_modules = mocks[0]
        _import_modules = mocks[1]
        _import_modules.return_value = []
        _fetch_modules = mocks[2]
        _fetch_modules.return_value = []
        _fetch_manifest = mocks[3]
        _fetch_manifest.return_value = 'path,sum,size'

        # testing

        method = SynchronizeWithDirectory(conduit, config)
        method._run(inventory)

        # validation

        _fetch_manifest.assert_called_with()
        _fetch_modules.assert_called_with(_fetch_manifest())
        _import_modules.assert_called_with(inventory, _fetch_modules())
        _purge_unwanted_modules.assert_called_with(inventory, _import_modules())

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_manifest')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._fetch_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._import_modules')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._purge_unwanted_modules')
    def test_run_fetch_manifest_failed(self, *mocks):
        config = {}
        conduit = Mock()
        inventory = Mock()

        _purge_unwanted_modules = mocks[0]
        _import_modules = mocks[1]
        _import_modules.return_value = []
        _fetch_modules = mocks[2]
        _fetch_modules.return_value = []
        _fetch_manifest = mocks[3]
        _fetch_manifest.return_value = None

        # testing

        method = SynchronizeWithDirectory(conduit, config)
        method._run(inventory)

        # validation

        _fetch_manifest.assert_called_with()
        self.assertFalse(_fetch_modules.called)
        self.assertFalse(_import_modules.called)
        self.assertFalse(_purge_unwanted_modules.called)

    @patch('pulp_puppet.plugins.importers.directory.URL_TO_DOWNLOADER')
    @patch('pulp_puppet.plugins.importers.directory.importer_config_to_nectar_config')
    @patch('pulp_puppet.plugins.importers.directory.DownloadListener')
    def test_download(self, mock_listener, mock_nectar_config, mock_downloader_mapping):
        mock_nectar_config.return_value = Mock()

        mock_http_downloader = Mock()
        mock_http_class = Mock(return_value=mock_http_downloader)
        mock_downloader_mapping.__getitem__.return_value = mock_http_class

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

        method = SynchronizeWithDirectory(conduit, config)
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

        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}
        succeeded_report = Mock()

        mock_download.return_value = [succeeded_report], []
        mock_get_value.return_value = 'A,B,C\nD,E,F\n'

        # test

        method = SynchronizeWithDirectory(conduit, config)
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

        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}
        failed_report = Mock()
        failed_report.error_msg = 'just up and failed'

        mock_download.return_value = [], [failed_report]

        # test

        method = SynchronizeWithDirectory(conduit, config)
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

        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        manifest = [('path1', 'AA', 10), ('path2', 'BB', 20)]

        report_1 = Mock()
        report_1.destination = os.path.join(tmp_dir, manifest[0][0])
        report_2 = Mock()
        report_2.destination = os.path.join(tmp_dir, manifest[1][0])
        mock_download.return_value = [report_1, report_2], []

        # test

        method = SynchronizeWithDirectory(conduit, config)
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

        self.assertTrue(method.report.update_progress.called)
        self.assertEqual(method.report.module_state, constants.STATE_SUCCESS)

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._download')
    def test_fetch_modules_failures(self, mock_download):
        tmp_dir = '/tmp/puppet-testing'
        feed_url = 'http://host/root/'

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

        method = SynchronizeWithDirectory(conduit, config)
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
        self.assertEqual(method.report.module_state, constants.STATE_FAILED)
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

        puppet_manifest = SynchronizeWithDirectory._extract_metadata(module_path)

        # validation

        mock_mkdtemp.assert_called_with(dir=os.path.dirname(module_path))
        mock_tarfile.open.assert_called_with(module_path)
        tarball.getmembers.assert_called_with()
        tarball.extract.assert_called_with(members[6], mock_mkdtemp())
        mock_open.assert_called_with(os.path.join(mock_mkdtemp(), members[6].name))
        mock_json.load.assert_called_with(mock_fp)
        mock_shutil.rmtree.assert_called_with(mock_mkdtemp())

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._add_module')
    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._extract_metadata')
    def test_import_modules(self, mock_extract, mock_add):
        feed_url = 'http://host/root/PULP_MANAFEST'

        conduit = Mock()
        config = {constants.CONFIG_FEED: feed_url}

        mock_inventory = Mock()
        mock_inventory.already_associated.side_effect = [False, True, False]

        manifests = [
            {'name': 'pulp1', 'author': 'john', 'version': '1.0'},
            {'name': 'pulp2', 'author': 'john', 'version': '2.0'},
            {'name': 'pulp3', 'author': 'john', 'version': '3.0'},
        ]

        mock_extract.side_effect = manifests

        module_paths = [
            '/tmp/module_1',
            '/tmp/module_2',
            '/tmp/module_3',
        ]

        # test

        method = SynchronizeWithDirectory(conduit, config)
        imported_modules = method._import_modules(mock_inventory, module_paths)

        # validation

        mock_add.assert_any_with(module_paths[0], ANY)
        mock_add.assert_any_with(module_paths[2], ANY)

        # should only be modules 1 and 3.  2 already associated.
        self.assertEqual(len(imported_modules), 2)
        self.assertEqual(imported_modules[0], manifests[0])
        self.assertEqual(imported_modules[1], manifests[2])

    @patch('pulp_puppet.plugins.importers.directory.SynchronizeWithDirectory._extract_metadata')
    def test_import_modules_cancelled(self, mock_extract):
        config = {}
        mock_conduit = Mock()
        mock_inventory = Mock()

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method.canceled = True
        imported_modules = method._import_modules(mock_inventory, ['/path1', '/path2'])

        # validation

        self.assertFalse(mock_extract.called)
        self.assertEqual(imported_modules, [])

    @patch('pulp_puppet.plugins.importers.directory.shutil')
    def test_add_module(self, mock_shutil):
        module_path = '/tmp/mod.tar.gz'
        feed_url = 'http://host/root/PULP_MANAFEST'
        unit_key = {'name': 'puppet-module'}
        unit_metadata = {'A': 1, 'B': 2}
        unit = Mock()
        unit.storage_path = '/tmp/%s' % uuid4()

        mock_conduit = Mock()
        mock_conduit.init_unit = Mock(return_value=unit)

        config = {constants.CONFIG_FEED: feed_url}

        mock_module = Mock()
        mock_module.unit_key = Mock(return_value=unit_key)
        mock_module.unit_metadata = Mock(return_value=unit_metadata)
        mock_module.filename = Mock(return_value='puppet-module')

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method._add_module(module_path, mock_module)

        # validation

        mock_conduit.init_unit.assert_called_with(
            constants.TYPE_PUPPET_MODULE, unit_key, unit_metadata, mock_module.filename())
        mock_shutil.copy.assert_called_with(module_path, unit.storage_path)

    @patch('pulp_puppet.plugins.importers.directory.shutil')
    def test_add_module_not_copied(self, mock_shutil):
        module_path = '/tmp/mod.tar.gz'
        feed_url = 'http://host/root/PULP_MANAFEST'
        unit_key = {'name': 'puppet-module'}
        unit_metadata = {'A': 1, 'B': 2}
        unit = Mock()
        unit.storage_path = os.path.join(os.getcwd(), __file__)

        mock_conduit = Mock()
        mock_conduit.init_unit = Mock(return_value=unit)

        config = {constants.CONFIG_FEED: feed_url}

        mock_module = Mock()
        mock_module.unit_key = Mock(return_value=unit_key)
        mock_module.unit_metadata = Mock(return_value=unit_metadata)
        mock_module.filename = Mock(return_value='puppet-module')

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method._add_module(module_path, mock_module)

        # validation

        self.assertFalse(mock_shutil.copy.called)

    def test_purge_unwanted_modules(self):
        imported_modules = [{'A': 1}, {'B': 2}]
        unwanted_modules = [{'A': 3}, {'B': 4}]

        mock_conduit = Mock()

        config = Mock()
        config.get_boolean = Mock(side_effect={constants.CONFIG_REMOVE_MISSING: True}.get)

        mock_inventory = Mock()
        mock_inventory.unwanted_modules = Mock(return_value=unwanted_modules)

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method._purge_unwanted_modules(mock_inventory, imported_modules)

        # validation

        mock_inventory.unwanted_modules.assert_called_with(imported_modules)
        mock_conduit.remove_unit.assert_any_with(unwanted_modules[0])
        mock_conduit.remove_unit.assert_any_with(unwanted_modules[1])
        self.assertEqual(mock_conduit.remove_unit.call_count, 2)

    def test_purge_unwanted_modules_not_requested(self):
        mock_conduit = Mock()

        config = Mock()
        config.get_boolean = Mock(side_effect={constants.CONFIG_REMOVE_MISSING: False}.get)

        mock_inventory = Mock()

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method._purge_unwanted_modules(mock_inventory, [])

        # validation

        self.assertFalse(mock_inventory.unwanted_modules.called)
        self.assertFalse(mock_conduit.remove_unit.called)
        self.assertFalse(mock_conduit.remove_unit.called)

    def test_purge_unwanted_modules_default(self):
        mock_conduit = Mock()

        config = Mock()
        config.get_boolean = Mock(side_effect={}.get)

        mock_inventory = Mock()

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method._purge_unwanted_modules(mock_inventory, [])

        # validation

        self.assertFalse(mock_inventory.unwanted_modules.called)
        self.assertFalse(mock_conduit.remove_unit.called)
        self.assertFalse(mock_conduit.remove_unit.called)

    def test_purge_unwanted_modules_canceled(self):
        mock_conduit = Mock()

        config = Mock()
        config.get_boolean = Mock(side_effect={constants.CONFIG_REMOVE_MISSING: True}.get)

        mock_inventory = Mock()
        mock_inventory.unwanted_modules = Mock(return_value=['A', 'B'])

        # test

        method = SynchronizeWithDirectory(mock_conduit, config)
        method.canceled = True
        method._purge_unwanted_modules(mock_inventory, [])

        # validation

        self.assertFalse(mock_conduit.remove_unit.called)
        self.assertFalse(mock_conduit.remove_unit.called)


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


class TestInventory(TestCase):

    @patch('pulp_puppet.plugins.importers.directory.Inventory._associated')
    def test_constructor(self, mock_associated):
        associated = set()
        mock_associated.return_value = associated
        conduit = Mock()

        # test

        inventory = Inventory(conduit)

        # validation

        mock_associated.assert_called_once_with(conduit)
        self.assertEqual(inventory.associated, associated)

    @patch('pulp_puppet.plugins.importers.directory.UnitAssociationCriteria')
    def test_associated(self, mock_criteria):
        unit_1 = Mock()
        unit_1.metadata = {}
        unit_1.unit_key = {'name': 'pulp1', 'author': 'john', 'version': '1.0'}
        unit_2 = Mock()
        unit_2.metadata = {}
        unit_2.unit_key = {'name': 'pulp2', 'author': 'josh', 'version': '2.0'}
        units = [unit_1, unit_2]

        conduit = Mock()
        conduit.get_units = Mock(return_value=units)

        criteria = Mock()
        mock_criteria.return_value = criteria

        # test

        inventory = Inventory(conduit)

        # validation

        conduit.get_units.assert_called_once_with(criteria=criteria, as_generator=True)
        mock_criteria.assert_called_once_with(
            type_ids=[constants.TYPE_PUPPET_MODULE], unit_fields=Module.UNIT_KEY_NAMES)
        self.assertEqual(len(inventory.associated), 2)
        self.assertTrue(tuple(unit_1.unit_key.items()) in inventory.associated)
        self.assertTrue(tuple(unit_2.unit_key.items()) in inventory.associated)

    @patch('pulp_puppet.plugins.importers.directory.UnitAssociationCriteria')
    def test_already_associated(self, mock_criteria):
        associated = [
            {'name': 'pulp1', 'author': 'john', 'version': '1.0'},
            {'name': 'pulp2', 'author': 'josh', 'version': '2.0'}
        ]

        conduit = Mock()
        conduit.get_units = Mock(return_value=[])

        criteria = Mock()
        mock_criteria.return_value = criteria

        # test and validation

        module = Mock()
        inventory = Inventory(conduit)
        inventory.associated = set()
        inventory.associated.add(tuple(associated[0].items()))
        inventory.associated.add(tuple(associated[1].items()))

        # should be associated
        module.unit_key = Mock(return_value=associated[0])
        self.assertTrue(inventory.already_associated(module))

        # should be associated
        module.unit_key = Mock(return_value=associated[1])
        self.assertTrue(inventory.already_associated(module))

        # should not be associated
        module.unit_key = Mock(return_value={})
        self.assertFalse(inventory.already_associated(module))


    @patch('pulp_puppet.plugins.importers.directory.UnitAssociationCriteria')
    def test_unwanted_modules(self, mock_criteria):
        associated = [
            {'name': 'pulp1', 'author': 'john', 'version': '1.0'},
            {'name': 'pulp2', 'author': 'josh', 'version': '2.0'},
            {'name': 'pulp3', 'author': 'josh', 'version': '3.0'}
        ]

        conduit = Mock()
        conduit.get_units = Mock(return_value=[])

        criteria = Mock()
        mock_criteria.return_value = criteria

        # test and validation

        inventory = Inventory(conduit)
        inventory.associated = set()
        inventory.associated.add(tuple(associated[0].items()))
        inventory.associated.add(tuple(associated[1].items()))
        inventory.associated.add(tuple(associated[2].items()))

        wanted = associated[:1]
        unwanted = inventory.unwanted_modules(wanted)
        self.assertEqual(len(unwanted), 2)
        self.assertTrue(associated[1] in unwanted)
        self.assertTrue(associated[2] in unwanted)
