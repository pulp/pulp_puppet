import unittest

from pulp_puppet.plugins.distributors import distributor
from pulp_puppet.plugins.distributors.distributor import PuppetModuleDistributor


class TestDistributor(unittest.TestCase):
    def test_entry_point(self):
        ret = distributor.entry_point()
        self.assertEqual(ret[0], PuppetModuleDistributor)
        self.assertTrue(isinstance(ret[1], dict))
