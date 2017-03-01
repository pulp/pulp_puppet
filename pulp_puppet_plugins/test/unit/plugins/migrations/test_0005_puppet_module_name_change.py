"""
Tests for pulp_rpm.plugins.migrations.0005_puppet_module_name_change
"""
import unittest

from mock import Mock, patch

from mongoengine import NotUniqueError

from pulp.server.db import model
from pulp.server.db.migrate.models import _import_all_the_way

from pulp_puppet.plugins.db.models import Module

PATH_TO_MODULE = 'pulp_puppet.plugins.migrations.0005_puppet_module_name_change'

migration = _import_all_the_way(PATH_TO_MODULE)


class Test0005PuppetModuleNameChange(unittest.TestCase):
    """
    Test the migration of the puppet module name update
    """
    @patch('__builtin__.open', autospec=True)
    @patch(PATH_TO_MODULE + '.model.Distributor.objects')
    @patch(PATH_TO_MODULE + '.Module.objects')
    def test_migration(self, mock_modules, mock_dist, mock_open):
        module_foo = Module(name='kung-foo', version='0.1.2', author='kung')
        mock_modules.filter.return_value = [module_foo]
        module_foo.save = Mock()

        migration.migrate()

        module_foo.save.assert_called_once_with()
        mock_dist.filter.assert_called_once_with(repo_id__in=[], last_publish__ne=None)

    @patch('__builtin__.open', autospec=True)
    @patch(PATH_TO_MODULE + '.model.Repository.objects')
    @patch(PATH_TO_MODULE + '.repo_controller')
    @patch(PATH_TO_MODULE + '.model.RepositoryContentUnit.objects')
    @patch(PATH_TO_MODULE + '.model.Distributor.objects')
    @patch(PATH_TO_MODULE + '.Module.objects')
    def test_migration_duplicate_unit(self, mock_modules, mock_dist, mock_association,
                                      mock_controller, mock_repo, mock_open):
        module_foo = Module(name='kung-foo', version='0.1.2', author='kung')
        module_bar = Module(name='foo', version='0.1.2', author='kung')
        module_bar.first = Mock()
        mock_modules.filter.side_effect = ([module_foo], module_bar)
        module_foo.save = Mock()
        module_foo.save.side_effect = NotUniqueError()
        repo_association = model.RepositoryContentUnit(repo_id='test_repo',
                                                       unit_type_id='puppet_module',
                                                       unit_id='bar')
        test_repo = model.Repository(repo_id='test_repo')
        mock_repo.get_repo_or_missing_resource.return_value = test_repo
        mock_association.filter.return_value = [repo_association]

        migration.migrate()

        module_foo.save.assert_called_once_with()
        mock_association.filter.assert_called_once_with(unit_id=module_foo.id)
        mock_modules.filter.assert_called_with(name='foo')
        mock_controller.disassociate_units.assert_called_once_with(repo_association, [module_foo])
        mock_repo.get_repo_or_missing_resource.assert_called_once_with('test_repo')
        mock_controller.rebuild_content_unit_counts.assert_called_once_with(test_repo)
