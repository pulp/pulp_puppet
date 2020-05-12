from setuptools import setup, find_packages

setup(
    name='pulp_puppet_handlers',
    version='2.21.2b2',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
)
