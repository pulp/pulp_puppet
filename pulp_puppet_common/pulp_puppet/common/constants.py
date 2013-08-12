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

"""
Contains constants that are global across the entire puppet plugin. Eventually,
this will be pulled into a common dependency across all of the puppet
support plugins (importers, distributors, extensions).
"""

# -- ids ----------------------------------------------------------------------

# ID used to refer to the puppet importer
IMPORTER_TYPE_ID = 'puppet_importer'

# ID used to refer to the puppet importer instance on a repository
IMPORTER_ID = IMPORTER_TYPE_ID

# ID used to refer to the puppet distributor
DISTRIBUTOR_TYPE_ID = 'puppet_distributor'

# ID used to refer to the puppet distributor instance on a repository
DISTRIBUTOR_ID = 'puppet_distributor'

# ID used to refer to the puppet distributor
INSTALL_DISTRIBUTOR_TYPE_ID = 'puppet_install_distributor'

# ID used to refer to the puppet distributor instance on a repository
INSTALL_DISTRIBUTOR_ID = 'puppet_install_distributor'

# ID used to refer to the whole repo profiler
WHOLE_REPO_PROFILER_ID = 'puppet_whole_repo_profiler'

# ID of the puppet module type definition (must match what's in puppet.json)
TYPE_PUPPET_MODULE = 'puppet_module'

# Used as a note on a repository to indicate it is a Puppet repository
REPO_NOTE_KEY = '_repo-type' # needs to be standard across extensions
REPO_NOTE_PUPPET = 'puppet-repo'

# -- storage and hosting ------------------------------------------------------

# Name of the hosted file describing the contents of the repository
REPO_METADATA_FILENAME = 'modules.json'

# Name of the file that holds dependency data, which is required by the WSGI
# app that implements puppet forge's API
REPO_DEPDATA_FILENAME = '.dependency_db'

# File name inside of a module where its metadata is found
MODULE_METADATA_FILENAME = 'metadata.json'

# Location in the repository where a module will be hosted
# Substitutions: author first character, author
HOSTED_MODULE_FILE_RELATIVE_PATH = 'system/releases/%s/%s/'

# Name template for a module
# Substitutions: author, name, version
MODULE_FILENAME = '%s-%s-%s.tar.gz'

# Location in Pulp where modules will be stored (the filename includes all
# of the uniqueness of the module, so we can keep this flat)
# Substitutions: filename
STORAGE_MODULE_RELATIVE_PATH = '%s'

# -- progress states ----------------------------------------------------------

STATE_NOT_STARTED = 'not-started'
STATE_RUNNING = 'running'
STATE_SUCCESS = 'success'
STATE_FAILED = 'failed'
STATE_SKIPPED = 'skipped'

COMPLETE_STATES = (STATE_SUCCESS, STATE_FAILED, STATE_SKIPPED)

# -- importer configuration keys ----------------------------------------------

# Location from which to sync modules
CONFIG_FEED = 'feed'

# List of queries to run on the feed
CONFIG_QUERIES = 'queries'

# Whether or not to remove modules that were previously synchronized but were
# not on a subsequent sync
CONFIG_REMOVE_MISSING = 'remove_missing'
DEFAULT_REMOVE_MISSING = False

# -- distributor configuration keys -------------------------------------------

# Controls if modules will be served over HTTP
CONFIG_SERVE_HTTP = 'serve_http'
DEFAULT_SERVE_HTTP = True

# Controls if modules will be served over HTTP
CONFIG_SERVE_HTTPS = 'serve_https'
DEFAULT_SERVE_HTTPS = False

# Local directory the web server will serve for HTTP repositories
CONFIG_HTTP_DIR = 'http_dir'
DEFAULT_HTTP_DIR = '/var/www/pulp_puppet/http/repos'

# Local directory the web server will serve for HTTPS repositories
CONFIG_HTTPS_DIR = 'https_dir'
DEFAULT_HTTPS_DIR = '/var/www/pulp_puppet/https/repos'

# Default absolute path component of URL where repos are stored
CONFIG_ABSOLUTE_PATH = 'absolute_path'
DEFAULT_ABSOLUTE_PATH = '/pulp/puppet/'

CONFIG_INSTALL_PATH = 'install_path'

# -- forge API ---------------------------------------------------------------

# value passed as either username or password in basic auth to signify that the
# field should be considered null
FORGE_NULL_AUTH_VALUE = '.'

# -- REST API ----------------------------------------------------------------

# Option key passed to an "install" consumer request with a repository ID
# as its value that should be used for the request
REPO_ID_OPTION = 'repo_id'

# Option key passed to an "install" consumer request with a repository ID
# as its value that should have its entire contents installed
WHOLE_REPO_OPTION = 'whole_repo'

# -- extensions --------------------------------------------------------------

# Number of modules to display by name for operations that return a list of
# modules that were acted on, such as copy and remove
DISPLAY_MODULES_THRESHOLD = 100
