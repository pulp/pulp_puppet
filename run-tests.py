#!/usr/bin/env python2

import os
import subprocess

from pulp.devel.test_runner import run_tests

# Find and eradicate any existing .pyc files, so they do not eradicate us!
PROJECT_DIR = os.path.dirname(__file__)
subprocess.call(['find', PROJECT_DIR, '-name', '*.pyc', '-delete'])

PACKAGES = [os.path.dirname(__file__), 'pulp_puppet']

EL5_SAFE_TESTS = [
    'pulp_puppet_common/test/unit/',
    'pulp_puppet_extensions_admin/test/unit/',
    'pulp_puppet_extensions_consumer/test/unit/',
    'pulp_puppet_handlers/test/unit/',
]

NON_EL5_TESTS = [
    'pulp_puppet_plugins/test/unit/',
    'pulp_puppet_tools/test/unit/',
]

dir_safe_all_platforms = [os.path.join(os.path.dirname(__file__), x) for x in EL5_SAFE_TESTS]
dir_safe_non_rhel5 = [os.path.join(os.path.dirname(__file__), x) for x in NON_EL5_TESTS]

os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp_puppet.forge.settings'

run_tests(PACKAGES, dir_safe_all_platforms, dir_safe_non_rhel5,
          flake8_paths=[PROJECT_DIR])
