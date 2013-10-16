# -*- coding: utf-8 -*-
# Migration script for existing rpm units to include repodata
#
# Copyright © 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
import logging

from pulp.server.managers.content.query import ContentQueryManager

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import metadata

_log = logging.getLogger('pulp')

def migrate(*args, **kwargs):
    """
    for each puppet module, calculate a checksum for the source file on the filesystem
    """
    query_manager = ContentQueryManager()
    collection = query_manager.get_content_unit_collection(type_id=constants.TYPE_PUPPET_MODULE)
    for puppet_unit in collection.find():
        storage_path = puppet_unit['_storage_path']
        checksum = metadata.calculate_checksum(storage_path)
        puppet_unit['checksum'] = checksum
        puppet_unit['checksum_type'] = constants.DEFAULT_HASHLIB
        collection.save(puppet_unit, safe=True)
    _log.info("Migrated puppet modules to include checksum")
