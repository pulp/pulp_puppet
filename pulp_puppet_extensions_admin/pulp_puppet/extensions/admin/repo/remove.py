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
from pulp_puppet.extensions.admin.repo import units_display


DESC_REMOVE = _('remove copied or uploaded modules from a repository')


class RemoveCommand(UnitRemoveCommand):
    """
    Class for executing unit remove commands for puppet_module units
    """

    def __init__(self, context, name='remove', description=DESC_REMOVE,
                 module_count_threshold=constants.DISPLAY_MODULES_THRESHOLD):
        UnitRemoveCommand.__init__(self, context, name=name, description=description,
                                   type_id=constants.TYPE_PUPPET_MODULE)

        self.max_units_displayed = module_count_threshold

    @staticmethod
    def get_formatter_for_type(type_id):
        """
        Returns a method that can be used to format the unit key of a puppet_module
        for display purposes

        :param type_id: the type_id of the unit key to get a formatter for
        :type type_id: str
        :return: function
        """
        return units_display.get_formatter_for_type(type_id)
