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
import logging

from pulp.plugins.importer import Importer
from pulp.common.config import read_json_config

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import configuration, sync, upload, copier

# The platform currently doesn't support automatic loading of conf files when the plugin
# uses entry points. The current thinking is that the conf files will be named the same as
# the plugin and put in a conf.d type of location. For now, this implementation will assume
# that's the final solution and the plugin will attempt to load the file itself in the
# entry_point method.
CONF_FILENAME = 'server/plugins.conf.d/%s.json' % constants.IMPORTER_TYPE_ID

_logger = logging.getLogger(__name__)


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
        self.sync_runner = None
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
        self.sync_runner = sync.PuppetModuleSyncRun(repo, sync_conduit, config)
        report = self.sync_runner.perform_sync()
        self.sync_runner = None
        return report

    def import_units(self, source_repo, dest_repo, import_conduit, config,
                     units=None):
        return copier.copy_units(import_conduit, units)

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit,
                    config):
        try:
            report = upload.handle_uploaded_unit(repo, type_id, unit_key, metadata, file_path,
                                                 conduit)
        except Exception, e:
            _logger.exception(e)
            report = {'success_flag': False, 'summary': e.message, 'details': {}}
        return report

    def cancel_sync_repo(self):
        """
        Cancel a running repository synchronization operation.
        """
        self.sync_cancelled = True
        sync_runner = self.sync_runner
        if sync_runner is None:
            return
        sync_runner.cancel_sync()

    def is_sync_cancelled(self):
        """
        Hook back into this plugin to check if a cancel request has been issued
        for a sync.

        :return: true if the sync should stop running; false otherwise
        :rtype: bool
        """
        return self.sync_cancelled
