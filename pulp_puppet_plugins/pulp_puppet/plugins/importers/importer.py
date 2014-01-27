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

import logging

from gettext import gettext as _
from urlparse import urlparse

from pulp.plugins.importer import Importer
from pulp.common.config import read_json_config

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import configuration, upload, copier
from pulp_puppet.plugins.importers.directory import SynchronizeWithDirectory
from pulp_puppet.plugins.importers.forge import SynchronizeWithPuppetForge

# The platform currently doesn't support automatic loading of conf files when the plugin
# uses entry points. The current thinking is that the conf files will be named the same as
# the plugin and put in a conf.d type of location. For now, this implementation will assume
# that's the final solution and the plugin will attempt to load the file itself in the
# entry_point method.
CONF_FILENAME = 'server/plugins.conf.d/%s.json' % constants.IMPORTER_TYPE_ID

_LOG = logging.getLogger(__name__)

# -- plugins ------------------------------------------------------------------


def entry_point():
    """
    Entry point that pulp platform uses to load the importer
    :return: importer class and its config
    :rtype:  Importer, {}
    """
    plugin_config = read_json_config(CONF_FILENAME)
    return PuppetModuleImporter, plugin_config


class PuppetModuleImporter(Importer):

    def __init__(self):
        super(PuppetModuleImporter, self).__init__()
        self.sync_method = None
        self.sync_cancelled = False

    @classmethod
    def metadata(cls):
        return {
            'id': constants.IMPORTER_TYPE_ID,
            'display_name': _('Puppet Importer'),
            'types': [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config):
        return configuration.validate(config)

    def sync_repo(self, repo, sync_conduit, config):
        self.sync_cancelled = False

        # Supports two methods of synchronization.
        # 1. Synchronize with a directory containing a pulp manifest and puppet modules.
        # 2. Synchronize with Puppet Forge.
        # When the feed URL references a PULP_MANIFEST, the directory synchronization
        # method is used.  Otherwise, the puppet forge synchronization method is used.

        # synchronize with a directory

        feed_url = config.get(constants.CONFIG_FEED)
        parsed_url = urlparse(feed_url)
        if parsed_url.path.rsplit('/', 1)[-1].endswith(constants.MANIFEST_FILENAME):
            self.sync_method = SynchronizeWithDirectory(sync_conduit, config)
            report = self.sync_method(repo)
            self.sync_method = None
            return report

        # synchronize with puppet forge

        self.sync_method = SynchronizeWithPuppetForge(repo, sync_conduit, config)
        report = self.sync_method()
        self.sync_method = None
        return report

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        return copier.copy_units(import_conduit, units)

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        try:
            report = upload.handle_uploaded_unit(repo, type_id, unit_key, metadata, file_path, conduit)
        except Exception, e:
            _LOG.exception(e)
            report = {'success_flag': False, 'summary': e.message, 'details': {}}
        return report

    def cancel_sync_repo(self, call_request, call_report):
        self.sync_cancelled = True
        sync_method = self.sync_method
        if sync_method is None:
            return
        sync_method.cancel()

    def is_sync_cancelled(self):
        """
        Hook back into this plugin to check if a cancel request has been issued
        for a sync.

        :return: true if the sync should stop running; false otherwise
        :rtype: bool
        """
        return self.sync_cancelled
