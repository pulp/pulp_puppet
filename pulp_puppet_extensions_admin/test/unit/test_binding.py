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

import mock
from pulp.client.commands.consumer.bind import OPTION_DISTRIBUTOR_ID

from pulp_puppet.common import constants
from pulp_puppet.extensions.admin.consumer import bind


class TestBindCommand(unittest.TestCase):
    def setUp(self):
        self.command = bind.BindCommand(mock.MagicMock())

    def test_add_distributor_option(self):
        # makes sure it does not add the distributor option
        for option in self.command.options:
            self.assertTrue(option.keyword != OPTION_DISTRIBUTOR_ID.keyword)

    def test_get_distributor_id(self):
        result = self.command.get_distributor_id({})

        self.assertEqual(result, constants.DISTRIBUTOR_TYPE_ID)


class TestUnbindCommand(unittest.TestCase):
    def setUp(self):
        self.command = bind.UnbindCommand(mock.MagicMock())

    def test_add_distributor_option(self):
        # makes sure it does not add the distributor option
        for option in self.command.options:
            self.assertTrue(option.keyword != OPTION_DISTRIBUTOR_ID.keyword)

    def test_get_distributor_id(self):
        result = self.command.get_distributor_id({})

        self.assertEqual(result, constants.DISTRIBUTOR_TYPE_ID)
