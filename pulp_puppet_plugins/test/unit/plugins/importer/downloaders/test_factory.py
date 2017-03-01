import unittest

from pulp_puppet.plugins.importers.downloaders import factory
from pulp_puppet.plugins.importers.downloaders.exceptions import UnsupportedFeedType, InvalidFeed
from pulp_puppet.plugins.importers.downloaders.local import LocalDownloader


class DownloadersFactoryTests(unittest.TestCase):

    def test_get_downloader(self):
        # Test
        downloader = factory.get_downloader('file://localhost', None, None, None)

        # Verify
        self.assertTrue(downloader is not None)
        self.assertTrue(isinstance(downloader, LocalDownloader))

    def test_get_downloader_invalid_feed(self):
        try:
            factory.get_downloader(None, None, None, None)
            self.fail()
        except InvalidFeed, e:
            self.assertEqual(e.feed, None)

    def test_get_downloader_unsupported_feed_type(self):
        try:
            factory.get_downloader('jdob://localhost', None, None, None)
            self.fail()
        except UnsupportedFeedType, e:
            self.assertEqual(e.feed_type, 'jdob')

    def test_is_valid_feed(self):
        self.assertTrue(factory.is_valid_feed('file://localhost'))

    def test_is_valid_feed_false(self):
        self.assertFalse(factory.is_valid_feed(None))
