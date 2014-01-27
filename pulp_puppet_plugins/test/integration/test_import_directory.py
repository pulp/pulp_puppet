# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

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
            {constants.CONFIG_FEED: 'file://%s/../data/simple/PULP_MANIFEST' % test_dir,
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