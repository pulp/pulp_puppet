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

import json
import logging
import urlparse

_LOGGER = logging.getLogger(__name__)

class Unit(object):
    """
    Represents a unit for purposes of generating dependency data equivalent to
    the puppet forge API's output.
    """

    def __init__(self, name, version, file, dependencies, db, repo_id, host, protocol):
        """

        :param name:        name in form "author/title"
        :type  name:        str
        :param version:     version of the module
        :type  version:     str
        :param file:        absolute path component of URL to the file
        :type  file:        str
        :param dependencies:list of dependencies as dicts with keys "name" and
                            "version_requirement"
        :type  dependencies:list
        :param db:          open instance of a gdbm database
        :type  db:          gdbm.gdbm
        :param repo_id:     ID of the repository in which this unit lives and in
                            which dependencies should be searched for
        :type  repo_id:     str
        :param host:        host name, optionally ending with a ":" and port
                            number, to which the current web request was made
        :type  host:        str
        :param protocol:    protocol used for this web request, such as "http"
        :type  protocol:    str
        """
        self.name = name
        self.version = version
        self.file = file
        self.dependencies = dependencies
        self.db = db
        self.repo_id = repo_id
        self.host = host
        self.protocol = protocol

    @classmethod
    def units_from_json(cls, name, db, repo_id, host, protocol):
        """
        Given JSON loaded from the dependency database, return a list of
        Unit instances

        :param name:        name in form "author/title"
        :type  name:        str
        :param db:          open instance of a gdbm database
        :type  db:          gdbm.gdbm
        :param repo_id:     ID of the repository in which this unit lives and in
                            which dependencies should be searched for
        :type  repo_id:     str
        :param host:        host name, optionally ending with a ":" and port
                            number, to which the current web request was made
        :type  host:        str
        :param protocol:    protocol used for this web request, such as "http"
        :type  protocol:    str

        :return:    list of Unit instances
        :rtype:     list
        """
        try:
            json_data = db[name]
        except KeyError:
            _LOGGER.debug('module %s not found in repo %s' % (name, repo_id))
            return []
        units = json.loads(json_data)
        return [
            cls(name=name, db=db, repo_id=repo_id, host=host, protocol=protocol, **unit)
            for unit in units
        ]

    def build_dep_metadata(self):
        """
        Builds and returns the dependency metadata for this unit

        :return:    data structure defining dependency data for the given module and
                    its download path, identical to what the puppet forge v1 API
                    generates, except this structure is not yet JSON serialized
        :rtype:     dict
        """
        root = {self.name: [self.to_dict()]}
        for dep in self.dependencies:
            self.add_dep_to_metadata(dep['name'], root)
        return root

    def add_dep_to_metadata(self, name, root):
        """
        Given a dependency metadata structure, add a new dependency to it. This
        will recursively add dependencies of the current dependency being added.

        :param name:    name of the module in the form "author/title"
        :type  name:    str
        :param root:    existing dependency data structure
        :type  root:    dict

        :return:    None
        """
        if name not in root:
            units = self.units_from_json(name, self.db, self.repo_id, self.host, self.protocol)
            root[name] = [unit.to_dict() for unit in units]
            for unit in units:
                for dep in unit.dependencies:
                    self.add_dep_to_metadata(dep['name'], root)

    @property
    def _deps_as_list(self):
        """
        transforms the name and version that define a dependency into the format
        expected to be served by this API.

        :return:    list of 2-member lists, each containing name and version
                    expression
        :rtype:     list
        """
        return [[dep['name'], dep['version_requirement']] for dep in self.dependencies]

    def to_dict(self):
        """
        returns the dictionary that will define a particular version of a named
        unit within the dependency structure

        :rtype: dict
        """
        return {
            'file' : urlparse.urljoin(
                '%s://%s/' % (self.protocol, self.host),
                self.file,
            ),
            'version' : self.version,
            'dependencies' : self._deps_as_list,
        }

    def __cmp__(self, other):
        """
        Converts versions before doing the comparison. They are strings such as
        "1.0.0", which we convert to a tuple of ints such as (1, 0, 0).

        :param other:   other Unit instance
        :type  other:   pulp_puppet.forge.unit.Unit

        :return:        whatever "cmp" returns
        """
        my_version = map(int, self.version.split('.'))
        other_version = map(int, other.version.split('.'))
        return cmp(my_version, other_version)
