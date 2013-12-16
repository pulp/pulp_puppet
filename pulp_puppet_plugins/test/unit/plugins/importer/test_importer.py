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

from pulp_puppet.plugins.importers import importer
from pulp_puppet.plugins.importers.importer import PuppetModuleImporter


class TestImporter(unittest.TestCase):
    def test_entry_point(self):
        ret = importer.entry_point()
        self.assertEqual(ret[0], PuppetModuleImporter)
        self.assertTrue(isinstance(ret[1], dict))


class TestPuppetModuleImporter(unittest.TestCase):

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
