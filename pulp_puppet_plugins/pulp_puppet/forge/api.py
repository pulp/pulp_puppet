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

from pulp.server.db import connection
import web

from pulp_puppet.forge import releases

# This is all that is required to start using Manager classes
connection.initialize()

urls = (
    '/releases.json', 'Releases',
)

app = web.application(urls, globals())

MODULE_PATTERN = re.compile('^[a-zA-Z0-9]+/[a-zA-Z0-9_]+$')


class Releases(object):
    def GET(self):
        credentials = self._get_credentials()
        if not credentials:
            return web.unauthorized()

        module_name = self._get_module_name()
        if not module_name:
            # apparently our version of web.py, 0.36, doesn't take a message
            # parameter for error handlers like this one. Ugh.
            return web.badrequest()
        version =  web.input().get('version')

        web.header('Content-Type', 'application/json')
        data = releases.view(*credentials, module_name=module_name, version=version)
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
        if MODULE_PATTERN.match(module_name):
            return module_name


if __name__ == '__main__':
    # run this app stand-alone, useful for testing
    app.run()
