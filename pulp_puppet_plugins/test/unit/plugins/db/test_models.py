import unittest

from pulp.common.compat import json

from pulp_puppet.plugins.db.models import RepositoryMetadata, Module

# -- constants ----------------------------------------------------------------

VALID_REPO_METADATA_JSON = """[
{"tag_list":["postfix","applications"],
 "project_url":"http://www.example42.com",
 "name":"postfix",
 "author":"lab42",
 "releases":[{"version":"0.0.1"},{"version":"0.0.2"}],
 "desc":"Test Postfix module.",
 "version":"0.0.2",
 "full_name":"lab42/postfix",
 "checksum":"foo",
 "checksum_type":"foo_type"},
{"tag_list":[],
 "project_url":"http://www.example42.com",
 "name":"common",
 "author":"lab42",
 "releases":[{"version":"0.0.1"}],
 "desc":"Example42 common resources module.",
 "version":"0.0.1",
 "full_name":"lab42/common",
 "checksum":"bar",
 "checksum_type":"bar_type"}
]
"""

VALID_MODULE_METADATA_JSON = """{
  "name": "jdob-valid",
  "version": "1.0.0",
  "source": "http://example.org/jdob-valid/source",
  "author": "jdob",
  "license": "Apache License, Version 2.0",
  "summary": "Valid Module Summary",
  "description": "Valid Module Description",
  "project_page": "http://example.org/jdob-valid",
  "dependencies": [
    {
      "name": "jdob/dep-alpha",
      "version_requirement": ">= 1.0.0"
    },
    {
      "name": "ldob/dep-beta",
      "version_requirement": ">= 2.0.0"
    }
  ],
  "types": [],
  "checksums": {
    "Modulefile": "704cecf2957448dcf7fa20cffa2cf7c1",
    "README": "11edd8578497566d8054684a8c89c6cb",
    "manifests/init.pp": "1d1fb26825825b4d64d37d377016869e",
    "spec/spec_helper.rb": "a55d1e6483344f8ec6963fcb2c220372",
    "tests/init.pp": "7043c7ef0c4b0ac52b4ec6bb76008ebd"
  },
  "checksum": "anvil",
  "checksum_type": "acme_checksum"
}
"""

# -- test cases ---------------------------------------------------------------


class RepositoryMetadataTests(unittest.TestCase):

    def test_update_from_json(self):
        # Test
        metadata = RepositoryMetadata()
        metadata.update_from_json(VALID_REPO_METADATA_JSON)

        # Verify
        self.assertEqual(2, len(metadata.modules))
        for m in metadata.modules:
            self.assertTrue(isinstance(m, Module))

        sorted_modules = sorted(metadata.modules, key=lambda x: x.name)

        self.assertEqual(sorted_modules[0].name, 'common')
        self.assertEqual(sorted_modules[0].author, 'lab42')
        self.assertEqual(sorted_modules[0].version, '0.0.1')
        self.assertEqual(sorted_modules[0].tag_list, [])
        self.assertEqual(sorted_modules[0].description, None)
        self.assertEqual(sorted_modules[0].project_page, None)
        self.assertEqual(sorted_modules[0].checksum, 'bar')
        self.assertEqual(sorted_modules[0].checksum_type, 'bar_type')

        self.assertEqual(sorted_modules[1].name, 'postfix')
        self.assertEqual(sorted_modules[1].author, 'lab42')
        self.assertEqual(sorted_modules[1].version, '0.0.2')
        self.assertEqual(sorted_modules[1].tag_list, ['postfix', 'applications'])
        self.assertEqual(sorted_modules[1].description, None)
        self.assertEqual(sorted_modules[1].project_page, None)
        self.assertEqual(sorted_modules[1].checksum, 'foo')
        self.assertEqual(sorted_modules[1].checksum_type, 'foo_type')

    def test_to_json(self):
        # Setup
        metadata = RepositoryMetadata()
        metadata.update_from_json(VALID_REPO_METADATA_JSON)

        # Test
        serialized = metadata.to_json()

        # Verify
        parsed = json.loads(serialized)

        self.assertEqual(2, len(parsed))

        sorted_modules = sorted(parsed, key=lambda x: x['name'])

        self.assertEqual(4, len(sorted_modules[0]))
        self.assertEqual(sorted_modules[0]['name'], 'common')
        self.assertEqual(sorted_modules[0]['author'], 'lab42')
        self.assertEqual(sorted_modules[0]['version'], '0.0.1')
        self.assertEqual(sorted_modules[0]['tag_list'], [])

        self.assertEqual(4, len(sorted_modules[1]))
        self.assertEqual(sorted_modules[1]['name'], 'postfix')
        self.assertEqual(sorted_modules[1]['author'], 'lab42')
        self.assertEqual(sorted_modules[1]['version'], '0.0.2')
        self.assertEqual(sorted_modules[1]['tag_list'], ['postfix', 'applications'])
