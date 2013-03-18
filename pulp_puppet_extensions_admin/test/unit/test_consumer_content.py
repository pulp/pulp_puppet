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
from pulp.bindings.responses import Task, STATE_FINISHED
from pulp.client.commands.consumer.content import ConsumerContentUpdateCommand, ConsumerContentUninstallCommand

import base_cli
from pulp_puppet.common import constants
from pulp_puppet.extensions.admin.consumer import content

class TestParseUnits(unittest.TestCase):
    def test_empty_list(self):
        result = content.parse_units([])

        self.assertEqual(result, [])

    def test_invalid_name(self):
        self.assertRaises(ValueError, content.parse_units, ['notvalid'])

    def test_burried_invalid_name(self):
        units = ['foo/bar', 'a/b/1.2.3', 'puppetlabs/stdlib', 'notvalid', 'x/y']

        self.assertRaises(ValueError, content.parse_units, units)

    def test_single_unit(self):
        result = content.parse_units(['foo/bar'])

        self.assertEqual(len(result), 1)
        unit = result[0]
        self.assertEqual(unit.get('type_id'), constants.TYPE_PUPPET_MODULE)
        unit_key = unit.get('unit_key', {})
        self.assertEqual(unit_key.get('author'), 'foo')
        self.assertEqual(unit_key.get('name'), 'bar')
        self.assertTrue('version' not in unit_key)

    def test_single_unit_with_version(self):
        result = content.parse_units(['foo/bar/1.2.3'])

        self.assertEqual(len(result), 1)
        unit = result[0]
        self.assertEqual(unit.get('type_id'), constants.TYPE_PUPPET_MODULE)
        unit_key = unit.get('unit_key', {})
        self.assertEqual(unit_key.get('author'), 'foo')
        self.assertEqual(unit_key.get('name'), 'bar')
        self.assertEqual(unit_key.get('version'), '1.2.3')

    def test_units(self):
        result = content.parse_units(['foo/bar', 'abc/xyz'])

        self.assertEqual(len(result), 2)
        for unit in result:
            self.assertEqual(unit.get('type_id'), constants.TYPE_PUPPET_MODULE)
            unit_key = unit.get('unit_key', {})
            self.assertTrue(unit_key.get('author') in ['foo', 'abc'])
            self.assertTrue(unit_key.get('name') in ['bar', 'xyz'])
            self.assertTrue('version' not in unit_key)


class TestContentMixin(base_cli.ExtensionTests):
    TASK_TEMPLATE = {
        "call_request_group_id": 'default-group',
        "call_request_id": 'default-id',
        "call_request_tags": [],
        "exception": None,
        "finish_time": None,
        "progress": {},
        "reasons": [],
        "response": None,
        "result": None,
        "schedule_id": None,
        "start_time": None,
        "state": STATE_FINISHED,
        "traceback": None,
    }

    def setUp(self):
        super(TestContentMixin, self).setUp()
        # makes a good example of a plain use of this mixing
        self.command = content.UpdateCommand(self.context)

    def _generate_details(self, contents=None):
        return {constants.TYPE_PUPPET_MODULE: {'details': contents or {}}}

    def test_add_content_options(self):
        command = content.ContentMixin('', '', mock.MagicMock())
        command.add_content_options()

        self.assertEqual(len(command.options), 1)
        option = command.options[0]

        self.assertEqual(option.keyword, content.OPTION_CONTENT_UNIT_REQUIRED.keyword)
        self.assertTrue(option.required)

    def test_get_content_units(self):
        units = ['a/b', 'c/d']
        result = self.command.get_content_units({content.OPTION_CONTENT_UNIT.keyword: units})

        self.assertEqual(units, result)
        self.assertEqual(units[0], result[0])
        self.assertEqual(units[1], result[1])

    def test_succeeded_no_change(self):
        task = Task(self.TASK_TEMPLATE)
        task.result = {
            'details': {constants.TYPE_PUPPET_MODULE: {'details': {}}},
            'num_changes': 0
        }
        self.command.succeeded('', task)

        tags = self.prompt.get_write_tags()
        self.assertTrue(content.TAG_NO_CHANGES in tags)

    def test_succeeded_one_change(self):
        task = Task(self.TASK_TEMPLATE)
        task.result = {
            'details': self._generate_details(),
            'num_changes': 1
        }
        self.command.succeeded('', task)

        tags = self.prompt.get_write_tags()
        self.assertTrue(content.TAG_CHANGE_MADE in tags)

    def test_succeeded_multiple_changes(self):
        task = Task(self.TASK_TEMPLATE)
        task.result = {
            'details': self._generate_details(),
            'num_changes': 2
        }
        self.command.succeeded('', task)

        tags = self.prompt.get_write_tags()
        self.assertTrue(content.TAG_CHANGE_MADE in tags)
        # make sure it's just 1 message even though there were 2 changes
        self.assertEqual(len(filter(lambda x: x==content.TAG_CHANGE_MADE, tags)), 1)

    @mock.patch('pulp_puppet.extensions.admin.consumer.content.ContentMixin._render_error_messages')
    def test_succeeded_hands_off_errors(self, mock_render):
        task = Task(self.TASK_TEMPLATE)
        task.result = {
            'details': self._generate_details({'errors': {'foo/bar': {}}}),
            'num_changes': 1
        }
        self.command.succeeded('', task)

        mock_render.assert_called_once_with(task.result)

    def test_render_errors_empty(self):
        result = {
            'details': self._generate_details({'errors':{}}),
            'num_changes': 5
        }

        self.command._render_error_messages(result)

        tags = self.prompt.get_write_tags()
        self.assertEqual(len(tags), 0)

    def test_render_errors_one(self):
        result = {
            'details': self._generate_details({'errors': {'foo/bar': {}}}),
            'num_changes': 5
        }

        self.command._render_error_messages(result)

        tags = self.prompt.get_write_tags()
        self.assertEqual(len(tags), 1)
        self.assertTrue(content.TAG_ERROR in tags)

    def test_render_errors_two(self):
        result = {
            'details': self._generate_details({'errors': {'foo/bar': {}, 'a/b': {}}}),
            'num_changes': 5
        }

        self.command._render_error_messages(result)

        tags = self.prompt.get_write_tags()
        # make sure there were two error tags
        self.assertEqual(len(tags), 2)
        self.assertEqual(len(filter(lambda x: x==content.TAG_ERROR, tags)), 2)

    def test_render_errors_ten(self):
        result = {
            'details': self._generate_details({'errors': {
                'foo/bar': {},
                'a/b': {},
                'a/c': {},
                'a/d': {},
                'a/e': {},
                'a/f': {},
                'a/g': {},
                'a/h': {},
                'a/i': {},
                'a/j': {},
            }}),
            'num_changes': 5
        }

        self.command._render_error_messages(result)

        # should print the first 5, then a message that the rest were truncated
        tags = self.prompt.get_write_tags()
        self.assertEqual(len(tags), 6)
        self.assertTrue(content.TAG_TRUNCATED in tags)
        self.assertEqual(len(filter(lambda x: x==content.TAG_ERROR, tags)), 5)


