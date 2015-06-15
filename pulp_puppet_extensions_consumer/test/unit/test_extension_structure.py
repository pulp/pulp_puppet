import consumer_base_cli
from pulp_puppet.extensions.consumer import bind, pulp_cli, structure


class TestStructure(consumer_base_cli.ConsumerExtensionTests):
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


class TestInit(consumer_base_cli.ConsumerExtensionTests):
    def test_init(self):
        pulp_cli.initialize(self.context)

        root = self.context.cli.find_subsection(structure.SECTION_ROOT)
        self.assertTrue(bind.BindCommand(self.context).name in root.commands)
        self.assertTrue(bind.UnbindCommand(self.context).name in root.commands)
        self.assertTrue(pulp_cli.SEARCH_NAME in root.commands)
