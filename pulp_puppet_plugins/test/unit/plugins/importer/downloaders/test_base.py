import unittest

from pulp_puppet.plugins.importers.downloaders import base


class BaseDownloaderTests(unittest.TestCase):

    def test_not_implemented(self):
        # Ensures the base class properly raises NotImplementedError for
        # appropriate APIs

        b = base.BaseDownloader(None, None, None)
        self.assertRaises(NotImplementedError, b.retrieve_metadata, None)
        self.assertRaises(NotImplementedError, b.retrieve_module, None, None)
        self.assertRaises(NotImplementedError, b.retrieve_modules, None, None)
        self.assertRaises(NotImplementedError, b.cancel)
        self.assertRaises(NotImplementedError, b.cleanup_module, None)
