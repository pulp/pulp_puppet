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
"""
Tests for pulp_rpm.plugins.migrations.0001_puppet_module_unit_checksum
"""
import unittest

from mock import patch
from pulp.server.db.migrate.models import _import_all_the_way
from pulp.devel.mock_cursor import MockCursor

from pulp_puppet.common import constants


class Test0001PuppetModuleUnitChecksum(unittest.TestCase):
    """
    Test the FilesDistributor object.
    """

    @patch('pulp_puppet.plugins.importers.metadata.calculate_checksum')
    @patch('pulp.server.managers.content.query.ContentQueryManager', autospec=True)
    def test_migration(self, mock_query_manager, mock_calc_checksum):
        migration = _import_all_the_way('pulp_puppet.plugins.migrations.0001_puppet_'
                                             'module_unit_checksum')
        storage_path = '/foo/storage'
        mock_calc_checksum.return_value = "foo_checksum"
        unit = {'_storage_path': storage_path}
        mock_query_manager.return_value.get_content_unit_collection.return_value.find.return_value = MockCursor([unit])
        migration.migrate()
        mock_calc_checksum.assert_called_once_with(storage_path)
        mock_query_manager.return_value.get_content_unit_collection.return_value.save.assert_called_once()
        target_unit = mock_query_manager.return_value.get_content_unit_collection.return_value.save.call_args[0][0]
        self.assertEquals(target_unit['checksum'], 'foo_checksum')
        self.assertEquals(target_unit['checksum_type'], constants.DEFAULT_HASHLIB)


