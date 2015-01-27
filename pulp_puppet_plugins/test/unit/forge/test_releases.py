# -*- coding: utf-8 -*-

import functools
import gdbm
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
    dependencies=[{'name': 'you/yourmodule', 'version_requirement': '>= 2.1.0'}]
)

UNIT_DICT_FROM_DB = {
    'file': '/path/to/file',
    'version': '1.0.0',
    'dependencies': [{'name': 'you/yourmodule', 'version_requirement': '>= 2.1.0'}]
}

MOCK_HOST_PROTOCOL = {
    'host': 'localhost',
    'protocol': 'http'
}


class FooException(Exception):
    """
    Exception class used for testing only
    """
    pass


@mock.patch.object(releases, 'get_host_and_protocol', return_value={'host': 'bar'})
class TestUnitGenerator(unittest.TestCase):

    def test_empty_dbs(self, mock_get_host):
        self.assertEquals([], list(releases.unit_generator({}, 'foo')))

    @mock.patch('pulp_puppet.forge.releases.json.loads', autospec=True)
    def test_module_in_second_db(self, mock_load, mock_get_host):
        dbs = {
            'repo1': {'db': {}, 'protocol': 'http'},
            'repo2': {'db': {'foo': False}, 'protocol': 'http'},
        }

        mock_load.return_value = [UNIT_DICT_FROM_DB]

        results = list(releases.unit_generator(dbs, 'foo'))
        self.assertEquals(1, len(results))

    @mock.patch('pulp_puppet.forge.releases.json.loads', autospec=True)
    def test_module_not_found(self, mock_load, mock_get_host):
        dbs = {
            'repo1': {'db': {}, 'protocol': 'http'},
            'repo2': {'db': {}, 'protocol': 'http'},
        }

        mock_load.return_value = [UNIT_DICT_FROM_DB]

        results = list(releases.unit_generator(dbs, 'foo'))
        self.assertEquals(0, len(results))

    @mock.patch('pulp_puppet.forge.releases.json.loads', autospec=True)
    def test_two_modules_in_one_db(self, mock_load, mock_get_host):
        dbs = {
            'repo1': {'db': {'foo': True}, 'protocol': 'http'},
        }

        mock_load.return_value = [UNIT_DICT_FROM_DB, UNIT_DICT_FROM_DB]

        results = list(releases.unit_generator(dbs, 'foo'))
        self.assertEquals(2, len(results))

    @mock.patch('pulp_puppet.forge.releases.json.loads', autospec=True)
    def test_four_modules_in_two_db(self, mock_load, mock_get_host):
        dbs = {
            'repo1': {'db': {'foo': True}, 'protocol': 'http'},
            'repo2': {'db': {'foo': True}, 'protocol': 'http'},
        }

        mock_load.return_value = [UNIT_DICT_FROM_DB, UNIT_DICT_FROM_DB]

        results = list(releases.unit_generator(dbs, 'foo'))
        self.assertEquals(4, len(results))


