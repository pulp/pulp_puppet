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

from pulp.plugins.util import importer_config

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers.downloaders import factory as downloader_factory


def validate(config):
    """
    Validates the configuration for the puppet module importer.

    :param config: configuration passed in by Pulp
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :return: the expected return from the plugin's validate_config method
    :rtype:  tuple
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
        msg = _(u'Configuration errors:\n')
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
        return False, _('The feed <%(f)s> is invalid') % {'f': feed}

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
        msg = _('The value for <%(q)s> must be specified as a list')
        msg = msg % {'q': constants.CONFIG_QUERIES}
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
        msg = _('The value for <%(r)s> must be either "true" or "false"')
        msg = msg % {'r': constants.CONFIG_REMOVE_MISSING}
        return False, msg

    return True, None
