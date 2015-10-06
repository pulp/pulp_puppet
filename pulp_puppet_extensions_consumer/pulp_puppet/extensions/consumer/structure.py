from gettext import gettext as _

SECTION_ROOT = 'puppet'
DESC_ROOT = _('manage Puppet bindings')


def ensure_puppet_root(cli):
    """
    Verifies that the root of puppet-related commands exists in the CLI,
    creating it using constants from this module if it does not.

    :param cli: CLI instance being configured
    :type  cli: pulp.client.extensions.core.PulpCli
    """
    root_section = cli.find_section(SECTION_ROOT)
    if root_section is None:
        root_section = cli.create_section(SECTION_ROOT, DESC_ROOT)
    return root_section


def root_section(cli):
    return cli.root_section.find_subsection(SECTION_ROOT)