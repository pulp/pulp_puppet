from unittest import TestCase

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_puppet.plugins.migrations.0004_standard_storage_path'

migration = _import_all_the_way(PATH_TO_MODULE)


class TestMigrate(TestCase):
    """
    Test migration 0004.
    """

    @patch(PATH_TO_MODULE + '.module_plan')
    @patch(PATH_TO_MODULE + '.Migration')
    def test_migrate(self, _migration, *functions):
        plans = []
        _migration.return_value.add.side_effect = plans.append

        # test
        migration.migrate()

        # validation
        self.assertEqual(
            plans,
            [
                f.return_value for f in functions
            ])
        _migration.return_value.assert_called_once_with()


class TestPlans(TestCase):

    @patch(PATH_TO_MODULE + '.connection.get_collection')
    def test_module(self, get_collection):
        # test
        plan = migration.module_plan()

        # validation
        get_collection.assert_called_once_with('units_puppet_module')
        self.assertEqual(plan.collection, get_collection.return_value)
        self.assertEqual(
            plan.key_fields,
            (
                'author',
                'name',
                'version'
            ))
        self.assertTrue(plan.join_leaf)
        self.assertTrue(isinstance(plan, migration.Plan))
