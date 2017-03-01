import copy
from gettext import gettext as _
import os
import re

from pulp.client.commands.repo import upload as upload_commands

from pulp_puppet.common import constants


DESC_FILE = _('path to a file to upload; may be specified multiple times '
              'for multiple files. File name format must be '
              'author-name-version.tar.gz')


class UploadModuleCommand(upload_commands.UploadCommand):

    def __init__(self, context, upload_manager):
        super(UploadModuleCommand, self).__init__(context, upload_manager)

        # add a customized file option that replaces the original
        option_file = copy.copy(upload_commands.OPTION_FILE)
        option_file.validate_func = self.validate_file_name
        option_file.description = DESC_FILE
        self.options.remove(upload_commands.OPTION_FILE)
        self.add_option(option_file)

    def generate_unit_key(self, filename, **kwargs):
        # Need to return empty string and not None because CLI expects a string
        return ""

    def determine_type_id(self, filename, **kwargs):
        return constants.TYPE_PUPPET_MODULE

    def matching_files_in_dir(self, dir):
        all_files_in_dir = super(UploadModuleCommand, self).matching_files_in_dir(dir)
        modules = [f for f in all_files_in_dir if f.endswith('.tar.gz')]
        return modules

    @staticmethod
    def validate_file_name(name_list):
        """
        Validator for use with okaara's CLI argument validation framework.

        :param name_list: list of filenames
        :type  name_list: type
        """
        for name in name_list:
            if re.match('^.+?-.+?-.+?\.tar\.gz$', os.path.basename(name)) is None:
                raise ValueError(_('Filename must have the format author-name-version.tar.gz'))
