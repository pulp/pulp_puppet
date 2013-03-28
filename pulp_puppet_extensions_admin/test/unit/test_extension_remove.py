# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock

from pulp.client.commands.unit import UnitRemoveCommand

import base_cli
from pulp_puppet.common.constants import DISPLAY_MODULES_THRESHOLD
from pulp_puppet.extensions.admin.repo.remove import RemoveCommand, DESC_REMOVE


class RemovePuppetModulesCommand(base_cli.ExtensionTests):

    def setUp(self):
        super(RemovePuppetModulesCommand, self).setUp()
        self.command = RemoveCommand(self.context)

    def test_defaults(self):
        self.assertTrue(isinstance(self.command, UnitRemoveCommand))
        self.assertEqual('remove', self.command.name)
        self.assertEqual(DESC_REMOVE, self.command.description)
        self.assertEqual(DISPLAY_MODULES_THRESHOLD, self.command.module_count_threshold)
        # uses default remove method
        self.assertEqual(self.command.method, self.command.run)

    @mock.patch('pulp_puppet.extensions.admin.repo.units_display.display_modules')
    def test_succeeded(self, mock_display):
        # Setup
        fake_modules = 'm'
        fake_task = mock.MagicMock()
        fake_task.result = fake_modules

        # Test
        self.command.succeeded(fake_task)

        # Verify
        mock_display.assert_called_once_with(self.prompt, fake_modules, self.command.module_count_threshold)
