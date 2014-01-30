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

import functools
import json
import unittest
import urlparse

import mock

from pulp_puppet.forge.unit import Unit


unit_generator = functools.partial(
    Unit, name='me/mymodule', file='/path/to/file', db={}, repo_id='repo1',
    host='localhost', protocol='http', version='1.0.0',
    dependencies = [{'name':'you/yourmodule', 'version_requirement': '>= 2.1.0'}]
)


class TestUnitsFromJSON(unittest.TestCase):
    UNIT_JSON = json.dumps([{
        'version' : '1.2.0',
        'file' : 'path/to/file.tar.gz',
        'dependencies' : [{
            'name':'me/mymodule',
            'version_requirement': '>= 2.1.0'
        }]
    }])

    def test_valid(self):
        name = 'me/stuntmodule'
        db = {name:self.UNIT_JSON}
        result = Unit.units_from_json(name, db, 'repo1', 'localhost', 'http')

        self.assertEqual(len(result), 1)
        self.assertTrue(isinstance(result[0], Unit))
        self.assertEqual(result[0].name, name)
        self.assertEqual(result[0].repo_id, 'repo1')
        self.assertEqual(result[0].host, 'localhost')
        self.assertEqual(result[0].protocol, 'http')

    def test_not_in_db(self):
        name = 'me/stuntmodule'
        db = {}
        result = Unit.units_from_json(name, db, 'repo1', 'localhost', 'http')

        self.assertEqual(len(result), 0)


class TestBuildDepMetadata(unittest.TestCase):
    def test_no_deps(self):
        unit = unit_generator(dependencies=[])

        result = unit.build_dep_metadata()

        self.assertEqual(result, {unit.name: [unit.to_dict()]})

    @mock.patch.object(Unit, '_add_dep_to_metadata', spec=unit_generator()._add_dep_to_metadata)
    def test_with_dep(self, mock_add_dep):
        unit = unit_generator()

        result = unit.build_dep_metadata()

        self.assertEqual(result, {unit.name: [unit.to_dict()]})
        mock_add_dep.assert_called_once_with('you/yourmodule', {unit.name: [unit.to_dict()]})


class TestAddDepToMetadata(unittest.TestCase):
    @mock.patch.object(Unit, 'units_from_json', spec=unit_generator().units_from_json)
    def test_normal(self, mock_units_from_json):
        # demonstrates recursive dep adding
        mock_units_from_json.side_effect = [
            [unit_generator(name='foo/bar')],
            [unit_generator(name='you/yourmodule', dependencies=[])]
        ]
        unit = unit_generator()
        data = {}

        unit._add_dep_to_metadata('foo/bar', data)

        # verify that this method was called correctly
        self.assertEqual(mock_units_from_json.call_count, 2)
        mock_units_from_json.assert_any_call('foo/bar', unit.db, unit.repo_id, unit.host, unit.protocol)
        mock_units_from_json.assert_called_with('you/yourmodule', unit.db, unit.repo_id, unit.host, unit.protocol)

        self.assertEqual(set(data.keys()), set(['foo/bar', 'you/yourmodule']))
        self.assertEqual(data['foo/bar'], [unit_generator(name='foo/bar').to_dict()])
        self.assertEqual(data['you/yourmodule'],
                         [unit_generator(name='you/yourmodule', dependencies=[]).to_dict()])

    def test_name_already_in_root(self):
        # it should do nothing in this case
        unit = unit_generator()
        mock_list_of_module_metadata = mock.MagicMock()
        root = {'foo/bar': mock_list_of_module_metadata}

        unit._add_dep_to_metadata('foo/bar', root)

        self.assertEqual(root['foo/bar'], mock_list_of_module_metadata)


class TestDepsAsList(unittest.TestCase):
    def test_normal(self):
        unit = unit_generator()
        result = unit._deps_as_list

        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 2)
        self.assertEqual(result[0][0], unit.dependencies[0]['name'])
        self.assertEqual(result[0][1], unit.dependencies[0]['version_requirement'])

    def test_empty(self):
        unit = unit_generator(dependencies=[])
        result = unit._deps_as_list

        self.assertEqual(result, [])


class TestToDict(unittest.TestCase):
    def test_normal(self):
        unit = unit_generator()
        result = unit.to_dict()

        self.assertEqual(len(result), 3)
        self.assertEqual(result['version'], unit.version)
        self.assertEqual(result['file'], unit.file)
        self.assertEqual(result['dependencies'], unit._deps_as_list)

    def test_file_url(self):
        unit = unit_generator(host='localhost')
        result = unit.to_dict()

        self.assertEqual(result['file'], unit.file)


class TestCmp(unittest.TestCase):
    """
    The 'semantic_version' library is being used under the hood, which is a good
    thing. Thus these tests will do good spot-checking, but not an exhaustive
    exercise of every semver possibility.
    """
    @mock.patch('semantic_version.Version.__cmp__', autospec=True)
    def test_uses_semver(self, mock_version):
        """
        If we ever stop using python-semantic_version, we should revisit the
        suite of tests below.
        """
        unit_generator(version='1.2.0') > unit_generator(version='1.1.3')

        self.assertEqual(mock_version.call_count, 1)

    def test_plain_gt(self):
        self.assertTrue(unit_generator(version='1.2.0') > unit_generator(version='1.1.3'))

    def test_plain_lt(self):
        self.assertTrue(unit_generator(version='1.2.0') < unit_generator(version='2.1.3'))

    def test_double_digit_lt(self):
        self.assertTrue(unit_generator(version='1.2.0') < unit_generator(version='1.12.3'))

    def test_plain_eq(self):
        self.assertEqual(unit_generator(version='1.2.0'), unit_generator(version='1.2.0'))

    def test_alpha_gt(self):
        self.assertTrue(unit_generator(version='1.2.3') > unit_generator(version='1.1.0-alpha'))

    def test_alpha_lt(self):
        self.assertTrue(unit_generator(version='1.0.3') < unit_generator(version='1.1.0-alpha'))

    def test_alpha_eq(self):
        self.assertEqual(unit_generator(version='1.2.0-alpha'), unit_generator(version='1.2.0-alpha'))
