import unittest

import mock

from pulp_puppet.plugins.importers import copier


class CopierTests(unittest.TestCase):

    def test_copy_units_only_specified(self):
        # Setup
        conduit = mock.MagicMock()
        specified_units = ['a', 'b']

        # Test
        copier.copy_units(conduit, specified_units)

        # Verify
        self.assertEqual(0, conduit.get_source_units.call_count)

        self.assertEqual(len(specified_units), conduit.associate_unit.call_count)
        self._assert_associated_units(conduit, specified_units)

    def _assert_associated_units(self, conduit, units):
        all_call_args = conduit.associate_unit.call_args_list
        for unit, call_args in zip(units, all_call_args):
            self.assertEqual(call_args[0][0], unit)
