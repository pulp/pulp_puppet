# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import gdbm
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import mock
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, PublishReport, Unit

from pulp_puppet.common import constants
from pulp_puppet.plugins.distributors import publish

# -- constants ----------------------------------------------------------------

DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../data'
FAKE_PULP_STORAGE_DIR = os.path.join(DATA_DIR, 'repos', 'valid')

# -- test cases ---------------------------------------------------------------

class MockConduit(mock.MagicMock):

    def build_success_report(self, summary, details):
        return PublishReport(True, summary, details)

    def build_failure_report(self, summary, details):
        return PublishReport(False, summary, details)


class PublishRunTests(unittest.TestCase):

    def setUp(self):
        # Set up fake published location to write repositories to
        self.test_httpd_base = tempfile.mkdtemp(prefix='pulp-puppet-dist-publish')
        self.test_http_dir = os.path.join(self.test_httpd_base, 'http')
        self.test_https_dir = os.path.join(self.test_httpd_base, 'https')

        os.mkdir(self.test_http_dir)
        os.mkdir(self.test_https_dir)

        # Fake repository working directory
        self.working_dir = tempfile.mkdtemp(prefix='pulp-puppet-repo-dir')

        # Have the conduit return units to copy (real units from the data dir)
        self.units = []
        for module in [m for m in os.listdir(FAKE_PULP_STORAGE_DIR) if m.endswith('.tar.gz')]:
            author, name, version = module.split('-')
            version = version[0:5]
            key = {'name' : name, 'version' : version, 'author' : author}
            storage_dir = os.path.join(FAKE_PULP_STORAGE_DIR, module)

            metadata = {'checksums' : [['a', 'a'], ['b', 'b']]}
            u = Unit(constants.TYPE_PUPPET_MODULE, key, metadata, storage_dir)
            self.units.append(u)
        self.conduit = MockConduit()
        self.conduit.get_units.return_value = self.units

        # Configuration for the run
        self.repo = Repository('test-repo', working_dir=self.working_dir)
        self.config = PluginCallConfiguration(
            {
                constants.CONFIG_HTTP_DIR : self.test_http_dir,
                constants.CONFIG_HTTPS_DIR : self.test_https_dir,
            },
            {
                constants.CONFIG_SERVE_HTTP : True,
                constants.CONFIG_SERVE_HTTPS : True,
            }
        )
        self.is_cancelled_call = mock.MagicMock().is_cancelled_call

        self.run = publish.PuppetModulePublishRun(self.repo, self.conduit,
                                                  self. config, self.is_cancelled_call)

    def tearDown(self):
        if os.path.exists(self.test_httpd_base):
            shutil.rmtree(self.test_httpd_base)

        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)

    @mock.patch('gdbm.open')
    def test_generate_dep_data(self, mock_open):
        class FakeDB(dict):
            """Fake version of gdbm database"""
            close_called = False
            def close(self):
                self.close_called = True
        mock_open.return_value = FakeDB()
        file_to_test = os.path.join(DATA_DIR, 'simple', 'xinetd-1.2.0.tar.gz')
        with open(file_to_test, 'r') as file_handle:
            content = file_handle.read()
            md5_sum = hashlib.md5(content).hexdigest()

        units = [
            Unit(constants.TYPE_PUPPET_MODULE,
                 {'name': 'foo', 'version': '1.0.3', 'author': 'me'},
                 {'dependencies': []}, file_to_test),
            Unit(constants.TYPE_PUPPET_MODULE,
                 {'name': 'foo', 'version': '1.1.0', 'author': 'me'},
                 {'dependencies': []}, file_to_test),
            Unit(constants.TYPE_PUPPET_MODULE,
                 {'name': 'bar', 'version': '1.0.0', 'author': 'me'},
                 {'dependencies': [{'name': 'me/foo', 'version_requirement': '>= 1.0.0'}]},
                 file_to_test),
        ]
        self.run._generate_dependency_data(units)

        db = mock_open.return_value
        self.assertTrue(db.close_called)
        self.assertTrue('me/foo' in db)
        self.assertTrue('me/bar' in db)
        foo_data = json.loads(db['me/foo'])
        self.assertEqual(len(foo_data), 2)
        bar_data = json.loads(db['me/bar'])
        self.assertEqual(len(bar_data), 1)
        self.assertEqual(bar_data[0]['dependencies'][0]['name'], 'me/foo')
        self.assertEqual(bar_data[0]['dependencies'][0]['version_requirement'], '>= 1.0.0')
        self.assertEqual(bar_data[0]['file_md5'], md5_sum)

    def test_perform_publish(self):
        # Test
        report = self.run.perform_publish()

        # Verify

        # Units copied to the proper published dirs
        for unit in self.units:
            filename = os.path.basename(unit.storage_path)
            author = unit.unit_key['author']
            relative_path = constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (author[0], author)

            http_published_filename = os.path.join(self.test_http_dir, self.repo.id, relative_path, filename)
            self.assertTrue(os.path.exists(http_published_filename), msg='%s does not exist' % http_published_filename)
            self.assertTrue(os.path.islink(http_published_filename), msg='%s is not a symlink' % http_published_filename)

            https_published_filename = os.path.join(self.test_https_dir, self.repo.id, relative_path, filename)
            self.assertTrue(os.path.exists(https_published_filename), msg='%s does not exist' % https_published_filename)
            self.assertTrue(os.path.islink(https_published_filename), msg='%s is not a symlink' % https_published_filename)

        # Build directory was cleaned up
        self.assertTrue(not os.path.exists(self.run._build_dir()))

        # Dependency metadata was generated
        expected_dep_file = os.path.join(self.test_http_dir, self.repo.id, constants.REPO_DEPDATA_FILENAME)
        self.assertTrue(os.path.exists(expected_dep_file))
        db = gdbm.open(expected_dep_file)
        for unit in self.units:
            name = '%s/%s' % (unit.unit_key['author'], unit.unit_key['name'])
            self.assertTrue(db.has_key(name))
            data = json.loads(db[name])
            self.assertTrue(isinstance(data, list))
            if len(data) == 1:
                self.assertEqual(data[0]['version'], unit.unit_key['version'])
                self.assertTrue(isinstance(data[0].get('dependencies'), list))
                self.assertTrue('file' in data[0])
        db.close()

        self.assertTrue(os.path.exists(self.test_http_dir))

        # Final report
        self.assertTrue(report.success_flag)
        self.assertTrue(report.summary['total_execution_time'] is not None)
        self.assertTrue(report.summary['total_execution_time'] > -1)
        self.assertEqual(len(report.details), 0)

        # Progress report was updated
        pr = self.run.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_finished_count, 2)
        self.assertEqual(pr.modules_error_count, 0)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertEqual(pr.modules_error_message, None)
        self.assertEqual(pr.modules_exception, None)
        self.assertEqual(pr.modules_traceback, None)
        self.assertEqual(pr.modules_individual_errors, None)

        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertEqual(pr.metadata_error_message, None)
        self.assertEqual(pr.metadata_exception, None)
        self.assertEqual(pr.metadata_traceback, None)

        self.assertEqual(pr.publish_http, constants.STATE_SUCCESS)
        self.assertEqual(pr.publish_https, constants.STATE_SUCCESS)

    def test_unpublish_http(self):
        """
        After a successful publish, run another without HTTP to make sure the
        previously published repository is removed.
        """

        # Setup
        self.run.perform_publish()

        # Test
        self.config.override_config = {constants.CONFIG_SERVE_HTTP : False,}
        self.run.perform_publish()

        # Verify
        published_repo_dir = os.path.join(self.test_http_dir, self.repo.id)
        self.assertTrue(not os.path.exists(published_repo_dir))

    def test_publish_skip_http_https(self):
        # Setup
        self.config.override_config = {
            constants.CONFIG_SERVE_HTTP : False,
            constants.CONFIG_SERVE_HTTPS : False,
        }

        # Test
        self.run.perform_publish()

        # Verify
        pr = self.run.progress_report
        self.assertEqual(pr.publish_http, constants.STATE_SKIPPED)
        self.assertEqual(pr.publish_https, constants.STATE_SKIPPED)

    def test_error_in_modules_step(self):
        # Setup
        self.repo.working_dir = '/foo' # init build dir will fail

        # Test
        report = self.run.perform_publish()

        # Verify
        self.assertTrue(not report.success_flag)
        self.assertEqual(report.summary['total_execution_time'], -1)
        self.assertEqual(len(report.details), 0)

        pr = self.run.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_FAILED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)
        self.assertEqual(pr.modules_error_count, None)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertTrue(pr.modules_error_message is not None)
        self.assertTrue(pr.modules_exception is not None)
        self.assertTrue(pr.modules_traceback is not None)
        self.assertEqual(pr.modules_individual_errors, None)

        self.assertEqual(pr.metadata_state, constants.STATE_NOT_STARTED)

    def test_error_in_metadata_step(self):
        # Setup
        self.config.override_config = {constants.CONFIG_HTTP_DIR : '/foo'}

        # Test
        report = self.run.perform_publish()

        # Verify
        self.assertTrue(not report.success_flag)
        self.assertTrue(report.summary['total_execution_time'] > -1)
        self.assertEqual(len(report.details), 0)

        pr = self.run.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)

        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertTrue(pr.metadata_error_message is not None)
        self.assertTrue(pr.metadata_exception is not None)
        self.assertTrue(pr.metadata_traceback is not None)
        self.assertTrue(pr.metadata_execution_time is not None)

    def test_existing_build_dir(self):
        # Setup
        build_dir = self.run._build_dir()
        os.makedirs(build_dir)

        sample_file = os.path.join(build_dir, 'sample')
        f = open(sample_file, 'w')
        f.write('foo')
        f.close()

        # Test
        self.run._init_build_dir()

        # Verify
        self.assertTrue(os.path.exists(build_dir))
        self.assertTrue(not os.path.exists(sample_file))

    @mock.patch('os.symlink')
    def test_failed_symlink(self, mock_symlink):
        # Setup
        mock_symlink.side_effect = Exception() # simulate write permission error

        # Test
        report = self.run.perform_publish()

        # Verify
        self.assertTrue(report.success_flag) # still an overall success

        pr = self.run.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS) # still a success
        self.assertEqual(pr.modules_error_count, 2)
        self.assertEqual(pr.modules_finished_count, 0)
        self.assertEqual(len(pr.modules_individual_errors), 2)

        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)

    def test_unpublish_repo(self):
        # Setup
        os.makedirs(os.path.join(self.test_http_dir, self.repo.id))
        os.makedirs(os.path.join(self.test_https_dir, self.repo.id))

        # Test
        publish.unpublish_repo(self.repo, self.config)

        # Verify
        self.assertTrue(not os.path.exists(os.path.join(self.test_http_dir, self.repo.id)))
        self.assertTrue(not os.path.exists(os.path.join(self.test_https_dir, self.repo.id)))
