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
    new_puppet_publish_dir = os.path.join(NEW_PUBLISH_ROOT_DIR, NEW_PUPPET_PUBLISH_DIR_NAME)
    if os.path.exists(old_puppet_publish_dir) and os.listdir(old_puppet_publish_dir):
        # Move contents of '/var/www/pulp_puppet' into '/var/lib/pulp/published/puppet'
        move_directory_contents(old_puppet_publish_dir, new_puppet_publish_dir)
        _log.info("Migrated published puppet repositories to the new location")


def move_directory_contents(src_dir, dest_dir):
    """
    Move everything in src_dir to dest_dir
    """
    # perform the move. /var/lib/pulp/published/puppet already exists so we
    # need to move like this (i.e, we can't use shutil.copytree). This should
    # leave an empty /var/www/pulp_puppet dir.
    for entry in os.listdir(src_dir):
        shutil.move(os.path.join(src_dir, entry), os.path.join(dest_dir, entry))
