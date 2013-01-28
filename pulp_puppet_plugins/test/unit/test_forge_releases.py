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
import unittest

import mock
from pulp.server.managers.consumer.bind import BindManager
import web

from pulp_puppet.common import constants
from pulp_puppet.forge import releases
from pulp_puppet.forge.unit import Unit


unit_generator = functools.partial(
    Unit, name='me/mymodule', file='/path/to/file', db={}, repo_id='repo1',
    host='localhost', protocol='http', version='1.0.0',
    dependencies = [{'name':'you/yourmodule', 'version_requirement': '>= 2.1.0'}]
)

MOCK_HOST_PROTOCOL = {
    'host': 'localhost',
    'protocol' : 'http'
}


class TestView(unittest.TestCase):
    def test_null_auth(self):
        self.assertRaises(web.Unauthorized, releases.view, releases.NULL_AUTH_VALUE, releases.NULL_AUTH_VALUE, 'foo/bar')

    @mock.patch.object(releases, 'find_newest', autospec=True)
    def test_repo_only(self, mock_find):
        result = releases.view(releases.NULL_AUTH_VALUE, 'repo1', 'foo/bar')
        mock_find.assert_called_once_with(['repo1'], 'foo/bar')
        self.assertEqual(result, mock_find.return_value.build_dep_metadata.return_value)

    @mock.patch.object(releases, 'find_newest', autospec=True)
    def test_repo_and_consumer(self, mock_find):
        # should ignore the consumer
        releases.view('consumer1', 'repo1', 'foo/bar')
        mock_find.assert_called_once_with(['repo1'], 'foo/bar')

    @mock.patch.object(releases, 'find_newest', autospec=True)
    @mock.patch.object(releases, 'get_bound_repos', autospec=True)
    def test_consumer_only(self, mock_get_bound, mock_find):
        mock_get_bound.return_value = ['repo1', 'repo2']

        releases.view('consumer1', releases.NULL_AUTH_VALUE, 'foo/bar')

        mock_get_bound.assert_called_once_with('consumer1')
        mock_find.assert_called_once_with(['repo1', 'repo2'], 'foo/bar')

    @mock.patch.object(releases, 'find_version', autospec=True)
    def test_with_version(self, mock_find):
        result = releases.view(releases.NULL_AUTH_VALUE, 'repo1', 'foo/bar', '1.0.0')
        mock_find.assert_called_once_with(['repo1'], 'foo/bar', '1.0.0')
        self.assertEqual(result, mock_find.return_value.build_dep_metadata.return_value)

    @mock.patch.object(releases, 'find_newest', autospec=True, return_value=None)
    @mock.patch('web.NotFound', return_value=Exception())
    def test_unit_not_found(self, mock_not_found, mock_find):
        self.assertRaises(Exception, releases.view, releases.NULL_AUTH_VALUE, 'repo1', 'foo/bar')
        mock_not_found.assert_called_once_with()

    @mock.patch.object(releases, 'find_newest', autospec=True)
    def test_close_unit_db(self, mock_find):
        result = releases.view(releases.NULL_AUTH_VALUE, 'repo1', 'foo/bar')
        mock_find.return_value.db.close.assert_called_once_with()

    @mock.patch.object(releases, 'find_newest', autospec=True)
    def test_close_unit_db_with_error(self, mock_find):
        mock_find.return_value.build_dep_metadata.side_effect=Exception
        self.assertRaises(Exception, releases.view, releases.NULL_AUTH_VALUE, 'repo1', 'foo/bar')
        mock_find.return_value.db.close.assert_called_once_with()


