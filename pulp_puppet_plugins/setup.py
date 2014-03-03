# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from setuptools import setup, find_packages

setup(
    name='pulp_puppet_plugins',
    version='2.4.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points = {
        'pulp.distributors': [
            'distributor = pulp_puppet.plugins.distributors.distributor:entry_point',
            'installdistributor = pulp_puppet.plugins.distributors.installdistributor:entry_point',
            'filedistributor = pulp_puppet.plugins.distributors.filedistributor:entry_point',
        ],
        'pulp.importers': [
            'importer = pulp_puppet.plugins.importers.importer:entry_point',
        ],
        'pulp.profilers': [
            'profiler = pulp_puppet.plugins.profilers.wholerepo:entry_point',
        ],
        'pulp.server.db.migrations': [
            'pulp_puppet = pulp_puppet.plugins.migrations',
        ],
    }
)
