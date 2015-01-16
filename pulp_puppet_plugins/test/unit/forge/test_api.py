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

import json
import unittest
import urlparse

import mock
from pulp.server.db.connection import initialize
import web

from pulp_puppet.forge import api

initialize(name='pulp_unittest')

class TestAppPre33(unittest.TestCase):
    app = api.pre_33_app
    FAKE_VIEW_DATA = {
        'foo/bar': [{'version': '1.0.0', 'file': '/tmp/foo', 'dependencies': []}]
    }

    @staticmethod
    def make_path(name=None, version=None):
        path = '/releases.json'
        if name:
            path += '?module=%s' % name
            if version:
                path += '&version=%s' % version
        return path

    def test_no_credentials(self):
        result = self.app.request(self.make_path())
        self.assertEqual(result.status, '401 Unauthorized')

    def test_404_at_root(self):
        result = self.app.request('/')
        self.assertEqual(result.status, '404 Not Found')

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(api.Releases, '_get_credentials')
    def test_normal(self, mock_get_cred, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_view.return_value = self.FAKE_VIEW_DATA

        result = self.app.request(self.make_path('foo/bar'))

        self.assertEqual(result.status, '200 OK')
        self.assertEqual(result.headers['Content-Type'], 'application/json')
        self.assertEqual(result.data, json.dumps(self.FAKE_VIEW_DATA))
        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar', version=None)

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(api.Releases, '_get_credentials')
    def test_with_version(self, mock_get_cred, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_view.return_value = {}

        result = self.app.request(self.make_path('foo/bar', '1.0.0'))

        self.assertEqual(result.status, '200 OK')
        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar',
                                          version='1.0.0')


class TestAppPost33(unittest.TestCase):
    app = api.post_33_app
    FAKE_VIEW_DATA = {
        'foo/bar': [{'version': '1.0.0', 'file': '/tmp/foo', 'dependencies': []}]
    }

    @staticmethod
    def make_path(repo=None, consumer=None, name=None, version=None):
        if repo:
            base = '/repository/%s/api/v1/releases.json' % repo
        else:
            base = '/consumer/%s/api/v1/releases.json' % consumer

        if name:
            base += '?module=%s' % name
            if version:
                base += '&version=%s' % version
        return base

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    def test_normal_with_repo(self, mock_view):
        mock_view.return_value = self.FAKE_VIEW_DATA

        path = self.make_path('repo1', None, 'foo/bar')
        result = self.app.request(path)

        self.assertEqual(result.status, '200 OK')
        self.assertEqual(result.headers['Content-Type'], 'application/json')
        self.assertEqual(result.data, json.dumps(self.FAKE_VIEW_DATA))
        mock_view.assert_called_once_with('.', 'repo1', module_name='foo/bar', version=None)

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    def test_normal_with_consumer(self, mock_view):
        mock_view.return_value = self.FAKE_VIEW_DATA

        path = self.make_path(None, 'consumer1', 'foo/bar')
        result = self.app.request(path)

        self.assertEqual(result.status, '200 OK')
        self.assertEqual(result.headers['Content-Type'], 'application/json')
        self.assertEqual(result.data, json.dumps(self.FAKE_VIEW_DATA))
        mock_view.assert_called_once_with('consumer1', '.', module_name='foo/bar', version=None)

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    def test_with_version(self, mock_view):
        mock_view.return_value = {}

        result = self.app.request(self.make_path('repo1', None, 'foo/bar', '1.0.0'))

        self.assertEqual(result.status, '200 OK')
        mock_view.assert_called_once_with('.', 'repo1', module_name='foo/bar', version='1.0.0')

    def test_invalid_resource_type(self):
        result = self.app.request('/notatype/foo/api/v1/releases.json?module=foo/bar')

        self.assertEqual(result.status, '404 Not Found')


# these header objects are very annoying to mock out, and we really just want
# them to stay out of the way.
@mock.patch.object(web, 'header', new=mock.MagicMock())
@mock.patch.object(web.webapi, 'ctx', new=mock.MagicMock())
class TestGET(unittest.TestCase):
    @mock.patch('web.ctx')
    def test_no_credentials(self, mock_ctx):
        mock_ctx.env = {}

        result = api.Releases().GET()
        self.assertTrue(isinstance(result, web.webapi.Unauthorized))

    @mock.patch('web.ctx')
    @mock.patch.object(api.Releases, '_get_credentials')
    @mock.patch.object(api.Releases, '_get_module_name')
    def test_no_module_name(self, mock_get_name, mock_get_cred, mock_ctx):
        mock_get_name.return_value = None
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_ctx.env = {}

        result = api.Releases().GET()
        self.assertTrue(isinstance(result, web.webapi.BadRequest))

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(web, 'input')
    @mock.patch.object(api.Releases, '_get_credentials')
    @mock.patch.object(api.Releases, '_get_module_name')
    def test_no_version(self, mock_get_name, mock_get_cred, mock_input, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_get_name.return_value = 'foo/bar'
        mock_input.return_value = {}
        mock_view.return_value = {}

        result = api.Releases().GET()

        self.assertEqual(result, json.dumps({}))
        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar', version=None)

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(web, 'input')
    @mock.patch.object(api.Releases, '_get_credentials')
    @mock.patch.object(api.Releases, '_get_module_name')
    def test_with_version(self, mock_get_name, mock_get_cred, mock_input, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_get_name.return_value = 'foo/bar'
        mock_input.return_value = {'version': '1.0.0'}
        mock_view.return_value = {}

        result = api.Releases().GET()
        self.assertEqual(result, json.dumps({}))

        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar',
                                          version='1.0.0')


class TestGetCredentials(unittest.TestCase):
    @mock.patch('web.ctx')
    def test_normal(self, mock_ctx):
        mock_ctx.env = {'HTTP_AUTHORIZATION': 'Basic aGV5aXRzbWU6bGV0bWVpbg=='}
        result = api.Releases._get_credentials()
        self.assertEqual(result, ('heyitsme', 'letmein'))

    @mock.patch('web.ctx')
    def test_invalid_string(self, mock_ctx):
        mock_ctx.env = {'HTTP_AUTHORIZATION': 'Basic notreallyencoded'}
        result = api.Releases._get_credentials()
        self.assertTrue(result is None)

    @mock.patch('web.ctx')
    def test_not_provided(self, mock_ctx):
        mock_ctx.env = {}
        result = api.Releases._get_credentials()
        self.assertTrue(result is None)


class TestGetModuleName(unittest.TestCase):
    @mock.patch('web.input', autospec=True, return_value={'module': 'foo/bar'})
    def test_normal(self, mock_input):
        result = api.Releases._get_module_name()

        self.assertEqual(result, 'foo/bar')
        mock_input.assert_called_once_with()

    @mock.patch('web.input', autospec=True, return_value={})
    def test_not_provided(self, mock_input):
        result = api.Releases._get_module_name()

        self.assertTrue(result is None)
        mock_input.assert_called_once_with()


class TestPost36(unittest.TestCase):

    @mock.patch('pulp_puppet.forge.api.releases.view')
    def test_get_releases(self, mock_view):
        release = api.ReleasesPost36()
        release.get_releases()
        mock_view.assert_called_once_with(recurse_deps=False,
                                          view_all_matching=True)

    def test_format_query_string_no_version(self):
        result = api.ReleasesPost36._format_query_string(
            base_url='https://foo.com/api/v3/',
            module_name='modulename', module_version=None,
            offset=5, limit=2
        )

        data = urlparse.urlparse(result)
        self.assertEquals('https', data.scheme)
        self.assertEquals('foo.com', data.netloc)
        self.assertEquals('/api/v3/', data.path)

        query = urlparse.parse_qs(data.query)
        self.assertEquals(['modulename'], query['module'])
        self.assertEquals(['2'], query['limit'])
        self.assertEquals(['5'], query['offset'])
        self.assertTrue('version' not in query)

    def test_format_query_string_with_version(self):
        result = api.ReleasesPost36._format_query_string(
            base_url='https://foo.com/api/v3/',
            module_name='modulename', module_version='3.5',
            offset=5, limit=2
        )
        data = urlparse.urlparse(result)
        query = urlparse.parse_qs(data.query)
        self.assertEquals(['3.5'], query['version'])

    @mock.patch('web.ctx')
    @mock.patch('web.header')
    @mock.patch('web.input', autospec=True, return_value={'module': 'foo/bar'})
    def test_format_results_pagination_defaults(self, mock_input, mock_hdr, mock_ctx):
        release = api.ReleasesPost36()
        mock_ctx.path = 'releases/'
        result_str = release.format_results({'foo/bar': []})
        result = json.loads(result_str)

        self.assertEquals(20, result['pagination']['limit'])
        self.assertEquals(0, result['pagination']['offset'])
        self.assertEquals(0, result['pagination']['total'])
        self.assertEquals(u'/v3releases/?limit=20&module=foo%2Fbar&offset=0',
                          result['pagination']['first'])
        self.assertEquals(u'/v3releases/?limit=20&module=foo%2Fbar&offset=0',
                          result['pagination']['current'])
        self.assertEquals(None, result['pagination']['previous'])
        self.assertEquals(None, result['pagination']['next'])

    @mock.patch('web.ctx')
    @mock.patch('web.header')
    @mock.patch('web.input', autospec=True, return_value={'module': 'foo/bar',
                                                          'limit': '1',
                                                          'offset': '1'})
    def test_format_results_pagination_middle_page(self, mock_input, mock_hdr, mock_ctx):
        release = api.ReleasesPost36()
        mock_ctx.path = 'releases/'
        result_str = release.format_results({'foo/bar': [
            {'dependencies': [], 'version': '1.0', 'file': 'foo', 'file_md5': 'bar'},
            {'dependencies': [], 'version': '2.0', 'file': 'foo', 'file_md5': 'bar'},
            {'dependencies': [], 'version': '3.0', 'file': 'foo', 'file_md5': 'bar'},
        ]})
        result = json.loads(result_str)

        self.assertEquals(1, result['pagination']['limit'])
        self.assertEquals(1, result['pagination']['offset'])
        self.assertEquals(3, result['pagination']['total'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=0',
                          result['pagination']['first'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=0',
                          result['pagination']['previous'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=1',
                          result['pagination']['current'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=2',
                          result['pagination']['next'])
        self.assertEquals(1, len(result['results']))
        self.assertEquals('2.0', result['results'][0]['metadata']['version'])

    @mock.patch('web.ctx')
    @mock.patch('web.header')
    @mock.patch('web.input', autospec=True, return_value={'module': 'foo/bar',
                                                          'limit': '1',
                                                          'offset': '2'})
    def test_format_results_pagination_last_page(self, mock_input, mock_hdr, mock_ctx):
        release = api.ReleasesPost36()
        mock_ctx.path = 'releases/'
        result_str = release.format_results({'foo/bar': [
            {'dependencies': [], 'version': '1.0', 'file': 'foo', 'file_md5': 'bar'},
            {'dependencies': [], 'version': '2.0', 'file': 'foo', 'file_md5': 'bar'},
            {'dependencies': [], 'version': '3.0', 'file': 'foo', 'file_md5': 'bar'},
        ]})
        result = json.loads(result_str)

        self.assertEquals(1, result['pagination']['limit'])
        self.assertEquals(2, result['pagination']['offset'])
        self.assertEquals(3, result['pagination']['total'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=0',
                          result['pagination']['first'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=1',
                          result['pagination']['previous'])
        self.assertEquals(u'/v3releases/?limit=1&module=foo%2Fbar&offset=2',
                          result['pagination']['current'])
        self.assertEquals(None, result['pagination']['next'])
        self.assertEquals(1, len(result['results']))
        self.assertEquals('3.0', result['results'][0]['metadata']['version'])

    @mock.patch('web.ctx')
    @mock.patch('web.header')
    @mock.patch('web.input', autospec=True, return_value={'module': 'foo/bar'})
    def test_format_results_render_module(self, mock_input, mock_hdr, mock_ctx):
        release = api.ReleasesPost36()
        mock_ctx.path = 'releases/'
        result_str = release.format_results({'foo/bar': [
            {'dependencies': [('apple', '42.5')],
             'version': '1.0', 'file': 'foo', 'file_md5': 'bar'},
        ]})
        result = json.loads(result_str)

        module_data = result['results'][0]
        self.assertEquals('foo/bar', module_data['metadata']['name'])
        self.assertEquals('1.0', module_data['metadata']['version'])
        self.assertEquals('foo', module_data['file_uri'])
        self.assertEquals('bar', module_data['file_md5'])
        dependencies = module_data['metadata']['dependencies']
        self.assertEquals('apple', dependencies[0]['name'])
        self.assertEquals('42.5', dependencies[0]['version_requirement'])