class TestInstallCommand(base_cli.ExtensionTests):
    def setUp(self):
        super(TestInstallCommand, self).setUp()
        # makes a good example of a plain use of this mixing
        self.command = content.InstallCommand(self.context)

    def test_add_content_options(self):
        # make sure it adds our content unit option
        options = [opt for opt in self.command.options if opt.keyword == content.OPTION_CONTENT_UNIT.keyword]
        self.assertEqual(len(options), 1)

        option = options[0]

        self.assertFalse(option.required)

    def test_add_install_options(self):
        # make sure it adds our content unit option
        options = [opt for opt in self.command.options if opt.keyword == content.OPTION_WHOLE_REPO.keyword]
        self.assertEqual(len(options), 1)

    @mock.patch.object(content.ContentMixin, 'get_content_units')
    def test_get_content_units_normal(self, mock_get_units):
        kwargs = {'foo': 'bar'}
        result = self.command.get_content_units(kwargs)

        mock_get_units.assert_called_once_with(kwargs)
        self.assertEqual(result, mock_get_units.return_value)

    @mock.patch.object(content.ContentMixin, 'get_content_units')
    def test_get_content_units_whole_repo(self, mock_get_units):
        kwargs = {content.OPTION_WHOLE_REPO.keyword: 'repo1'}
        result = self.command.get_content_units(kwargs)

        self.assertEqual(mock_get_units.call_count, 0)
        self.assertEqual(len(result), 1)
        unit = result[0]
        self.assertEqual(unit['type_id'], constants.TYPE_PUPPET_MODULE)
        self.assertTrue(unit['unit_key'] is None)

    @mock.patch('pulp.client.commands.consumer.content.ConsumerContentInstallCommand.get_install_options')
    def test_get_install_options_not_present(self, mock_get_options):
        kwargs = {'foo': 'bar'}

        result = self.command.get_install_options(kwargs)

        # makes sure the parent class was called
        mock_get_options.assert_called_once_with(kwargs)
        self.assertEqual(result, mock_get_options.return_value)

    @mock.patch('pulp.client.commands.consumer.content.ConsumerContentInstallCommand.get_install_options')
    def test_get_install_options_not_present(self, mock_get_options):
        kwargs = {content.OPTION_WHOLE_REPO.keyword: 'repo1'}

        result = self.command.get_install_options(kwargs)

        # parent class not called
        self.assertEqual(mock_get_options.call_count, 0)
        self.assertEqual(result[constants.REPO_ID_OPTION], 'repo1')
        self.assertTrue(result[constants.WHOLE_REPO_OPTION] is True)

    @mock.patch('pulp.client.commands.consumer.content.ConsumerContentInstallCommand.run')
    def test_run_normal(self, mock_run):
        kwargs = {content.OPTION_CONTENT_UNIT.keyword: ['foo/bar']}
        self.command.run(**kwargs)

        mock_run.assert_called_once_with(**kwargs)

    @mock.patch('pulp.client.commands.consumer.content.ConsumerContentInstallCommand.run')
    def test_run_whole_repo(self, mock_run):
        kwargs = {
            content.OPTION_WHOLE_REPO.keyword: 'repo1',
            content.OPTION_CONTENT_UNIT.keyword: [],
        }
        self.command.run(**kwargs)

        mock_run.assert_called_once_with(**kwargs)

    @mock.patch('pulp.client.commands.consumer.content.ConsumerContentInstallCommand.run')
    def test_run_no_units(self, mock_run):
        kwargs = {
            content.OPTION_WHOLE_REPO.keyword: None,
            content.OPTION_CONTENT_UNIT.keyword: [],
        }
        self.command.run(**kwargs)

        # make sure it complains that we didn't specify any units
        self.assertEqual(mock_run.call_count, 0)
        tags = self.prompt.get_write_tags()
        self.assertTrue(content.TAG_INVALID_INPUT in tags)


class TestUpdateCommand(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(content.UpdateCommand, content.ContentMixin))
        self.assertTrue(issubclass(content.UpdateCommand, ConsumerContentUpdateCommand))


class TestUninstallCommand(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(content.UninstallCommand, content.ContentMixin))
        self.assertTrue(issubclass(content.UninstallCommand, ConsumerContentUninstallCommand))
