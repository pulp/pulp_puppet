from gettext import gettext as _

from pulp.plugins.distributor import Distributor
from pulp.server.db.model import Repository

from pulp_puppet.common import constants
from pulp_puppet.plugins.distributors import configuration, publish


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor
    :return: distributor class and its config
    :rtype:  Distributor, {}
    """
    return PuppetModuleDistributor, configuration.DEFAULT_CONFIG


class PuppetModuleDistributor(Distributor):
    def __init__(self):
        super(PuppetModuleDistributor, self).__init__()
        self.publish_cancelled = False

    @classmethod
    def metadata(cls):
        return {
            'id': constants.DISTRIBUTOR_TYPE_ID,
            'display_name': _('Puppet Distributor'),
            'types': [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, config_conduit):
        config.default_config = configuration.DEFAULT_CONFIG
        return configuration.validate(config)

    def distributor_removed(self, repo, config):
        config.default_config = configuration.DEFAULT_CONFIG
        publish.unpublish_repo(repo, config)

    def publish_repo(self, repo_transfer, publish_conduit, config):
        repo = Repository.objects.get_repo_or_missing_resource(repo_transfer.id)
        self.publish_cancelled = False
        config.default_config = configuration.DEFAULT_CONFIG
        publish_runner = publish.PuppetModulePublishRun(repo, repo_transfer, publish_conduit,
                                                        config, self.is_publish_cancelled)
        report = publish_runner.perform_publish()
        return report

    def cancel_publish_repo(self):
        """
        Cancel a running repository publish operation.
        """
        self.publish_cancelled = True

    def is_publish_cancelled(self):
        """
        Hook into this plugin to check if a cancel request has been issued for a publish operation.

        :return: true if the sync should stop running; false otherwise
        :rtype: bool
        """
        return self.publish_cancelled
