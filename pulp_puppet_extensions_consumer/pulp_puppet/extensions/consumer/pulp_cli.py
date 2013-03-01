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
