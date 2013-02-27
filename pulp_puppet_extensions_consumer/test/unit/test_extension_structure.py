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

import base_cli
from pulp_puppet.extensions.consumer import bind, pulp_cli, structure


class TestStructure(base_cli.ExtensionTests):
    def test_ensure_puppet_root(self):
        # Test
        returned_root_section = structure.ensure_puppet_root(self.cli)

        # Verify
        self.assertTrue(returned_root_section is not None)
        self.assertEqual(returned_root_section.name, structure.SECTION_ROOT)
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)
        self.assertEqual(puppet_root_section.name, structure.SECTION_ROOT)

    def test_ensure_puppet_root_idempotency(self):
        # Test
        structure.ensure_puppet_root(self.cli)
        returned_root_section = structure.ensure_puppet_root(self.cli)

        # Verify
        self.assertTrue(returned_root_section is not None)
        self.assertEqual(returned_root_section.name, structure.SECTION_ROOT)
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)
        self.assertEqual(puppet_root_section.name, structure.SECTION_ROOT)


class TestInit(base_cli.ExtensionTests):
    def test_init(self):
        pulp_cli.initialize(self.context)

        root = self.context.cli.find_subsection(structure.SECTION_ROOT)
        self.assertTrue(bind.BindCommand(self.context).name in root.commands)
        self.assertTrue(bind.UnbindCommand(self.context).name in root.commands)
