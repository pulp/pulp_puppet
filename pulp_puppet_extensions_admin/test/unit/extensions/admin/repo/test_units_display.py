# -*- coding: utf-8 -*-
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

from pulp_puppet.common.constants import TYPE_PUPPET_MODULE
from pulp_puppet.extensions.admin.repo import units_display


class UnitsDisplayTests(unittest.TestCase):

    def test_get_formatter_for_type(self):
        formatter = units_display.get_formatter_for_type(TYPE_PUPPET_MODULE)
        self.assertEquals('foo-bar-baz', formatter({'author': 'foo',
                                                    'name': 'bar',
                                                    'version': 'baz'}))

    def test_get_formatter_for_type_raises_value_error(self):
        self.assertRaises(ValueError, units_display.get_formatter_for_type, 'foo-type')