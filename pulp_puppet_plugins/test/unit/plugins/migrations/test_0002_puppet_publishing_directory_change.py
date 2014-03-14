# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
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
Tests for pulp_rpm.plugins.migrations.0002_puppet_publishing_directory_change
"""
import os
import tempfile
import unittest

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way


class Test0002PuppetPublishingDirectoryChange(unittest.TestCase):
    """
    Test the migration of published puppet repo content to the new publish location
    """

    @patch('pulp_puppet.plugins.migrations.0002_puppet_publishing_directory_change.'
           'move_directory_contents_and_rename')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_migration(self, mock_listdir, mock_path_exists, mock_move_directory):
        migration = _import_all_the_way('pulp_puppet.plugins.migrations.0002_puppet_'
                                        'publishing_directory_change')
        migration.migrate()
        mock_listdir.assert_called_once_with('/var/www/pulp_puppet')
        mock_path_exists.assert_called_once_with('/var/www/pulp_puppet')

    def test_move_directory_contents_and_rename(self):
        test_old_publish_dir = tempfile.mkdtemp(prefix='test_0002_migration_old')
        old_http_publish_dir = os.path.join(test_old_publish_dir, 'http', 'repos')
        old_https_publish_dir = os.path.join(test_old_publish_dir, 'https', 'repos')
        os.makedirs(old_http_publish_dir)
        os.makedirs(old_https_publish_dir)

        test_new_publish_dir = tempfile.mkdtemp(prefix='test_0002_migration_new')
        new_http_publish_dir = os.path.join(test_new_publish_dir, 'puppet', 'http', 'repos')
        new_https_publish_dir = os.path.join(test_new_publish_dir, 'puppet', 'https', 'repos')

        migration = _import_all_the_way('pulp_puppet.plugins.migrations.0002_puppet_'
                                        'publishing_directory_change')
        migration.move_directory_contents_and_rename(test_old_publish_dir,
                                                     test_new_publish_dir,
                                                     os.path.basename(test_old_publish_dir),
                                                     'puppet')

        self.assertTrue(os.path.exists(new_http_publish_dir))
        self.assertTrue(os.path.exists(new_https_publish_dir))
        self.assertFalse(os.path.exists(test_old_publish_dir))

