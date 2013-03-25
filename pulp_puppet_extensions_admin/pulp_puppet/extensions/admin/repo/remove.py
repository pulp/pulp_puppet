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

from gettext import gettext as _

from pulp.client.commands.unit import UnitRemoveCommand
from pulp_puppet.common import constants


DESC_REMOVE = _('remove copied or uploaded modules from a repository')


class RemoveCommand(UnitRemoveCommand):

    def __init__(self, context, name='remove', description=DESC_REMOVE):
        super(RemoveCommand, self).__init__(
            context,
            name=name,
            description=description,
            type_id=constants.TYPE_PUPPET_MODULE,
        )
