from gettext import gettext as _
import logging

from pulp.server.managers.content.query import ContentQueryManager

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import metadata

_log = logging.getLogger('pulp')


def migrate(*args, **kwargs):
    """
    For each puppet module, calculate a checksum for the source file on the filesystem.
    """
    query_manager = ContentQueryManager()
    collection = query_manager.get_content_unit_collection(type_id=constants.TYPE_PUPPET_MODULE)
    for puppet_unit in collection.find():
        storage_path = puppet_unit['_storage_path']
        checksum = metadata.calculate_checksum(storage_path)
        puppet_unit['checksum'] = checksum
        puppet_unit['checksum_type'] = constants.DEFAULT_HASHLIB
        collection.save(puppet_unit)
    _log.info("Migrated puppet modules to include checksum")
