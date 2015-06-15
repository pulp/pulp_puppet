from gettext import gettext as _
import os

from pulp.plugins.file.model_distributor import FileDistributor

from pulp_puppet.common import constants
from pulp_puppet.plugins.distributors import configuration


def entry_point():
    """
    Advertise the Puppet File distributor to Pulp.

    :return: Puppet File and its empty config
    :rtype:  tuple
    """
    return PuppetFileDistributor, {}


class PuppetFileDistributor(FileDistributor):
    """
    Distribute Puppet Module File
    """

    @classmethod
    def metadata(cls):
        """
        Advertise the capabilities of the PuppetFileDistributor.

        :return: The description of PuppetFileDistributor's capabilities.
        :rtype: dict
        """
        return {
            'id': constants.DISTRIBUTOR_FILE_TYPE_ID,
            'display_name': 'Puppet File Distributor',
            'types': [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, config_conduit):
        """
        Validate the configuration information for the puppet file distributor.

        Ensures that the https directory where the files are going to be served from is valid.

        :param repo: metadata describing the repository to which the configuration applies
        :type repo: pulp.plugins.model.Repository
        :param config: plugin configuration instance; contains the proposed repo configuration
        :type config: pulp.plugins.config.PluginCallConfiguration
        :param config_conduit: Configuration Conduit
        :type config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

        :return: A tuple of validation results
        :rtype: tuple of length two. Either (False, str) or (True, None)
        """
        config.default_config = configuration.DEFAULT_CONFIG
        https_dir = config.get(constants.CONFIG_FILE_HTTPS_DIR)
        if https_dir is not None and os.path.isdir(https_dir):
            return True, None
        return False, \
            _("The directory specified for the puppet file distributor is invalid: %(https_dir)s" %
              {'https_dir': https_dir})

    def publish_metadata_for_unit(self, unit):
        """
        Publish the metadata for a single unit.

        This should be writing to open file handles from the initialize_metadata call

        :param unit: the unit for which metadata needs to be written
        :type unit: pulp_puppet.plugins.db.models.Module
        """
        self.metadata_csv_writer.writerow([os.path.basename(unit.storage_path),
                                           unit.checksum,
                                           unit.checksum_type])

    def get_hosting_locations(self, repo, config):
        """
        Get the paths on the filesystem where the build directory should be copied.

        :param repo: The repository that is going to be hosted
        :type repo: pulp.plugins.model.Repository
        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginConfiguration
        """
        config.default_config = configuration.DEFAULT_CONFIG
        hosting_dir = os.path.join(config.get(constants.CONFIG_FILE_HTTPS_DIR), repo.repo_id)
        return [hosting_dir]

    def get_paths_for_unit(self, unit):
        """
        Get the paths within a target directory where this unit should be linked to.

        :param unit: The unit for which we want to return target paths
        :type unit: pulp_puppet.plugins.db.models.Module

        :return: a list of paths the unit should be linked to
        :rtype: list of str
        """
        return [os.path.basename(unit.storage_path), ]
