import unittest

import mock
from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import copier


class CopierTests(unittest.TestCase):

    def test_copy_units_all_units(self):
        # Setup
        conduit = mock.MagicMock()
        all_source_units = ['a', 'b', 'c']  # content is irrelevant
        conduit.get_source_units.return_value = all_source_units

        # Test
        returned = copier.copy_units(conduit, None)

        # Verify
        self.assertEqual(returned, all_source_units)
        self.assertEqual(1, conduit.get_source_units.call_count)
        call_args = conduit.get_source_units.call_args
        self.assertTrue('criteria' in call_args[1])
        self.assertTrue(isinstance(call_args[1]['criteria'], UnitAssociationCriteria))
        self.assertEqual(call_args[1]['criteria'].type_ids, [constants.TYPE_PUPPET_MODULE])

        self.assertEqual(len(all_source_units), conduit.associate_unit.call_count)
        self._assert_associated_units(conduit, all_source_units)

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
