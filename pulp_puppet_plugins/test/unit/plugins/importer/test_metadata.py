import os
import shutil
import tempfile
import unittest

import mock
from pulp.server.exceptions import InvalidValue

from pulp_puppet.plugins.importers import metadata


DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../../../data'
MODULE_STRING = 'pulp_puppet.plugins.importers.metadata'


class NegativeMetadataTests(unittest.TestCase):

    def setUp(self):
        self.author = 'jdob'
        self.name = None  # set in test itself
        self.version = '1.0.0'

        self.module = mock.Mock()

        self.module_dir = os.path.join(DATA_DIR, 'bad-modules')
        self.tmp_dir = tempfile.mkdtemp(prefix='puppet-metadata-tests')

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_extract_metadata_bad_tarball(self):
        # Setup
        self.module.name = 'empty'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata.extract_metadata(filename, self.tmp_dir)
            self.fail()
        except metadata.ExtractionException, e:
            self.assertEqual(e.module_filename, filename)
            self.assertEqual(e.property_names[0], filename)
            self.assertTrue(isinstance(e, InvalidValue))

    def test_extract_non_standard_bad_tarball(self):
        # Setup
        self.module.name = 'empty'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata._extract_json(filename, self.tmp_dir)
            self.fail()
        except metadata.ExtractionException, e:
            self.assertEqual(e.module_filename, filename)

    @mock.patch(MODULE_STRING + '.tarfile')
    def test_extract_metadata_no_metadata(self, mock_tarfile):
        # Setup
        self.module.name = 'no-metadata'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata.extract_metadata(filename, self.tmp_dir)
            self.fail()
        except metadata.MissingModuleFile, e:
            self.assertEqual(e.module_filename, filename)