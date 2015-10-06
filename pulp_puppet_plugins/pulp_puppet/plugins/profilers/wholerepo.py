from gettext import gettext as _
import logging

from pulp.plugins.profiler import Profiler
from pulp.server.config import config as pulp_conf
from pulp.server.controllers.repository import find_repo_content_units
from pulp.server.db.model import Repository

from pulp_puppet.common import constants


_LOGGER = logging.getLogger(__name__)


def entry_point():
    return WholeRepoProfiler, {}


class WholeRepoProfiler(Profiler):

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this profiler. The
        following keys will be present in the returned dictionary:

        * id - Programmatic way to refer to this profiler. Must be unique
               across all profilers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the profiler.
        * types - List of all content type IDs that may be processed using this
                  profiler.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        :return: description of the profiler's capabilities
        :rtype:  dict
        """
        return {
            'id': constants.WHOLE_REPO_PROFILER_ID,
            'display_name': _('Profiler to install entire puppet repo'),
            'types' : [constants.TYPE_PUPPET_MODULE]
        }

    def install_units(self, consumer, units, options, config, conduit):
        """
        Inspect the options, and if constants.WHOLE_REPO_ID has a non-False
        value, replace the list of units with a list of all units in the given
        repository. Omits version numbers, which allows the install tool to
        automatically choose the most recent version of each.

        :param consumer: A consumer.
        :type consumer: pulp.plugins.model.Consumer

        :param units: A list of content units to be installed.
        :type units: list of: { type_id:<str>, unit_key:<dict> }

        :param options: Install options; based on unit type.
        :type options: dict

        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginCallConfiguration

        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.profiler.ProfilerConduit

        :return: The translated units
        :rtype: list of: {'type_id': <str>, unit_key: {'author': <author>, 'name': <name>}
        """
        repo_id = options.get(constants.REPO_ID_OPTION)
        self._inject_forge_settings(options)
        if options.get(constants.WHOLE_REPO_OPTION) and repo_id:
            msg = _('installing whole repo %(repo_id)s on %(consumer_id)s')
            msg_dict = {'repo_id': repo_id, 'consumer_id': consumer.id}
            _LOGGER.debug(msg, msg_dict)

            repo = Repository.objects.get(repo_id=repo_id)
            units = find_repo_content_units(repo, yield_content_unit=True)

            unit_key_dict = {}
            for unit in units:
                fullname = '%s/%s' % (unit.author, unit.name)
                unit_key_dict[fullname] = {
                    'unit_key': {'author': unit.author, 'name': unit.name},
                    'type_id': constants.TYPE_PUPPET_MODULE
                }

            return unit_key_dict.values()

        else:
            return units

    def update_units(self, consumer, units, options, config, conduit):
        """
        Translate the units to be updated.

        :param consumer: A consumer.
        :type consumer: pulp.plugins.model.Consumer

        :param units: A list of content units to be updated.
        :type units: list of: { type_id:<str>, unit_key:<dict> }

        :param options: Update options; based on unit type.
        :type options: dict

        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginCallConfiguration

        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.profiler.ProfilerConduit

        :return: The translated units
        :rtype: list of: { type_id:<str>, unit_key:<dict> }
        """
        self._inject_forge_settings(options)
        return units

    def _inject_forge_settings(self, options):
        """
        Inject the puppet forge settings into the options.
        Add the pulp server host and port information to the options.
        Used by the agent handler.

        :param options: An options dictionary.
        :type options: dict
        """
        options[constants.FORGE_HOST] = pulp_conf.get('server', 'server_name')
