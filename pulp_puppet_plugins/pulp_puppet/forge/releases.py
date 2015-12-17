# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import gdbm
import json
import logging
import os.path

from django.http import HttpResponseNotFound, HttpResponse
from pulp.server.db import model
from pulp.server.managers.consumer.bind import BindManager

from pulp_puppet.common import constants
from pulp_puppet.forge.unit import Unit

_LOGGER = logging.getLogger(__name__)


def unit_generator(dbs, module_name, hostname):
    """
    Generator to produce all units visible to the API caller

    :param dbs: The list of repo gdm files available to query for data
    :type dbs: dict
    :param module_name: The module name to search for
    :type module_name: str
    :param hostname: The hostname of server serving modules
    :type hostname: str
    """
    for repo_id, data in dbs.iteritems():
        protocol = data['protocol']
        db = data['db']
        try:
            json_data = db[module_name]
        except KeyError:
            _LOGGER.debug('module %s not found in repo %s' % (module_name, repo_id))
            continue
        units = json.loads(json_data)
        for unit in units:
            yield Unit(name=module_name, db=db, repo_id=repo_id, host=hostname, protocol=protocol,
                       **unit)


def view(consumer_id, repo_id, module_name, version=None, recurse_deps=True,
         view_all_matching=False, hostname=None):
    """
    produces data for the "releases.json" view

    :param consumer_id: unique ID for a consumer
    :type  consumer_id: str
    :param repo_id:     unique ID for a repo
    :type  repo_id:     str
    :param module_name: name of a module in form "author/title"
    :type  module_name: str
    :param version:     optional version
    :type  version:     str
    :param recurse_deps: Whether or not a module should have it's full dependency chain
                         recursively added to it's own
    :type recurse_deps: bool
    :param view_all_matching: whether or not all matching modules should be returned or just
                              just the first one
    :type view_all_matching: bool

    :return:    data structure defining dependency data for the given module and
                its download path, identical to what the puppet forge v1 API
                generates, except this structure is not yet JSON serialized
    :rtype:     dict
    """
    # Build the list of repositories that should be queried
    if repo_id == constants.FORGE_NULL_AUTH_VALUE:
        if consumer_id == constants.FORGE_NULL_AUTH_VALUE:
            # must provide either consumer ID or repo ID
            return HttpResponse('Unauthorized', status=401)
        repo_ids = get_bound_repos(consumer_id)
    else:
        repo_ids = [repo_id]

    dbs = None
    return_data = None
    try:
        # Get the list of database files to query
        dbs = get_repo_data(repo_ids)

        # Build list of units to return
        ret = []
        # If a version was specified filter by that specific version of the module
        if version:
            for unit in unit_generator(dbs, module_name, hostname):
                if unit.version == version:
                    ret.append(unit)
                    break
        else:
            units = list(unit_generator(dbs, module_name, hostname))
            # if view_all_matching then return all modules matching the query, otherwise
            # only return the first matching module (for forge v1 & v2 api compliance)
            if view_all_matching:
                ret = units
            else:
                if units:
                    ret.append(max(units))

        # calculate dependencies for the units being returned & build the return structure
        return_data = {}
        for unit in ret:
            populated_unit = unit.build_dep_metadata(recurse_deps)
            for unit_name, unit_details in populated_unit.iteritems():
                return_data.setdefault(unit_name, []).extend(unit_details)

        if not return_data:
            return HttpResponseNotFound()

    finally:
        # Close all the database files. If closing one raises an error we still need to
        # close the others so that file handles aren't left open.
        if dbs:
            error_raised = None
            for repo_id, dbs_data in dbs.iteritems():
                try:
                    dbs_data['db'].close()
                except Exception, e:
                    error_raised = e

            if error_raised:
                raise error_raised

    return return_data


# this just provides a convenient way to access each config key and value from
# the following function
PROTOCOL_CONFIG_KEYS = {
    'http': (constants.CONFIG_HTTP_DIR, constants.DEFAULT_HTTP_DIR),
    'https': (constants.CONFIG_HTTPS_DIR, constants.DEFAULT_HTTPS_DIR),
}


def get_repo_data(repo_ids):
    """
    Find, open, and return the gdbm database file associated with each repo
    plus that repo's publish protocol

    :param repo_ids: list of repository IDs.
    :type  repo_ids: list

    :return:    dictionary where keys are repo IDs, and values are dicts that
                contain an open gdbm database under key "db", and a protocol
                under key "protocol".
    :rtype:     dict
    """
    ret = {}
    for distributor in model.Distributor.objects(repo_id__in=repo_ids):
        publish_protocol = _get_protocol_from_distributor(distributor)
        protocol_key, protocol_default_value = PROTOCOL_CONFIG_KEYS[publish_protocol]
        repo_path = distributor['config'].get(protocol_key, protocol_default_value)
        repo_id = distributor['repo_id']
        db_path = os.path.join(repo_path, repo_id, constants.REPO_DEPDATA_FILENAME)
        try:
            ret[repo_id] = {'db': gdbm.open(db_path, 'r'), 'protocol': publish_protocol}
        except gdbm.error:
            _LOGGER.error('failed to find dependency database for repo %s. re-publish to fix.' %
                          repo_id)
    return ret


def _get_protocol_from_distributor(distributor):
    """
    Look at a distributor's config and determine what protocol it gets published
    for. Gives preference to https in case a distributor is configured for both.

    :param distributor: distributor as returned by
                        pulp.server.managers.RepoDistributorManager, should be
                        a dict with key 'config'
    :type  distributor: dict
    :return:
    """
    config = distributor['config']
    # look for an explicit setting for this distributor
    if config.get(constants.CONFIG_SERVE_HTTPS):
        return 'https'
    elif config.get(constants.CONFIG_SERVE_HTTP):
        return 'http'
    # look for the default
    elif constants.DEFAULT_SERVE_HTTPS:
        return 'https'
    elif constants.DEFAULT_SERVE_HTTP:
        return 'http'


def get_bound_repos(consumer_id):
    """
    :param consumer_id: unique ID of a consumer
    :type  consumer_id: str

    :return:    list of repo IDs
    :rtype:     list
    """
    bindings = BindManager().find_by_consumer(consumer_id)
    repos = [binding['repo_id']
             for binding in bindings
             if binding['distributor_id'] == constants.DISTRIBUTOR_TYPE_ID]
    return repos
