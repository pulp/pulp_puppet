# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
import unittest

import mock
from pulp.client.commands.repo.upload import UploadCommand, OPTION_FILE

import base_cli
from pulp_puppet.common import constants
from pulp_puppet.common.model import Module
from pulp_puppet.extensions.admin.repo import upload

MODULES_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../data/good-modules/jdob-valid/pkg'

class UploadModuleCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(UploadModuleCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = upload.UploadModuleCommand(self.context, self.upload_manager)
        self.filename = os.path.join(MODULES_DIR, 'jdob-valid-1.0.0.tar.gz')

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))

    def test_generate_unit_key(self):
        # Test
        key = self.command.generate_unit_key(self.filename)

        # Verify
        expected_key = Module.generate_unit_key('valid', '1.0.0', 'jdob')
        self.assertEqual(key, expected_key)

    def test_generate_unit_key_complex_version(self):
        filename = os.path.join(MODULES_DIR, 'jdob-valid-1.0.0-rc1.tar.gz')

        # Test
        key = self.command.generate_unit_key(filename)

        # Verify
        expected_key = Module.generate_unit_key('valid', '1.0.0-rc1', 'jdob')
        self.assertEqual(key, expected_key)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(self.filename)
        self.assertEqual(type_id, constants.TYPE_PUPPET_MODULE)

    def test_matching_files_in_dir(self):
        # Test
        module_files = self.command.matching_files_in_dir(MODULES_DIR)

        # Verify

        # Simple filename check
        expected = set(['jdob-valid-1.0.0.tar.gz', 'jdob-valid-1.1.0.tar.gz'])
        found = set([os.path.basename(m) for m in module_files])
        self.assertEqual(expected, found)

        # Make sure the full paths are valid
        for m in module_files:
            self.assertTrue(os.path.exists(m))

    def test_validator_presence(self):
        option_file =  [opt for opt in self.command.options if opt.keyword == OPTION_FILE.keyword][0]
        self.assertEqual(self.command.validate_file_name, option_file.validate_func)


class TestValidateFileName(unittest.TestCase):
    def test_full(self):
        upload.UploadModuleCommand.validate_file_name(['/path/to/author-foo-1.0.0.tar.gz'])

    def test_relative(self):
        upload.UploadModuleCommand.validate_file_name(['author-foo-1.0.0.tar.gz'])

    def test_multiple(self):
        upload.UploadModuleCommand.validate_file_name(
            ['/author-foo-1.0.0.tar.gz', '/tmp/author-bar-0.2.0.tar.gz'])

    def test_complex_version(self):
        upload.UploadModuleCommand.validate_file_name(['/path/to/author-foo-1.0.0-rc1.tar.gz'])

    def test_require_author(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/-foo-1.0.0.tar.gz'])

    def test_require_name(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/author--1.0.0.tar.gz'])

    def test_require_version(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/author-foo.tar.gz'])

    def test_require_extension(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/author-foo-1.0.0.gz'])

    def test_empty(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, [''])

    def test_dir(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/tmp'])

    def test_root(self):
        self.assertRaises(ValueError, upload.UploadModuleCommand.validate_file_name, ['/'])
