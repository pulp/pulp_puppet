"""
Tests for pulp_puppet.plugins.migrations.0003_puppet_drop_module_indexes
"""
import unittest

from mock import patch, call

from pulp.server.db.migrate.models import _import_all_the_way


migration = _import_all_the_way('pulp_puppet.plugins.migrations.0003_puppet_drop_module_indexes')


class Test0003PuppetIndexesDropped(unittest.TestCase):
    """
    Test the migration of dropping the puppet module indexes
    """

    @patch.object(migration, 'get_collection')
    def test_migration(self, mock_get_collection):
        migration.migrate()
        mock_get_collection.assert_called_once_with('units_puppet_module')
        calls = [call('name_1_version_1_author_1'), call('author_1'), call('tag_list_1')]
        mock_get_collection.return_value.drop_index.assert_has_calls(calls)
