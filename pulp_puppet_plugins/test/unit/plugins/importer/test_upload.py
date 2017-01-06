import os
import shutil
import tempfile
import unittest

import mock
from pulp.plugins.model import Repository

from pulp_puppet.common import constants
from pulp_puppet.plugins.db.models import InvalidModuleName
from pulp_puppet.plugins.importers import upload

DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../../../data'
MODULE_STRING = 'pulp_puppet.plugins.importers.upload'


class UploadTests(unittest.TestCase):

    def setUp(self):
        self.unit_key = {
            'name': 'pulp',
            'version': '2.0.0',
            'author': 'jdob',
        }
        self.unit_metadata = {
            'source': 'http://pulpproject.org',
        }
        self.filename = 'jdob-valid-1.0.0.tar.gz'
        self.dest_dir = tempfile.mkdtemp(prefix='puppet-upload-test')
        self.dest_file = os.path.join(self.dest_dir, self.filename)
        self.source_file = os.path.join(DATA_DIR, 'good-modules',
                                        'jdob-valid', 'pkg', self.filename)

        self.conduit = mock.MagicMock()

        self.working_dir = tempfile.mkdtemp(prefix='puppet-sync-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)

    def tearDown(self):
        shutil.rmtree(self.working_dir)
        if os.path.exists(self.dest_dir):
            shutil.rmtree(self.dest_dir)

    @mock.patch(MODULE_STRING + '.Module')
    @mock.patch(MODULE_STRING + '.repo_controller')
    def test_handle_uploaded_unit(self, mock_repo_controller, mock_module):
        # Setup
        initialized_unit = mock.MagicMock()
        initialized_unit.storage_path = self.dest_dir
        self.conduit.init_unit.return_value = initialized_unit
        mock_uploaded_module = mock_module.from_metadata.return_value
        mock_uploaded_module.puppet_standard_filename.return_value = self.filename

        # Test
        report = upload.handle_uploaded_unit(self.repo, constants.TYPE_PUPPET_MODULE, self.unit_key,
                                             self.unit_metadata, self.source_file, self.conduit)

        # Verify
        mock_module.from_metadata.return_value.save_and_import_content.assert_called_once()

        self.assertTrue(isinstance(report, dict))
        self.assertTrue('success_flag' in report)
        self.assertTrue(report['success_flag'])
        self.assertTrue('summary' in report)
        self.assertTrue('details' in report)

    @mock.patch(MODULE_STRING + '.Module')
    @mock.patch(MODULE_STRING + '.repo_controller')
    def test_handle_uploaded_unit_with_no_data(self, mock_repo_controller, mock_module):
        # Setup
        initialized_unit = mock.MagicMock()
        initialized_unit.storage_path = self.dest_dir
        self.conduit.init_unit.return_value = initialized_unit
        mock_uploaded_module = mock_module.from_metadata.return_value
        mock_uploaded_module.puppet_standard_filename.return_value = self.filename

        # Test
        report = upload.handle_uploaded_unit(self.repo, constants.TYPE_PUPPET_MODULE, {},
                                             {}, self.source_file, self.conduit)

        mock_module.from_metadata.return_value.save_and_import_content.assert_called_once()

        self.assertTrue(report['success_flag'])

    def test_handle_uploaded_unit_bad_type(self):
        self.assertRaises(NotImplementedError, upload.handle_uploaded_unit, self.repo, 'foo',
                          None, None, None, None)

    @mock.patch('pulp_puppet.plugins.importers.metadata.extract_metadata')
    def test_handle_uploaded_unit_bad_name(self, mock_metadata):
        mock_metadata.return_value = {'name': 'bad_name'}
        self.assertRaises(InvalidModuleName, upload.handle_uploaded_unit,
                          self.repo, constants.TYPE_PUPPET_MODULE,
                          self.unit_key, self.unit_metadata, self.source_file,
                          self.conduit)
