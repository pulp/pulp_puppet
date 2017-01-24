from setuptools import setup, find_packages

setup(
    name='pulp_puppet_extensions_consumer',
    version='2.12c2',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points = {
        'pulp.extensions.consumer': [
            'repo_admin = pulp_puppet.extensions.consumer.pulp_cli:initialize',
        ]
    }
)
