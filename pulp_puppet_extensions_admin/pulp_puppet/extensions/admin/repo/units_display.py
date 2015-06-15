"""
Methods to handle the rendering of a unit list returned from either the copy
or remove units commands.
"""

from gettext import gettext as _
from pulp_puppet.common.constants import TYPE_PUPPET_MODULE

MODULE_ID_TEMPLATE = '%(author)s-%(name)s-%(version)s'


def get_formatter_for_type(type_id):
    """
    Return a method that takes one argument (a unit) and formats a short string
    to be used as the output for the unit_remove command

    :param type_id: The type of the unit for which a formatter is needed
    :type type_id: str
    """

    if type_id != TYPE_PUPPET_MODULE:
        raise ValueError(_("The puppet module formatter can not process %s units.") % type_id)

    return lambda x: MODULE_ID_TEMPLATE % x
