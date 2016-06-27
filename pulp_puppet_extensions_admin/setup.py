from setuptools import setup, find_packages

setup(
    name='pulp_puppet_extensions_admin',
    version='2.8.5',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points = {
        'pulp.extensions.admin': [
            'repo_admin = pulp_puppet.extensions.admin.pulp_cli:initialize',
        ]
    }
)
