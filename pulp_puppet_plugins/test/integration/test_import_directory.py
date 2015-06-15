import os
import shutil

from mock import Mock, patch
from tempfile import mkdtemp
from unittest import TestCase

from pulp.plugins.config import PluginCallConfiguration

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.directory import SynchronizeWithDirectory


class TestSynchronizeWithDirectory(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        TestCase.tearDown(self)
        shutil.rmtree(self.tmp_dir)

    @patch('pulp_puppet.plugins.importers.directory.Inventory._associated')
    def test_import(self, mock_associated):
        test_dir = os.path.dirname(__file__)

        mock_associated.return_value = set()

        unit = Mock()
        unit.storage_path = self.tmp_dir

        config = PluginCallConfiguration(
            {},
            {constants.CONFIG_FEED: 'file://%s/../data/simple/' % test_dir,
             constants.CONFIG_REMOVE_MISSING: True})

        conduit = Mock()
        conduit.init_unit = Mock(return_value=unit)

        repository = Mock()
        repository.working_dir = self.tmp_dir

        # test

        method = SynchronizeWithDirectory(conduit, config)
        method(repository)

        # validation

        conduit.save_unit.assert_called_once_with(unit)
