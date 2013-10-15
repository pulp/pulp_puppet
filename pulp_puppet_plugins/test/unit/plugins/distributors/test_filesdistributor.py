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
Tests for pulp_rpm.plugins.distributors.iso_distributor.distributor
"""
import os
import shutil
import tempfile
import unittest

from mock import MagicMock, patch
from pulp.devel.mock_distributor import get_basic_config
from pulp.plugins.model import Unit
from pulp.plugins.config import PluginCallConfiguration

from pulp_puppet.common import constants
from pulp_puppet.plugins.distributors import configuration
from pulp_puppet.plugins.distributors import filesdistributor


class TestEntryPoint(unittest.TestCase):
    """
    Test the entry_point method. This is really just to get good coverage numbers, but hey.
    """
    def test_entry_point(self):
        files_distributor, config = filesdistributor.entry_point()
        self.assertEqual(files_distributor, filesdistributor.PuppetFilesDistributor)
        self.assertEqual(config, {})


class TestPuppetFilesDistributor(unittest.TestCase):
    """
    Test the FilesDistributor object.
    """
    def setUp(self):
        self.distributor = filesdistributor.PuppetFilesDistributor()
        self.temp_dir = tempfile.mkdtemp()
        self.files_path = os.path.join(self.temp_dir, 'files')
        os.makedirs(self.files_path)
        self.unit = MagicMock()
        self.unit.storage_path = os.path.join(self.temp_dir, 'source', "foo.tgz")
        self.config = PluginCallConfiguration({constants.CONFIG_FILES_HTTPS_DIR: self.files_path}, {})
        self.repo = self._get_default_repo()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _get_default_repo(self):
        repo = MagicMock()
        repo.id = 'awesome_repo'
        return repo

    def test_metadata(self):
        metadata = filesdistributor.PuppetFilesDistributor.metadata()
        self.assertEqual(metadata['id'], constants.DISTRIBUTOR_FILES_TYPE_ID)
        self.assertEqual(metadata['display_name'], 'Puppet Files Distributor')
        self.assertEqual(metadata['types'], [constants.TYPE_PUPPET_MODULE])

    def test_validate_config_no_files_dir_specified(self):
        config = PluginCallConfiguration({}, {})
        return_val, error_message = self.distributor.validate_config(self.repo, config, None)
        self.assertTrue(return_val)
        self.assertIsNone(error_message)

    def test_validate_config_none_files_dir_specified(self):
        config = PluginCallConfiguration({constants.CONFIG_FILES_HTTPS_DIR: None}, {})
        return_val, error_message = self.distributor.validate_config(self.repo, config, None)
        self.assertFalse(return_val)

    def test_validate_config_files_dir_does_not_exist(self):
        config = PluginCallConfiguration({constants.CONFIG_FILES_HTTPS_DIR: '/foo/bar/baz'}, {})
        return_val, error_message = self.distributor.validate_config(self.repo, config, None)
        self.assertFalse(return_val)

    def test_validate_config_files_dir_override_from_config(self):
        tempdir = tempfile.mkdtemp()
        try:
            config = PluginCallConfiguration({constants.CONFIG_FILES_HTTPS_DIR: tempdir}, {})
            return_val, error_message = self.distributor.validate_config(self.repo, config, None)
            self.assertTrue(return_val)
        finally:
            shutil.rmtree(tempdir)

    def test_get_hosting_locations(self):
        locations = self.distributor.get_hosting_locations(self.repo, self.config)
        self.assertEquals(1, len(locations))
        self.assertEquals(os.path.join(self.files_path, self.repo.id), locations[0])

    def test_get_paths_for_unit(self):
        paths = self.distributor.get_paths_for_unit(self.unit)
        self.assertEquals(1, len(paths))
        self.assertEquals('foo.tgz', paths[0])

    def test_publish_metadata_for_unit(self):
        unit = Unit(constants.TYPE_PUPPET_MODULE, {'name': 'foo'}, {},
                    os.path.join(self.temp_dir, 'foo.tgz'))
        metadata_distributor = filesdistributor.PuppetFilesDistributor()
        metadata_distributor.metadata_csv_writer = MagicMock()
        metadata_distributor.publish_metadata_for_unit(unit)
        metadata_distributor.metadata_csv_writer.writerow.assert_called_with(['foo.tgz'])