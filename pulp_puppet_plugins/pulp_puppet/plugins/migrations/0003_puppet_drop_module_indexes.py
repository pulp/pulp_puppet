import logging

from pulp.server.db.connection import get_collection
from pymongo.errors import OperationFailure


_log = logging.getLogger('pulp')


def migrate(*args, **kwargs):
    """
    Drop old indexes for units_puppet_module so that mongoengine will re-create the new ones.
    """
    units_puppet_module = get_collection('units_puppet_module')

    try:
        units_puppet_module.drop_index('name_1_version_1_author_1')
    except OperationFailure:
        # The index is already dropped
        pass
    try:
        units_puppet_module.drop_index('author_1')
    except OperationFailure:
        # The index is already dropped
        pass
    try:
        units_puppet_module.drop_index('tag_list_1')
    except OperationFailure:
        # The index is already dropped
        pass
