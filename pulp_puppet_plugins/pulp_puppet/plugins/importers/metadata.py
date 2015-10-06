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


def extract_metadata(filename, temp_dir):
    """
    Pulls the module's metadata file out of the module's tarball and returns it.

    :param filename: full path to the module file
    :type filename: str

    :param temp_dir: location the module's files should be extracted to; must exist prior to this
                     call
    :type temp_dir: str

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """
    metadata = _extract_json(filename, temp_dir)
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


def _extract_json(filename, temp_dir):
    """
    The entire module will be extracted to a temporary location and an attempt will be made to
    find the module file. If it still cannot be found, an exception is raised. The temporary
    location is deleted at the end of this call regardless.

    :param filename: full path to the module file
    :type filename: str

    :param temp_dir: location the module's files should be extracted to; must exist prior to this
                     call
    :type temp_dir: str

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
