# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock
from pulp.plugins.model import Consumer, AssociatedUnit
from pulp.plugins.conduits.profiler import ProfilerConduit

from pulp_puppet.common import constants
from pulp_puppet.plugins.profilers import wholerepo

class TestAccessories(unittest.TestCase):
    def test_entry_point(self):
        class_definition, config = wholerepo.entry_point()

        self.assertTrue(class_definition is wholerepo.WholeRepoProfiler)
        self.assertTrue(isinstance(config, dict))

    def test_metadata(self):
        result = wholerepo.WholeRepoProfiler.metadata()

        self.assertEqual(result['id'], constants.WHOLE_REPO_PROFILER_ID)
        self.assertTrue(isinstance(result['display_name'], basestring))
        self.assertEqual(result['types'], [constants.TYPE_PUPPET_MODULE])


class TestInstallUnits(unittest.TestCase):

    def setUp(self):
        self.profiler = wholerepo.WholeRepoProfiler()
        self.consumer = Consumer('consumer1', {})
        self.units = [
            {'type_id': constants.TYPE_PUPPET_MODULE,
             'unit_key': {'name': 'gcc', 'author': 'puppetlabs'}},
            {'type_id': constants.TYPE_PUPPET_MODULE,
             'unit_key': {'name': 'stdlib', 'author': 'puppetlabs', 'version': '3.1.1'}},
            {'type_id': constants.TYPE_PUPPET_MODULE,
             'unit_key': {'name': 'stdlib', 'author': 'puppetlabs', 'version': '3.2.0'}}
        ]
        self.conduit = mock.MagicMock(spec=ProfilerConduit())
        self.conduit.get_units.return_value = [
            AssociatedUnit(constants.TYPE_PUPPET_MODULE, unit['unit_key'], {}, '', '', '')
            for unit in self.units
        ]

    def test_option_not_present(self):
        options = {}
        result = self.profiler.install_units(self.consumer, self.units, options, {}, self.conduit)

        # make sure the units are unchanged
        self.assertEqual(result, self.units)
        # make sure the repo wasn't queried
        self.assertEqual(self.conduit.get_units.call_count, 0)
        self.assertTrue(constants.FORGE_HOST in options)

    def test_with_option(self):
        special_unit = {'type_id': constants.TYPE_PUPPET_MODULE, 'unit_key': None}
        options = {constants.REPO_ID_OPTION: 'repo1', constants.WHOLE_REPO_OPTION: True}

        result = self.profiler.install_units(
            self.consumer, [special_unit], options, {}, self.conduit)

        self.conduit.get_units.assert_called_once_with('repo1')
        # make sure it combined the two stdlib entries
        self.assertEqual(len(result), 2)
        for unit in result:
            self.assertTrue('version' not in unit['unit_key'])
            self.assertEqual(unit['unit_key']['author'], 'puppetlabs')
            self.assertTrue('name' in unit['unit_key'])
            self.assertEqual(unit['type_id'], constants.TYPE_PUPPET_MODULE)
        self.assertTrue(constants.FORGE_HOST in options)

    def test_with_repo_but_not_option(self):
        options = {constants.REPO_ID_OPTION: 'repo1'}
        result = self.profiler.install_units(self.consumer, self.units, options, {}, self.conduit)

        # make sure the units are unchanged
        self.assertEqual(result, self.units)
        # make sure the repo wasn't queried
        self.assertEqual(self.conduit.get_units.call_count, 0)
        self.assertTrue(constants.FORGE_HOST in options)


class TestUpdateUnits(unittest.TestCase):

    def test_update(self):
        options = {}
        units = [1, 2, 3]
        profiler = wholerepo.WholeRepoProfiler()
        _units = profiler.update_units(None, units, options, None, None)
        self.assertEqual(units, _units)
        self.assertTrue(constants.FORGE_HOST in options)