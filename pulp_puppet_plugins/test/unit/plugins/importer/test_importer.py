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

import unittest

from mock import Mock, patch

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import importer
from pulp_puppet.plugins.importers.importer import PuppetModuleImporter


class TestImporter(unittest.TestCase):

    def test_entry_point(self):
        ret = importer.entry_point()
        self.assertEqual(ret[0], PuppetModuleImporter)
        self.assertTrue(isinstance(ret[1], dict))


class TestPuppetModuleImporter(unittest.TestCase):

    @patch('pulp_puppet.plugins.importers.importer.SynchronizeWithDirectory')
    def test_directory_synchronization(self, mock_class):
        conduit = Mock()
        repository = Mock()
        config = {constants.CONFIG_FEED: 'http://host/tmp/%s' % constants.MANIFEST_FILENAME}
        mock_inst = Mock(return_value=1234)
        mock_class.return_value = mock_inst

        # test

        plugin = PuppetModuleImporter()
        report = plugin.sync_repo(repository, conduit, config)

        # validation

        mock_class.assert_called_with(conduit, config)
        mock_inst.assert_called_with(repository)
        self.assertEqual(report, mock_inst.return_value)

    @patch('pulp_puppet.plugins.importers.importer.SynchronizeWithPuppetForge')
    def test_forge_synchronization(self, mock_class):
        conduit = Mock()
        repository = Mock()
        config = {constants.CONFIG_FEED: 'http://host/tmp/forge'}
        mock_inst = Mock(return_value=1234)
        mock_class.return_value = mock_inst

        # test

        plugin = PuppetModuleImporter()
        report = plugin.sync_repo(repository, conduit, config)

        # validation

        mock_class.assert_called_with(repository, conduit, config)
        mock_inst.assert_called_with()
        mock_class.return_value = mock_inst

    @patch('pulp_puppet.plugins.importers.upload.handle_uploaded_unit')
    def testUploadUnit(self, mock_handle_upload):
        module_importer = PuppetModuleImporter()
        mock_handle_upload.return_value = {'success_flag': True, 'summary': '', 'details': {}}
        report = module_importer.upload_unit(Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
        self.assertTrue(report['success_flag'])

    @patch('pulp_puppet.plugins.importers.upload.handle_uploaded_unit')
    def TestUploadUnitFails(self, mock_handle_upload):
        module_importer = PuppetModuleImporter()
        mock_handle_upload.side_effect = Exception('bad')
        report = module_importer.upload_unit(Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
        self.assertFalse(report['success_flag'])
        self.assertEquals(report['summary'], 'bad')
