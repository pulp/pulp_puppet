from gettext import gettext as _
import json
import logging

import semantic_version

_LOGGER = logging.getLogger(__name__)


class Unit(object):
    """
    Represents a unit for purposes of generating dependency data equivalent to
    the Puppet Forge API's output.

    Note that the requested module will only have one version present in the
    output, even if multiple versions exist. I don't know why, but this is how
    the original API behaves.

    Also, when an included module has dependencies, all available versions of
    that module will be included; even versions that do not meet the dependency's
    version requirement. Again, I don't know why, but this is how the original
    API behaves.

    Unlike the examples below which are taken from Puppet Forge, we return full
    URLs to each file so that the basic auth credentials get stripped off.

    A basic example with no dependencies will look like this:

    http://forge.puppetlabs.com/api/v1/releases.json?module=puppetlabs/stdlib

    {
      "puppetlabs/stdlib": [
        {
          "dependencies": [],
          "version": "3.2.0",
          "file": "/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz"
        }
      ]
    }

    An example with dependencies will look like this (many versions of stdlib
    were removed for brevity):

    http://forge.puppetlabs.com/api/v1/releases.json?module=branan/minecraft

    {
      "branan/minecraft": [
        {
          "dependencies": [
            [
              "branan/s3file",
              ">= 1.0.0"
            ],
            [
              "puppetlabs/java",
              ">= 0.1.6"
            ],
            [
              "puppetlabs/stdlib",
              ">= 2.2.0"
            ]
          ],
          "version": "1.0.0",
          "file": "/system/releases/b/branan/branan-minecraft-1.0.0.tar.gz"
        }
      ],
      "puppetlabs/stdlib": [
        {
          "dependencies": [],
          "version": "3.1.0",
          "file": "/system/releases/p/puppetlabs/puppetlabs-stdlib-3.1.0.tar.gz"
        },
        {
          "dependencies": [],
          "version": "3.1.1",
          "file": "/system/releases/p/puppetlabs/puppetlabs-stdlib-3.1.1.tar.gz"
        },
        {
          "dependencies": [],
          "version": "3.2.0",
          "file": "/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz"
        }
      ],
      "branan/s3file": [
        {
          "dependencies": [],
          "version": "1.0.0",
          "file": "/system/releases/b/branan/branan-s3file-1.0.0.tar.gz"
        }
      ],
      "puppetlabs/java": [
        {
          "dependencies": [
            [
              "puppetlabs/stdlib",
              ">= 0.1.6"
            ]
          ],
          "version": "0.1.6",
          "file": "/system/releases/p/puppetlabs/puppetlabs-java-0.1.6.tar.gz"
        },
        {
          "dependencies": [
            [
              "puppetlabs/stdlib",
              ">= 0.1.6"
            ]
          ],
          "version": "0.2.0",
          "file": "/system/releases/p/puppetlabs/puppetlabs-java-0.2.0.tar.gz"
        }
      ]
    }
    """

    def __init__(self, name, version, file, dependencies, db, repo_id, host, protocol,
                 file_md5=None):
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
        :param file_md5:    the md5 checksum for the file
        :type  file_md5:    str
        """
        self.name = name
        self.version = version
        self.file = file
        self.dependencies = dependencies
        self.db = db
        self.repo_id = repo_id
        self.host = host
        self.protocol = protocol
        self.file_md5 = file_md5

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
            msg = _('module %(name)s not found in repo %(repo_id)s')
            msg_dict = {'name': name, 'repo_id': repo_id}
            _LOGGER.debug(msg, msg_dict)
            return []
        units = json.loads(json_data)
        return [
            cls(name=name, db=db, repo_id=repo_id, host=host, protocol=protocol, **unit)
            for unit in units
        ]

    def build_dep_metadata(self, recurse_deps=True):
        """
        Builds and returns the dependency metadata for this unit

        :param recurse_deps: Whether or not a module should have it's full dependency chain
                         recursively added to it's own
        :type recurse_deps: bool

        :return:    data structure defining dependency data for the given module and
                    its download path, identical to what the puppet forge v1 API
                    generates, except this structure is not yet JSON serialized
        :rtype:     dict
        """
        root = {self.name: [self.to_dict()]}
        for dep in self.dependencies:
            self._add_dep_to_metadata(dep['name'], root, recurse_deps=recurse_deps)
        return root

    def _add_dep_to_metadata(self, name, root, recurse_deps=True):
        """
        Given a dependency metadata structure, add a new dependency to it. This
        will recursively add dependencies of the current dependency being added.

        :param name:    name of the module in the form "author/title"
        :type  name:    str
        :param root:    existing dependency data structure
        :type  root:    dict
        :param recurse_deps: Whether or not a module should have it's full dependency chain
                             recursively added to it's own, Forge v1 & v2 requires the recursive
                             deps list while v3 does not.
        :type recurse_deps: bool

        :return:    None
        """
        if name not in root:
            units = self.units_from_json(name, self.db, self.repo_id, self.host, self.protocol)
            root[name] = [unit.to_dict() for unit in units]
            for unit in units:
                for dep in unit.dependencies:
                    if recurse_deps:
                        self._add_dep_to_metadata(dep['name'], root)

    @property
    def _deps_as_list(self):
        """
        transforms the name and version that define a dependency into the format
        expected to be served by this API.

        :return:    list of 2-member lists, each containing name and version
                    expression
        :rtype:     list
        """
        return [[dep['name'], dep.get('version_requirement', '>= 0.0.0')]
                for dep in self.dependencies]

    def to_dict(self):
        """
        returns the dictionary that will define a particular version of a named
        unit within the dependency structure

        :rtype: dict
        """
        return {
            'file': self.file,
            'version': self.version,
            'dependencies': self._deps_as_list,
            'file_md5': self.file_md5
        }

    def __cmp__(self, other):
        """
        Converts versions before doing the comparison. They are strings such as
        "1.0.0", which we convert to a tuple of ints such as (1, 0, 0).

        :param other:   other Unit instance
        :type  other:   pulp_puppet.forge.unit.Unit

        :return:        whatever "cmp" returns
        """
        my_semver = semantic_version.Version(self.version)
        other_semver = semantic_version.Version(other.version)
        return cmp(my_semver, other_semver)
