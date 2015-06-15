"""
Tests for pulp_puppet.plugins.migrations.0002_puppet_publishing_directory_change
"""
import os
import tempfile
import unittest

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way


class Test0002PuppetPublishingDirectoryChange(unittest.TestCase):
    """
    Test the migration of published puppet repo content to the new publish location
    """

    @patch('pulp_puppet.plugins.migrations.0002_puppet_publishing_directory_change.'
           'move_directory_contents')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_migration(self, mock_listdir, mock_path_exists, mock_move_directory):
        migration = _import_all_the_way('pulp_puppet.plugins.migrations.0002_puppet_'
                                        'publishing_directory_change')
        migration.migrate()
        mock_listdir.assert_called_once_with('/var/www/pulp_puppet')
        mock_path_exists.assert_has_call('/var/www/pulp_puppet')

    def test_move_directory_contents(self):
        test_old_publish_dir = tempfile.mkdtemp(prefix='test_0002_migration_old')
        old_http_publish_dir = os.path.join(test_old_publish_dir, 'http', 'repos')
        old_https_publish_dir = os.path.join(test_old_publish_dir, 'https', 'repos')
        os.makedirs(old_http_publish_dir)
        os.makedirs(old_https_publish_dir)

        test_new_publish_dir = tempfile.mkdtemp(prefix='test_0002_migration_new')
        test_new_publish_puppet_dir = os.path.join(test_new_publish_dir, 'puppet')
        # on a real system, this dir is created by the rpm
        os.mkdir(test_new_publish_puppet_dir)

        new_http_publish_dir = os.path.join(test_new_publish_puppet_dir, 'http', 'repos')
        new_https_publish_dir = os.path.join(test_new_publish_puppet_dir, 'https', 'repos')
        # put a file in the top-level dir to ensure it gets copied over too.
        # It is not typical to have a file there but we should move it over
        # just in case.
        open(os.path.join(test_old_publish_dir, 'some_file'), 'w').close()

        migration = _import_all_the_way('pulp_puppet.plugins.migrations.0002_puppet_'
                                        'publishing_directory_change')

        migration.move_directory_contents(test_old_publish_dir, test_new_publish_puppet_dir)

        self.assertTrue(os.path.exists(new_http_publish_dir))
        self.assertTrue(os.path.exists(new_https_publish_dir))
        self.assertTrue(os.path.exists(os.path.join(test_new_publish_puppet_dir, 'some_file')))
        # bz 1153072 - user needs to clear this dir manually
        self.assertTrue(os.path.exists(test_old_publish_dir))
        for (root, files, dirs) in os.walk(test_old_publish_dir):
            self.assertTrue(files == [])
            self.assertTrue(dirs == [])
