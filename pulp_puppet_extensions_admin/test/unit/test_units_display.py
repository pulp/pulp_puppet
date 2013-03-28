# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
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

import okaara.prompt
from pulp.client.extensions.core import PulpPrompt

from pulp_puppet.common import constants
from pulp_puppet.extensions.admin.repo import units_display


class UnitsDisplayTests(unittest.TestCase):

    def setUp(self):
        super(UnitsDisplayTests, self).setUp()

        # Disabling color makes it easier to grep results since the character codes aren't there
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)

    def test_display_modules_zero_count(self):
        # Test
        units_display.display_modules(self.prompt, [], 10)

        # Verify
        self.assertEqual(['too-few'], self.prompt.get_write_tags())

    def test_display_modules_over_threshold(self):
        # Test
        copied_modules = self._generate_copied_modules(10)
        units_display.display_modules(self.prompt, copied_modules, 5)

        # Verify
        self.assertEqual(['too-many'], self.prompt.get_write_tags())
        self.assertTrue('10' in self.recorder.lines[0])

    def test_display_modules_show_modules(self):
        # Test
        copied_modules = self._generate_copied_modules(2)

        # Reverse here so we can check the sort takes place in the method
        copied_modules.sort(key=lambda x : x['unit_key']['author'], reverse=True)

        units_display.display_modules(self.prompt, copied_modules, 10)

        # Verify
        expected_tags = ['just-enough', 'module', 'module']  # header + one line for each module
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertTrue('Modules' in self.recorder.lines[0])

        # Verify the sorting was done
        self.assertTrue('0' in self.recorder.lines[1])
        self.assertTrue('1' in self.recorder.lines[2])

    def _generate_copied_modules(self, count):
        """
        Returns a list of the given size representing modules as they would be handed to
        the display method.
        """
        modules = []
        for i in range(0, count):
            unit_key = {
                'author' : 'author-%s' % i,
                'name' : 'name-%s' % i,
                'version' : 'version-%s' % i,
            }
            modules.append({'type_id' : constants.TYPE_PUPPET_MODULE,
                            'unit_key' : unit_key})

        return modules
