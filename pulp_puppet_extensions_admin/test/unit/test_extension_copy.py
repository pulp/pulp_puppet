# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.bindings.exceptions import BadRequestException
from pulp.common.compat import json
from pulp.client.commands.unit import UnitCopyCommand
from pulp.client.extensions.core import TAG_REASONS

import base_cli
from pulp_puppet.common import constants
from pulp_puppet.extensions.admin.repo import copy_modules as copy_commands

class CopyCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(CopyCommandTests, self).setUp()
        self.command = copy_commands.PuppetModuleCopyCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UnitCopyCommand))
        self.assertEqual(self.command.name, 'copy')
        self.assertEqual(self.command.description, copy_commands.DESC_COPY)
        self.assertEqual(self.command.method, self.command.run)

    def test_run(self):
        # Setup
        data = {
            'from-repo-id' : 'from',
            'to-repo-id' : 'to'
        }

        self.server_mock.request.return_value = 202, self.task()

        # Test
        self.command.run(**data)

        # Verify
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual('POST', call_args[0])
        self.assertTrue(call_args[1].endswith('/to/actions/associate/'))

        body = json.loads(call_args[2])
        self.assertEqual(body['source_repo_id'], 'from')
        self.assertEqual(body['criteria']['type_ids'], [constants.TYPE_PUPPET_MODULE])

        self.assertEqual(['progress'], self.prompt.get_write_tags())

    def test_run_postponed(self):
        # Setup
        data = {
            'from-repo-id' : 'from',
            'to-repo-id' : 'to'
        }

        task = self.task()
        task['response'] = 'postponed'
        task['state'] = 'waiting'
        self.server_mock.request.return_value = 202, task

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(['postponed', TAG_REASONS], self.prompt.get_write_tags())

    def test_run_invalid_source_repo(self):
        # Setup
        data = {
            'from-repo-id' : 'from',
            'to-repo-id' : 'to',
        }

        error_report =  {
            'exception': None,
            'traceback': None,
            'property_names': [
                'source_repo_id'
            ],
            '_href': '/pulp/api/v2/repositories/test-repo/actions/associate/',
            'error_message': 'Invalid properties: [\'source_repo_id\']',
            'http_request_method': 'POST',
            'http_status': 400
        }

        self.server_mock.request.return_value = 400, error_report

        # Test
        try:
            self.command.run(**data)
            self.fail('Expected bad data exception')
        except BadRequestException, e:
            # Verify the translation from server-side property name to
            # client-side flag took place
            self.assertEqual(['from-repo-id'], e.extra_data['property_names'])
            self.assertTrue('source_repo_id' not in e.extra_data['property_names'])