class TestGetRepoDepDBs(unittest.TestCase):
    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_single_repo(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [{'repo_id':'repo1', 'config':{}}]

        result = releases.get_repo_dep_dbs(['repo1'])

        self.assertIsInstance(result, dict)
        self.assertEqual(result.keys(), ['repo1'])
        self.assertEqual(result['repo1'], mock_open.return_value)
        mock_open.assert_called_once_with('/var/www/pulp_puppet/http/repos/repo1/.dependency_db', 'r')

    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_multiple_repos(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [
            {'repo_id':'repo1', 'config':{}},
            {'repo_id':'repo2', 'config':{}}
        ]

        result = releases.get_repo_dep_dbs(['repo1', 'repo2'])

        self.assertTrue('repo1' in result)
        self.assertTrue('repo2' in result)

    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_configured_publish_dir(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [
            {'repo_id':'repo1',
             'config':{constants.CONFIG_HTTP_DIR: '/var/www/pulp_puppet/foo'}}
        ]

        result = releases.get_repo_dep_dbs(['repo1'])

        mock_open.assert_called_once_with('/var/www/pulp_puppet/foo/repo1/.dependency_db', 'r')


class TestFindVersion(unittest.TestCase):
    @mock.patch.object(releases, 'get_host_and_protocol', return_value=MOCK_HOST_PROTOCOL)
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_calls_units_from_json(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = []

        result = releases.find_version(['repo1', 'repo2'], 'foo/bar', '1.0.0')

        mock_units_from_json.assert_any_call(
            'foo/bar', mock_get_dbs.return_value['repo1'], 'repo1', **MOCK_HOST_PROTOCOL
        )
        mock_units_from_json.assert_any_call(
            'foo/bar', mock_get_dbs.return_value['repo2'], 'repo2', **MOCK_HOST_PROTOCOL
        )

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_returns_version(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = [
            unit_generator(version='2.1.3'),
            unit_generator(version='1.6.2'),
            unit_generator(version='2.0.3'),
            unit_generator(version='3.1.5'),
            ]

        result = releases.find_version(['repo1', 'repo2'], 'foo/bar', '2.0.3')

        self.assertIsInstance(result, Unit)
        self.assertEqual(result.version, '2.0.3')

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_no_units_found(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        # make sure it correctly returns None if there are no units found
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = []

        result = releases.find_version(['repo1', 'repo2'], 'foo/bar', '1.0.0')

        self.assertIsNone(result)

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json', side_effect=Exception)
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_close_dbs_on_error(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }

        self.assertRaises(Exception, releases.find_version, ['repo1', 'repo2'], 'foo/bar', '1.0.0')

        for mock_db in mock_get_dbs.return_value.itervalues():
            mock_db.close.assert_called_once_with()


class TestFindNewest(unittest.TestCase):
    @mock.patch.object(releases, 'get_host_and_protocol', return_value=MOCK_HOST_PROTOCOL)
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_calls_units_from_json(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = []

        result = releases.find_newest(['repo1', 'repo2'], 'foo/bar')

        mock_units_from_json.assert_any_call(
            'foo/bar', mock_get_dbs.return_value['repo1'], 'repo1', **MOCK_HOST_PROTOCOL
        )
        mock_units_from_json.assert_any_call(
            'foo/bar', mock_get_dbs.return_value['repo2'], 'repo2', **MOCK_HOST_PROTOCOL
        )

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_returns_newest(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = [
            unit_generator(version='2.1.3'),
            unit_generator(version='1.6.2'),
            unit_generator(version='3.1.5'),
            unit_generator(version='2.0.3'),
        ]

        result = releases.find_newest(['repo1', 'repo2'], 'foo/bar')

        self.assertIsInstance(result, Unit)
        self.assertEqual(result.version, '3.1.5')

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json')
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_no_units_found(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        # make sure it correctly returns None if there are no units found
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }
        mock_units_from_json.return_value = []

        result = releases.find_newest(['repo1', 'repo2'], 'foo/bar')

        self.assertIsNone(result)

    @mock.patch.object(releases, 'get_host_and_protocol')
    @mock.patch('pulp_puppet.forge.unit.Unit.units_from_json', side_effect=Exception)
    @mock.patch.object(releases, 'get_repo_dep_dbs', autospec=True)
    def test_close_dbs_on_error(self, mock_get_dbs, mock_units_from_json, mock_get_host_and_protocol):
        mock_get_dbs.return_value = {
            'repo1' : mock.MagicMock(),
            'repo2' : mock.MagicMock()
        }

        self.assertRaises(Exception, releases.find_newest, ['repo1', 'repo2'], 'foo/bar')

        for mock_db in mock_get_dbs.return_value.itervalues():
            mock_db.close.assert_called_once_with()



class TestGetHostAndProtocol(unittest.TestCase):
    @mock.patch('web.ctx', autospec=True)
    def test_normal(self, mock_ctx):
        mock_ctx.host = 'localhost'
        mock_ctx.protocol = 'http'

        result = releases.get_host_and_protocol()

        self.assertEqual(set(result.keys()), set(['host', 'protocol']))
        self.assertEqual(result['host'], 'localhost')
        self.assertEqual(result['protocol'], 'http')


class TestGetBoundRepos(unittest.TestCase):
    @mock.patch.object(BindManager, 'find_by_consumer', spec=BindManager().find_by_consumer)
    def test_only_puppet(self, mock_find):
        bindings =[{
            'repo_id': 'repo1',
            'distributor_id' : constants.DISTRIBUTOR_TYPE_ID
        }]
        mock_find.return_value = bindings

        result = releases.get_bound_repos('consumer1')

        mock_find.assert_called_once_with('consumer1')
        self.assertEqual(result, ['repo1'])

    @mock.patch.object(BindManager, 'find_by_consumer', spec=BindManager().find_by_consumer)
    def test_only_other_type(self, mock_find):
        bindings =[{
                       'repo_id': 'repo1',
                       'distributor_id': 'some_other_type'
                   }]
        mock_find.return_value = bindings

        result = releases.get_bound_repos('consumer1')

        mock_find.assert_called_once_with('consumer1')
        self.assertEqual(result, [])

    @mock.patch.object(BindManager, 'find_by_consumer', spec=BindManager().find_by_consumer)
    def test_mixed_types(self, mock_find):
        bindings =[
            {
               'repo_id': 'repo1',
               'distributor_id' : constants.DISTRIBUTOR_TYPE_ID
            },
            {
                'repo_id': 'repo2',
                'distributor_id' :'some_other_type'
            },
            {
                'repo_id': 'repo3',
                'distributor_id' : constants.DISTRIBUTOR_TYPE_ID
            },
        ]
        mock_find.return_value = bindings

        result = releases.get_bound_repos('consumer1')

        mock_find.assert_called_once_with('consumer1')
        self.assertEqual(result, ['repo1', 'repo3'])
