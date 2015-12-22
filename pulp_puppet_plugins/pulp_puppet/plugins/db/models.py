from mongoengine import ListField, StringField
from pulp.common.compat import json
from pulp.server.db.model import FileContentUnit

from pulp_puppet.common import constants
from pulp_puppet.plugins.importers import metadata as metadata_parser


class RepositoryMetadata(object):
    """
    An object that stores and produces Puppet Repository metadata

    :ivar modules: the list of modules in the repository
    :type modules: list
    """

    def __init__(self):
        self.modules = []

    def update_from_json(self, metadata_json):
        """
        Updates this metadata instance with modules found in the given JSON
        document. This can be called multiple times to merge multiple
        repository metadata JSON documents into this instance.

        :return: object representing the repository and all of its modules
        :rtype:  RepositoryMetadata
        """

        parsed = json.loads(metadata_json)

        # The contents of the metadata document is a list of dictionaries,
        # each representing a single module.
        for module_dict in parsed:
            module = Module.from_metadata(module_dict)
            self.modules.append(module)

    def to_json(self):
        """
        Return the repository metadata as a JSON representation.

        :return: The repository metadata as json.
        :rtype: str
        """
        repo_metadata_dict = []
        for module in self.modules:
            module_metadata = {'name': module.name, 'author': module.author,
                               'version': module.version, 'tag_list': module.tag_list}
            repo_metadata_dict.append(module_metadata)

        # Serialize metadata of all modules in the repo into a single JSON document
        return json.dumps(repo_metadata_dict)


class Module(FileContentUnit):
    """
    The mongoengine representation of a Puppet Module.

    The fields stored by this model correspond with attributes defined in Puppet Module metadata
    documentation. Refer to the Puppet documentation for more information about these fields.
    """

    name = StringField(required=True)
    version = StringField(required=True)
    author = StringField(required=True)

    # From Repository Metadata
    tag_list = ListField()

    # Generated at the file level
    checksum = StringField()
    checksum_type = StringField(default=constants.DEFAULT_HASHLIB)

    # From Module Metadata
    source = StringField()
    license = StringField()
    summary = StringField()
    description = StringField()
    project_page = StringField()
    types = ListField()
    dependencies = ListField()
    checksums = ListField()

    # For backward compatibility
    _ns = StringField(default='units_puppet_module')
    _content_type_id = StringField(required=True, default=constants.TYPE_PUPPET_MODULE)

    unit_key_fields = ('author', 'name', 'version')

    meta = {
        'allow_inheritance': False,
        'collection': 'units_puppet_module',
        'indexes': [
            {
                'fields': unit_key_fields,
                'unique': True
            },
        ],
    }

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        Checksums is expressed as a dict of files to checksum. This causes a problem in mongo
        since keys can't have periods in them, but file names clearly will. Translate this to a
        list of tuples to get around this before saving.

        :param sender:   sender class
        :type  sender:   object
        :param document: Document that sent the signal
        :type  document: Module
        :param kwargs:   unused
        """
        super(Module, cls).pre_save_signal(sender, document, **kwargs)
        if isinstance(document.checksums, dict):
            document.checksums = [(k, v) for k, v in document.checksums.items()]

    def import_content(self, path, location=None):
        """
        The parent class promises to import a content file into platform storage.
        The (optional) *location* may be used to specify a path within the unit
        storage where the content is to be stored.
        For example:
          import_content('/tmp/file') will store 'file' at: _storage_path
          import_content('/tmp/file', 'a/b/c) will store 'file' at: _storage_path/a/b/c

        In addition to the parent behavior, this overridden method calculates the
        checksum after moving the content to permanent storage if it has not already
        been provided.

        :param path:     The absolute path to the file to be imported.
        :type  path:     str
        :param location: The (optional) location within the unit storage path
                         where the content is to be stored.
        :type  location: str

        :raises PulpCodedException: PLP0036 if the unit has not been saved.
        :raises PulpCodedException: PLP0037 if *path* is not an existing file.
        """
        super(Module, self).import_content(path, location=location)
        if self.checksum is None:
            self.checksum = metadata_parser.calculate_checksum(self._storage_path)
        self.save()

    def __str__(self):
        """ Backwards compatible with __str__ from pulp.plugins.model.AssociatedUnit """
        return 'Unit [key=%s] [type=%s] [id=%s]' % (self.unit_key, self._content_type_id, self.id)

    def __repr__(self):
        """ Backwards compatible with __repr__ from pulp.plugins.model.AssociatedUnit """
        return str(self)

    @staticmethod
    def split_filename(filename):
        """
        Splits a module's filename into two parts 'author' and 'name' and returns them as a dict.

        Split the filename of a module into into two parts and return it as a dict with the keys
        'author' and 'name'. The module filenamename is expected to be in the format 'author-name'
        or 'author/name'.

        :param filename: The module's filename to be split into author and name.
        :type filename: basestring

        :return: A dictionary with 'author' and 'name' containing the author and name respectively.
        :rtype: A dict of strings.
        """
        try:
            author, name = filename.split("-", 1)
        except ValueError:
            # This is the forge format, but Puppet still allows it
            author, name = filename.split("/", 1)
        return {'author': author, 'name': name}

    @classmethod
    def from_metadata(cls, metadata):
        """
        Returns a cls instantiated from a dict of metadata.

        Not all metadata will be stored. Metadata is stripped out to only storable fields using
        the whitelist_fields method.

        :param metadata: A dictionary of Puppet module metadata.
        :type metdata: dict

        :return: Returns an instantiated cls created from whitelisted metdata
        :rtype: cls
        """
        whitelist_fields = cls.whitelist_fields(metadata)
        return cls(**whitelist_fields)

    @classmethod
    def whitelist_fields(cls, metadata):
        """
        Returns a dict containing only keys that can only be stored in the db as fields.

        The Puppet metadata specification contains more keys than Pulp stores. This function takes
        a dict of Puppet metadata and returns a dict with all non-storable keys removed.

        :param metadata: A dictionary of Puppet module metadata.
        :type metadata: dict

        :return: A dictionary containing only keys that can be stored in the database.
        :rtype: dict
        """
        whitelist_metadata = {}
        for k, v in metadata.iteritems():
            if k in cls._fields:
                whitelist_metadata[k] = v
        return whitelist_metadata

    def puppet_standard_filename(self):
        """
        Returns the Puppet standard filename for this module.

        :return: Puppet standard filename for this module
        :rtype:  str
        """
        return constants.MODULE_FILENAME % (self.author, self.name, self.version)

