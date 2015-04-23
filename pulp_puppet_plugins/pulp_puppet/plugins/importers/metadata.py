"""
Functionality around parsing the metadata within a packaged module (.tar.gz).
"""

import hashlib
import os
import shutil
import sys
import tarfile
import tempfile

from pulp.common.compat import json
from pulp.server.exceptions import InvalidValue

from pulp_puppet.common import constants


class ExtractionException(InvalidValue):
    """
    Root exception of all exceptions that can occur while extracting a module's
    metadata.
    """
    def __init__(self, module_filename):
        InvalidValue.__init__(self, module_filename)
        self.module_filename = module_filename


class MissingModuleFile(ExtractionException):
    """
    Raised if the metadata file cannot be extracted from a module.
    """
    pass


class InvalidTarball(ExtractionException):
    """
    Raised if the tarball cannot be opened.
    """
    pass


CHECKSUM_READ_BUFFER_SIZE = 65536


def extract_metadata(filename, temp_dir, module=None):
    """
    Pulls the module's metadata file out of the module's tarball and updates the
    module instance with its contents. The module instance itself is updated
    as part of this call. It is up to the caller to delete the temp_dir after
    this executes.

    :param filename: full path to the module file
    :type  filename: str

    :param temp_dir: location the module's files should be extracted to;
           must exist prior to this call
    :type  temp_dir: str

    :param module: module instance with name, author, version to help find
           the directory which contains metadata.json (optional)
    :type  module: Module

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """
    if module is None:
        metadata = _extract_non_standard_json(filename, temp_dir)
        return json.loads(metadata)

    # Attempt to load from the standard metadata file location. If it's not
    # found, try the brute force approach. If it's still not found, that call
    # will raise the appropriate MissingModuleFile exception.
    try:
        metadata = _extract_json(module, filename, temp_dir)
        return json.loads(metadata)
    except MissingModuleFile:
        metadata = _extract_non_standard_json(filename, temp_dir)
        return json.loads(metadata)


def calculate_checksum(filename):
    """
    Calculate the checksum for a given file using the default hashlib

    :param filename: the filename including path of the file to calculate a checksum for
    :type filename: str
    :return: The checksum for the file
    :rtype: str
    """
    m = hashlib.new(constants.DEFAULT_HASHLIB)
    with open(filename, 'r') as f:
        while 1:
            file_buffer = f.read(CHECKSUM_READ_BUFFER_SIZE)
            if not file_buffer:
                break
            m.update(file_buffer)
    return m.hexdigest()


def _extract_json(module, filename, temp_dir):
    """
    Extracts the module's metadata file from the tarball. This call will attempt
    to only extract and read the metadata file itself, cleaning up the
    extracted file at the end.

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """

    # Extract the module's metadata file itself
    metadata_file_path = '%s-%s-%s/%s' % (module.author, module.name,
                                          module.version,
                                          constants.MODULE_METADATA_FILENAME)

    try:
        tgz = tarfile.open(name=filename)
    except Exception:
        raise InvalidTarball(filename), None, sys.exc_info()[2]

    try:
        tgz.extract(metadata_file_path, path=temp_dir)
        tgz.close()
    except Exception:
        tgz.close()
        raise MissingModuleFile(filename), None, sys.exc_info()[2]

    # Read in the contents
    temp_filename = os.path.join(temp_dir, metadata_file_path)
    contents = _read_contents(temp_filename)
    return contents


def _extract_non_standard_json(filename, temp_dir):
    """
    Called if the module's metadata file isn't found in the standard location.
    The entire module will be extracted to a temporary location and an attempt
    will be made to find the module file. If it still cannot be found, an
    exception is raised. The temporary location is deleted at the end of this
    call regardless.

    :param filename: full path to the module file
    :type  filename: str

    :param temp_dir: location the module's files should be extracted to;
           must exist prior to this call
    :type  temp_dir: str

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """

    extraction_dir = tempfile.mkdtemp(dir=temp_dir)

    # Extract the entire module
    try:
        tgz = tarfile.open(name=filename)
        tgz.extractall(path=extraction_dir)
        tgz.close()
    except Exception:
        raise InvalidTarball(filename), None, sys.exc_info()[2]

    try:
        # Attempt to find the metadata in the Puppet module's main directory
        # It is expected the .tar.gz file will contain exactly one Puppet module
        try:
            module_dir = os.listdir(extraction_dir)[0]
        except IndexError:
            raise MissingModuleFile(filename)
        metadata_filename = constants.MODULE_METADATA_FILENAME
        metadata_full_path = os.path.join(extraction_dir, module_dir, metadata_filename)
        if not os.path.isfile(metadata_full_path):
            raise MissingModuleFile(filename)

        return _read_contents(metadata_full_path)
    finally:
        # Delete the entire extraction directory
        shutil.rmtree(extraction_dir)


def _read_contents(filename):
    """
    Simple utility to read in the contents of the given file, making sure to
    properly handle the file object.

    :return: contents of the given file
    """
    try:
        f = open(filename)
        contents = f.read()
        f.close()

        return contents
    finally:
        # Clean up the temporary file
        os.remove(filename)