@mock.patch.object(releases, 'get_host_and_protocol', return_value=MOCK_HOST_PROTOCOL)
class TestView(unittest.TestCase):

    # Mock the ctx so that the web.Unauthorized exception can be created properly
    @mock.patch('web.webapi.ctx')
    def test_null_auth(self, mock_ctx, mock_host):
        self.assertRaises(
            web.Unauthorized, releases.view, constants.FORGE_NULL_AUTH_VALUE,
            constants.FORGE_NULL_AUTH_VALUE, 'foo/bar')

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    @mock.patch.object(releases, 'get_bound_repos', autospec=True)
    def test_repo_ids_from_consumer(self, mock_get_bounds, mock_get_data,
                                    mock_unit_generator, mock_host):
        mock_get_bounds.return_value = ['apple', 'pear']
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'}
        }
        mock_unit_generator.return_value = [unit_generator()]

        releases.view('consumer1', constants.FORGE_NULL_AUTH_VALUE, 'me/mymodule')

        mock_get_bounds.assert_called_once_with('consumer1')
        mock_get_data.assert_called_once_with(['apple', 'pear'])

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_repo_ids_from_query_string(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        mock_unit_generator.return_value = [unit_generator()]

        releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule')

        mock_get_data.assert_called_once_with(['repo_foo'])

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_db_closing(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
            'repo2': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        mock_unit_generator.return_value = [unit_generator()]

        releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule')
        mock_get_data.return_value['repo1']['db'].close.assert_called_once_with()
        mock_get_data.return_value['repo2']['db'].close.assert_called_once_with()

    @mock.patch('web.NotFound', return_value=FooException())
    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_db_closing_with_exception(self, mock_get_data, mock_unit_generator, mock_not_found,
                                       mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
            'repo2': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        mock_unit_generator.return_value = []

        self.assertRaises(FooException, releases.view, constants.FORGE_NULL_AUTH_VALUE,
                          'repo_foo', 'me/mymodule')
        mock_get_data.return_value['repo1']['db'].close.assert_called_once_with()
        mock_get_data.return_value['repo2']['db'].close.assert_called_once_with()

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_db_closing_first_close_raises(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
            'repo2': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        mock_unit_generator.return_value = [unit_generator()]
        mock_get_data.return_value['repo1']['db'].close.side_effect = ValueError()

        self.assertRaises(ValueError, releases.view, constants.FORGE_NULL_AUTH_VALUE,
                          'repo_foo', 'me/mymodule')
        mock_get_data.return_value['repo1']['db'].close.assert_called_once_with()
        # Ensure the second db is still closed
        mock_get_data.return_value['repo2']['db'].close.assert_called_once_with()

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_calculating_deps_default(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        u1 = unit_generator(version='1.0.0')
        mock_unit_generator.return_value = [u1]
        u1_built_data = u1.build_dep_metadata(True)
        u1.build_dep_metadata = mock.Mock(return_value=u1_built_data)

        releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule')
        u1.build_dep_metadata.assert_called_once_with(True)

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_calculating_deps_recurse_false(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        u1 = unit_generator(version='1.0.0')
        mock_unit_generator.return_value = [u1]
        u1_built_data = u1.build_dep_metadata(False)
        u1.build_dep_metadata = mock.Mock(return_value=u1_built_data)

        releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule',
                      recurse_deps=False)
        u1.build_dep_metadata.assert_called_once_with(False)

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_filtering_version(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        u1 = unit_generator(version='1.0.0')
        u2 = unit_generator(version='2.0.0')
        mock_unit_generator.return_value = [u1, u2]

        result = releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule',
                               version='2.0.0')
        self.assertTrue('me/mymodule' in result)
        self.assertEquals(1, len(result['me/mymodule']))
        self.assertEquals('2.0.0', result['me/mymodule'][0]['version'])

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_filtering_view_all_true(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        u1 = unit_generator(version='1.0.0')
        u2 = unit_generator(version='2.0.0')
        mock_unit_generator.return_value = [u1, u2]

        result = releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule',
                               view_all_matching=True)
        self.assertTrue('me/mymodule' in result)
        self.assertEquals(2, len(result['me/mymodule']))

    @mock.patch.object(releases, 'unit_generator', autospec=True)
    @mock.patch.object(releases, 'get_repo_data', autospec=True)
    def test_filtering_view_all_false(self, mock_get_data, mock_unit_generator, mock_host):
        mock_get_data.return_value = {
            'repo1': {'db': mock.MagicMock(), 'protocol': 'http'},
        }
        u1 = unit_generator(version='1.0.0')
        u2 = unit_generator(version='3.0.0')
        u3 = unit_generator(version='2.0.0')
        mock_unit_generator.return_value = [u1, u2, u3]

        result = releases.view(constants.FORGE_NULL_AUTH_VALUE, 'repo_foo', 'me/mymodule',
                               view_all_matching=False)
        self.assertTrue('me/mymodule' in result)
        self.assertEquals(1, len(result['me/mymodule']))
        self.assertEquals('3.0.0', result['me/mymodule'][0]['version'])


class TestGetRepoData(unittest.TestCase):
    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_single_repo(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [{'repo_id':'repo1', 'config':{}}]

        result = releases.get_repo_data(['repo1'])

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result.keys(), ['repo1'])
        self.assertEqual(result['repo1']['db'], mock_open.return_value)
        mock_open.assert_called_once_with('/var/lib/pulp/published/puppet/http/repos/repo1/.dependency_db',
                                          'r')

    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_multiple_repos(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [
            {'repo_id':'repo1', 'config':{}},
            {'repo_id':'repo2', 'config':{}}
        ]

        result = releases.get_repo_data(['repo1', 'repo2'])

        self.assertTrue('repo1' in result)
        self.assertTrue('repo2' in result)

    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_configured_publish_dir(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [
            {'repo_id':'repo1',
             'config':{constants.CONFIG_HTTP_DIR: '/var/lib/pulp/published/puppet/foo'}}
        ]

        result = releases.get_repo_data(['repo1'])

        mock_open.assert_called_once_with('/var/lib/pulp/published/puppet/foo/repo1/.dependency_db', 'r')

    @mock.patch('web.ctx')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.find_by_repo_list')
    @mock.patch('gdbm.open', autospec=True)
    def test_db_open_error(self, mock_open, mock_find, mock_ctx):
        mock_ctx.protocol = 'http'
        mock_find.return_value = [{'repo_id':'repo1', 'config':{}}]
        mock_open.side_effect = gdbm.error

        result = releases.get_repo_data(['repo1'])

        self.assertEqual(result, {})
        mock_open.assert_called_once_with('/var/lib/pulp/published/puppet/http/repos/repo1/.dependency_db',
                                          'r')


class TestGetProtocol(unittest.TestCase):
    def test_default(self):
        result = releases._get_protocol_from_distributor({'config':{}})

        # http is currently the default protocol for publishes
        self.assertEqual(result, 'http')

    def test_no_config(self):
        # if there is no config, don't return a default. This is an error.
        self.assertRaises(KeyError, releases._get_protocol_from_distributor, {})

    def test_http(self):
        distributor = {'config': {constants.CONFIG_SERVE_HTTP: True}}
        result = releases._get_protocol_from_distributor(distributor)

        self.assertEqual(result, 'http')

    def test_https(self):
        distributor = {'config': {constants.CONFIG_SERVE_HTTPS: True}}
        result = releases._get_protocol_from_distributor(distributor)

        self.assertEqual(result, 'https')


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
