from gettext import gettext as _

from pulp.plugins.util import importer_config

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.downloaders import factory as downloader_factory


def validate(config):
    """
    Validates the configuration for the puppet module importer.

    :param config: configuration passed in by Pulp
    :type config: pulp.plugins.config.PluginCallConfiguration

    :return: the expected return from the plugin's validate_config method
    :rtype: tuple
    """
    validations = (
        _validate_feed,
        _validate_remove_missing,
        _validate_queries,
    )

    for v in validations:
        result, msg = v(config)
        if not result:
            return result, msg

    try:
        # This will raise an InvalidConfig if there are problems
        importer_config.validate_config(config)
        return True, None
    except importer_config.InvalidConfig, e:
        # Because the validate() API is silly, we must concatenate all the failure messages into
        # one.
        msg = _(u'Configuration errors:') + '\n'
        msg += '\n'.join(e.failure_messages)
        # Remove the last newline
        msg = msg.rstrip()
        return False, msg


def _validate_feed(config):
    """
    Validates the location of the puppet modules.
    """
    # The feed is optional
    if constants.CONFIG_FEED not in config.keys():
        return True, None

    # Ask the downloader factory to validate the feed has a supported downloader
    feed = config.get(constants.CONFIG_FEED)
    is_valid = downloader_factory.is_valid_feed(feed)
    if not is_valid:
        return False, _('The feed <%(feed_name)s> is invalid') % {'feed_name': feed}

    return True, None


def _validate_queries(config):
    """
    Validates the query parameters to apply to the source feed.
    """
    # The queries are optional
    if constants.CONFIG_QUERIES not in config.keys():
        return True, None

    queries = config.get(constants.CONFIG_QUERIES)
    if not isinstance(queries, (list, tuple)):
        error_dict = {'query': constants.CONFIG_QUERIES}
        msg = _('The value for <%(query)s> must be specified as a list') % error_dict
        return False, msg

    return True, None


def _validate_remove_missing(config):
    """
    Validates the remove missing modules value if it is specified.
    """
    # The flag is optional
    if constants.CONFIG_REMOVE_MISSING not in config.keys():
        return True, None

    # Make sure it's a boolean
    parsed = config.get_boolean(constants.CONFIG_REMOVE_MISSING)
    if parsed is None:
        error_dict = {'remove_missing': constants.CONFIG_REMOVE_MISSING}
        msg = _('The value for <%(remove_missing)s> must be either "true" or "false"') % error_dict
        return False, msg

    return True, None
