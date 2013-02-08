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

import mock
import web

from pulp_puppet.forge import api


class TestApp(unittest.TestCase):
    FAKE_VIEW_DATA = {
        'foo/bar' : [{'version' : '1.0.0', 'file': '/tmp/foo', 'dependencies': []}]
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
        result = api.app.request(self.make_path())
        self.assertEqual(result.status, '401 Unauthorized')

    def test_404_at_root(self):
        result = api.app.request('/')
        self.assertEqual(result.status, '404 Not Found')

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(api.Releases, '_get_credentials')
    def test_normal(self, mock_get_cred, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_view.return_value = self.FAKE_VIEW_DATA

        result = api.app.request(self.make_path('foo/bar'))

        self.assertEqual(result.status, '200 OK')
        self.assertEqual(result.headers['Content-Type'], 'application/json')
        self.assertEqual(result.data, json.dumps(self.FAKE_VIEW_DATA))
        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar', version=None)

    @mock.patch('pulp_puppet.forge.releases.view', autospec=True)
    @mock.patch.object(api.Releases, '_get_credentials')
    def test_with_version(self, mock_get_cred, mock_view):
        mock_get_cred.return_value = ('consumer1', 'repo1')
        mock_view.return_value = {}

        result = api.app.request(self.make_path('foo/bar', '1.0.0'))

        self.assertEqual(result.status, '200 OK')
        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar', version='1.0.0')


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

        mock_view.assert_called_once_with('consumer1', 'repo1', module_name='foo/bar', version='1.0.0')


class TestGetCredentials(unittest.TestCase):
    @mock.patch('web.ctx')
    def test_normal(self, mock_ctx):
        mock_ctx.env = {'HTTP_AUTHORIZATION' : 'Basic aGV5aXRzbWU6bGV0bWVpbg=='}
        result = api.Releases._get_credentials()
        self.assertEqual(result, ('heyitsme', 'letmein'))

    @mock.patch('web.ctx')
    def test_invalid_string(self, mock_ctx):
        mock_ctx.env = {'HTTP_AUTHORIZATION' : 'Basic notreallyencoded'}
        result = api.Releases._get_credentials()
        self.assertTrue(result is None)

    @mock.patch('web.ctx')
    def test_not_provided(self, mock_ctx):
        mock_ctx.env = {}
        result = api.Releases._get_credentials()
        self.assertTrue(result is None)


class TestGetModuleName(unittest.TestCase):
    @mock.patch('web.input', autospec=True, return_value={'module':'foo/bar'})
    def test_normal(self, mock_input):
        result = api.Releases._get_module_name()

        self.assertEqual(result, 'foo/bar')
        mock_input.assert_called_once_with()

    @mock.patch('web.input', autospec=True, return_value={})
    def test_not_provided(self, mock_input):
        result = api.Releases._get_module_name()

        self.assertTrue(result is None)
        mock_input.assert_called_once_with()
