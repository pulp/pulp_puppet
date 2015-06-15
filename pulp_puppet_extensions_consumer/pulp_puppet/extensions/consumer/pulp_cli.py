from pulp.client.commands.repo.query import RepoSearchCommand
from pulp.client.extensions.decorator import priority

from pulp_puppet.common import constants
from pulp_puppet.extensions.consumer import bind, structure

SEARCH_NAME = 'repos'


@priority()
def initialize(context):
    """
    :type context: pulp.client.extensions.core.ClientContext
    """

    structure.ensure_puppet_root(context.cli)

    root_section = structure.root_section(context.cli)
    root_section.add_command(bind.BindCommand(context))
    root_section.add_command(bind.UnbindCommand(context))
    root_section.add_command(RepoSearchCommand(context, constants.REPO_NOTE_PUPPET, name=SEARCH_NAME))
