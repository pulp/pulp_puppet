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

from pulp_puppet.devel import base_cli
from pulp_puppet.extensions.admin import structure

class StructureTests(base_cli.ExtensionTests):

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

    def test_ensure_repo_structure_no_root(self):
        # Test
        repo_section = structure.ensure_repo_structure(self.cli)

        # Verify
        self.assertTrue(repo_section is not None)
        self.assertEqual(repo_section.name, structure.SECTION_REPO)
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)

    def test_ensure_repo_structure_idempotency(self):
        # Test
        structure.ensure_repo_structure(self.cli)
        repo_section = structure.ensure_repo_structure(self.cli)

        # Verify
        self.assertTrue(repo_section is not None)
        self.assertEqual(repo_section.name, structure.SECTION_REPO)


class SectionRetrievalTests(base_cli.ExtensionTests):

    def setUp(self):
        super(SectionRetrievalTests, self).setUp()
        structure.ensure_repo_structure(self.cli)
        structure.ensure_consumer_structure(self.cli)

    def test_consumer_section(self):
        section = structure.consumer_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_CONSUMER)

    def test_consumer_install_section(self):
        section = structure.consumer_install_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_INSTALL)

    def test_consumer_update_section(self):
        section = structure.consumer_update_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_UPDATE)

    def test_consumer_uninstall_section(self):
        section = structure.consumer_uninstall_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_UNINSTALL)

    def test_repo_section(self):
        section = structure.repo_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_REPO)

    def test_repo_uploads_section(self):
        section = structure.repo_uploads_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_UPLOADS)

    def test_repo_sync_section(self):
        section = structure.repo_sync_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC)

    def test_repo_sync_schedules_section(self):
        section = structure.repo_sync_schedules_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC_SCHEDULES)

    def test_repo_publish_section(self):
        section = structure.repo_publish_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_PUBLISH)

    def test_repo_publish_schedules_section(self):
        section = structure.repo_publish_schedules_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_PUBLISH_SCHEDULES)
