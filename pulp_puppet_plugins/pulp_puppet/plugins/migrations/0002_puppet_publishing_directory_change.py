# -*- coding: utf-8 -*-
# Migration script to move published repositories to the new location.
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
import logging
import os
import shutil

_log = logging.getLogger('pulp')

OLD_PUBLISH_ROOT_DIR = '/var/www'
OLD_PUPPET_PUBLISH_DIR_NAME = 'pulp_puppet'
NEW_PUBLISH_ROOT_DIR = '/var/lib/pulp/published'
NEW_PUPPET_PUBLISH_DIR_NAME = 'puppet'


def migrate(*args, **kwargs):
    """
    Move files from old publish directories to the new location.
    """
    old_puppet_publish_dir = os.path.join(OLD_PUBLISH_ROOT_DIR, OLD_PUPPET_PUBLISH_DIR_NAME)
    if os.path.exists(old_puppet_publish_dir) and os.listdir(old_puppet_publish_dir):
        # Copy contents of '/var/www/pulp_puppet' to '/var/lib/pulp/published/puppet'
        move_directory_contents_and_rename(old_puppet_publish_dir,
                                           NEW_PUBLISH_ROOT_DIR,
                                           OLD_PUPPET_PUBLISH_DIR_NAME,
                                           NEW_PUPPET_PUBLISH_DIR_NAME)
        _log.info("Migrated published puppet repositories to the new location")


def move_directory_contents_and_rename(src_dir, dest_dir, old_dir_name, new_dir_name):
    """
    Move directory src_dir to dest_dir and rename it to new_dir_name.
    """
    shutil.move(src_dir, dest_dir)
    new_puppet_publish_dir = os.path.join(dest_dir, new_dir_name)
    if os.path.exists(new_puppet_publish_dir):
        os.rmdir(new_puppet_publish_dir)

    copied_pulp_puppet_directory = os.path.join(dest_dir, old_dir_name)
    os.rename(copied_pulp_puppet_directory, new_puppet_publish_dir)

