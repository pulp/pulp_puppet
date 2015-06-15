"""
Utilities for testing downloader implementations.
"""

import mock
import os
import shutil
import tempfile
import unittest

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository


class BaseDownloaderTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='downloader-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)

        self.config = PluginCallConfiguration({}, {})

        self.mock_progress_report = mock.MagicMock()

        self.author = 'jdob'
        self.name = 'valid'
        self.version = '1.1.0'
        self.module = mock.Mock()

    def tearDown(self):
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)
