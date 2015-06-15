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
