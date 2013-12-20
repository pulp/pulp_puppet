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

from ....base_cli import ExtensionTests
from pulp_puppet.common.constants import DISPLAY_MODULES_THRESHOLD, TYPE_PUPPET_MODULE
from pulp_puppet.extensions.admin.repo.remove import RemoveCommand, DESC_REMOVE


class RemovePuppetModulesCommand(ExtensionTests):

    def setUp(self):
        super(RemovePuppetModulesCommand, self).setUp()
        self.command = RemoveCommand(self.context)

    def test_defaults(self):
        self.assertTrue(isinstance(self.command, UnitRemoveCommand))
        self.assertEqual('remove', self.command.name)
        self.assertEqual(DESC_REMOVE, self.command.description)
        self.assertEqual(DISPLAY_MODULES_THRESHOLD, self.command.max_units_displayed)
        # uses default remove method
        self.assertEqual(self.command.method, self.command.run)

    @mock.patch('pulp_puppet.extensions.admin.repo.units_display.get_formatter_for_type')
    def test_get_formatter_for_type(self, mock_formatter):
        context = mock.MagicMock()
        command = RemoveCommand(context)

        command.get_formatter_for_type(TYPE_PUPPET_MODULE)
        mock_formatter.assert_called_once_with(TYPE_PUPPET_MODULE)
