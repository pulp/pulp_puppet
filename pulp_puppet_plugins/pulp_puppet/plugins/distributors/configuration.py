from gettext import gettext as _

from pulp_puppet.common import constants

# This should be added to the PluginCallConfiguration at the outset of each
# call in the distributor where one is specified. This will prevent the need
# for the rest of the codebase to explicitly apply default concepts.
DEFAULT_CONFIG = {
    constants.CONFIG_SERVE_HTTP: constants.DEFAULT_SERVE_HTTP,
    constants.CONFIG_SERVE_HTTPS: constants.DEFAULT_SERVE_HTTPS,
    constants.CONFIG_HTTP_DIR: constants.DEFAULT_HTTP_DIR,
    constants.CONFIG_HTTPS_DIR: constants.DEFAULT_HTTPS_DIR,
    constants.CONFIG_ABSOLUTE_PATH: constants.DEFAULT_ABSOLUTE_PATH,
    constants.CONFIG_FILE_HTTPS_DIR: constants.DEFAULT_FILE_HTTPS_DIR
}


def validate(config):
    """
    Validates the configuration for the puppet module distributor.

    :param config: configuration passed in by Pulp
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :return: the expected return from the plugin's validate_config method
    :rtype:  tuple
    """

    validations = (
        _validate_http,
        _validate_https
    )

    for v in validations:
        result, msg = v(config)
        if not result:
            return result, msg

    return True, None


def _validate_http(config):
    """
    Validates the serve HTTP flag.
    """
    parsed = config.get_boolean(constants.CONFIG_SERVE_HTTP)
    if parsed is None:
        msg_dict = {'k' : constants.CONFIG_SERVE_HTTP}
        return False, _('The value for <%(k)s> must be either "true" or "false"') % msg_dict

    return True, None


def _validate_https(config):
    """
    Validates the serve HTTPS flag.
    """
    parsed = config.get_boolean(constants.CONFIG_SERVE_HTTPS)
    if parsed is None:
        msg_dict = {'k' : constants.CONFIG_SERVE_HTTPS}
        return False, _('The value for <%(k)s> must be either "true" or "false"') % msg_dict

    return True, None

