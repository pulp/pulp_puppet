import logging

from gettext import gettext as _

from pulp.plugins.importer import Importer
from pulp.common.config import read_json_config
from pulp.server.exceptions import PulpCodedException

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
        self.sync_method = SynchronizeWithDirectory(repo, sync_conduit, config)
        report = self.sync_method()

        # When fetching the PULP_MANIFEST is not successful, it's assumed that the
        # feed points to a puppet forge instance and the synchronization is retried
        # using puppet forge method.

        if report.metadata_state == constants.STATE_FAILED:
            self.sync_method = SynchronizeWithPuppetForge(repo, sync_conduit, config)
            report = self.sync_method()

        self.sync_method = None
        return report.build_final_report()

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        return copier.copy_units(import_conduit, units)

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        report = upload.handle_uploaded_unit(repo, type_id, unit_key, metadata, file_path,
                                             conduit)
        return report

    def cancel_sync_repo(self):
        """
        Cancel a running repository synchronization operation.
        """
        self.sync_cancelled = True
        if self.sync_method is None:
            return
        self.sync_method.cancel()

    def is_sync_cancelled(self):
        """
        Hook into the plugin to check if a cancel request has been issued for a sync.

        :return: True if the sync should stop running; False otherwise
        :rtype: bool
        """
        return self.sync_cancelled
