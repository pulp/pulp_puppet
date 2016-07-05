from setuptools import setup, find_packages

setup(
    name='pulp_puppet_plugins',
    version='2.9.1a1',
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
        'pulp.unit_models': [
            'puppet_module=pulp_puppet.plugins.db.models:Module'
        ],
    }
)
