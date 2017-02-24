import unittest

from pulp_puppet.common.constants import TYPE_PUPPET_MODULE
from pulp_puppet.extensions.admin.repo import units_display


class UnitsDisplayTests(unittest.TestCase):

    def test_get_formatter_for_type(self):
        formatter = units_display.get_formatter_for_type(TYPE_PUPPET_MODULE)
        self.assertEquals('foo-bar-baz', formatter({'author': 'foo',
                                                    'name': 'bar',
                                                    'version': 'baz'}))

    def test_get_formatter_for_type_raises_value_error(self):
        self.assertRaises(ValueError, units_display.get_formatter_for_type, 'foo-type')
