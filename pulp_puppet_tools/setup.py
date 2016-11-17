from setuptools import setup, find_packages

setup(
    name='pulp_puppet_tools',
    version='2.10.3a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    entry_points={
        'console_scripts': [
            'pulp-puppet-module-builder = pulp_puppet.tools.puppet_module_builder:main',
        ]
    }
)
