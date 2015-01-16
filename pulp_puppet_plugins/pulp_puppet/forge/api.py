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

import base64
import json
import re
import urllib

from pulp.server.db import connection
import web

from pulp_puppet.forge import releases

# This is all that is required to start using Manager classes
connection.initialize()

pre_33_urls = (
    '/releases.json', 'Releases',
)
post_33_urls = (
    '/([^/]+)/([^/]+)/api/v1/releases.json', 'Releases',
)

post_36_urls = (
    '/releases', 'ReleasesPost36',
)

pre_33_app = web.application(pre_33_urls, globals())
post_33_app = web.application(post_33_urls, globals())
post_36_app = web.application(post_36_urls, globals())

MODULE_PATTERN = re.compile('(^[a-zA-Z0-9]+)(/|-)([a-zA-Z0-9_]+)$')


class Releases(object):
    REPO_RESOURCE = 'repository'
    CONSUMER_RESOURCE = 'consumer'

    def GET(self, resource_type=None, resource=None):
        """
        Credentials here are not actually used for authorization, but instead
        are used to identify:

            consumer ID in the username field
            repository ID in the password field

        This is to work around the fact that the "puppet module install"
        command has hard-coded absolute paths, so we cannot put consumer or
        repository IDs in the URL's path.
        """
        if resource_type is not None:
            if resource_type == self.REPO_RESOURCE:
                credentials = ('.', resource)
            elif resource_type == self.CONSUMER_RESOURCE:
                credentials = (resource, '.')
            else:
                return web.notfound()

        else:
            credentials = self._get_credentials()
            if not credentials:
                return web.unauthorized()

        module_name = self._get_module_name()
        if not module_name:
            # apparently our version of web.py, 0.36, doesn't take a message
            # parameter for error handlers like this one. Ugh.
            return web.badrequest()
        version = web.input().get('version')

        data = self.get_releases(*credentials, module_name=module_name, version=version)
        return self.format_results(data)

    def get_releases(self, *args, **kwargs):
        """
        Get the list of matching releases

        :return: The matching modules
        :rtype: dict
        """
        return releases.view(*args, **kwargs)

    def format_results(self, data):
        """
        Format the results and begin streaming out to the caller

        :param data: The module data to stream back to the caller
        :type data: dict
        :return: the body of what should be streamed out to the caller
        :rtype: str
        """
        web.header('Content-Type', 'application/json')
        return json.dumps(data)

    @staticmethod
    def _get_credentials():
        """
        :return: username and password provided as basic auth credentials
        :rtype:  str, str
        """
        auth = web.ctx.env.get('HTTP_AUTHORIZATION')
        if auth:
            encoded_credentials = re.sub('^Basic ', '', auth)
            try:
                username, password = base64.decodestring(encoded_credentials).split(':')
            # raised by the split if the decoded string lacks a ':'
            except ValueError:
                return
            return username, password

    @staticmethod
    def _get_module_name():
        """
        :return: name of the module being requested, or None if not found or invalid
        """
        module_name = web.input().get('module', '')
        match = MODULE_PATTERN.match(module_name)
        if match:
            normalized_name = u'%s/%s' % (match.group(1), match.group(3))
            return normalized_name


class ReleasesPost36(Releases):

    @staticmethod
    def _format_query_string(base_url, module_name, module_version, offset, limit):
        """
        Build the query string to be used for creating

        :param base_url: The context root to sue when generating a releases query.
        :type base_url: str
        :param module_name: The module name to add to the query string
        :type module_name: str
        :param module_version: The version of the module to encode in the query string
        :type module_version: str
        :param offset: The offset to encode for pagination
        :type offset: int
        :param limit: The max number of items to show on a page
        :type limit: int
        :return: The encoded URL for the specified query arguments
        :rtype: str
        """
        query_args = {'module': module_name,
                      'offset': offset,
                      'limit': limit}
        if module_version:
            query_args['version'] = module_version

        return '%s?%s' % (base_url, urllib.urlencode(query_args))

    def get_releases(self, *args, **kwargs):
        """
        Get the list of matching releases

        :return: The matching modules
        :rtype: dict
        """
        return releases.view(*args, recurse_deps=False, view_all_matching=True, **kwargs)

    def format_results(self, data):
        """
        Format the results and begin streaming out to the caller for the v3 API

        :param data: The module data to stream back to the caller
        :type data: dict
        :return: the body of what should be streamed out to the caller
        :rtype: str
        """
        web.header('Content-Type', 'application/json')
        limit = int(web.input().get('limit', 20))
        current_offset = int(web.input().get('offset', 0))
        module_name = web.input().get('module', '')
        module_version = web.input().get('version', None)
        base_url_string = '/v3%s' % web.ctx.path

        first_path = self._format_query_string(base_url_string, module_name, module_version,
                                               0, limit)
        current_path = self._format_query_string(base_url_string, module_name, module_version,
                                                 current_offset, limit)
        if current_offset > 0:
            previous_path = self._format_query_string(base_url_string, module_name, module_version,
                                                      current_offset - limit, limit)
        else:
            previous_path = None

        formatted_results = {
            'pagination': {
                'limit': limit,
                'offset': current_offset,
                'first': first_path,
                'previous': previous_path,
                'current': current_path,
                'next': None,
                'total': 1
            },
            'results': []
        }
        module_list = data.get(self._get_module_name())
        total_count = len(module_list)

        for module in module_list[current_offset: (current_offset + limit)]:
            formatted_dependencies = []
            for dep in module.get('dependencies', []):
                formatted_dependencies.append({
                    'name': dep[0],
                    'version_requirement': dep[1]
                })
            module_data = {
                'metadata': {
                    'name': module_name,
                    'version': module.get('version'),
                    'dependencies': formatted_dependencies
                },
                'file_uri': module.get('file'),
                'file_md5': module.get('file_md5')
            }

            formatted_results['results'].append(module_data)

        formatted_results['pagination']['total'] = total_count

        if total_count > (current_offset + limit):
            next_path = self._format_query_string(base_url_string, module_name, module_version,
                                                  current_offset + limit, limit)
            formatted_results['pagination']['next'] = next_path

        return json.dumps(formatted_results)

if __name__ == '__main__':
    # run this app stand-alone, useful for testing
    post_33_app.run()
