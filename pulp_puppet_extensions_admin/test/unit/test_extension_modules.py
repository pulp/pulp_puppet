from pulp.client.commands import options
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand

from pulp_puppet.devel import base_cli
from pulp_puppet.extensions.admin.repo import modules

# -- constants ----------------------------------------------------------------

SAMPLE_RESPONSE_BODY =[
    {
    "updated": "2012-08-29T14:39:39",
    "repo_id": "blog-repo",
    "created": "2012-08-29T14:39:39",
    "_ns": "repo_content_units",
    "unit_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
    "metadata": {
        "_storage_path": "/var/lib/pulp/content/puppet_module/thias-apache_httpd-0.3.2.tar.gz",
        "license ": "Apache 2.0",
        "description": "Install and enable the Apache httpd web server and manage its configuration with snippets.",
        "author": "thias",
        "_ns": "units_puppet_module",
        "_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
        "project_page": "http://glee.thias.es/puppet",
        "summary": "Apache HTTP Daemon installation and configuration",
        "source": "git://github.com/thias/puppet-modules/modules/apache_httpd",
        "dependencies": [],
        "version": "0.3.2",
        "_content_type_id": "puppet_module",
        "checksums": [["files/trace.inc", "00b0ef3384ae0ae23641de16a4f409c2"],],
        "tag_list": ["webservers", "apache"],
        "types": [],
        "name": "apache_httpd"
    },
    "unit_type_id": "puppet_module",
    "_id": {"$oid": "503e61eb8a905b3cc5000034"},
    "id": "503e61eb8a905b3cc5000034"
    },
        {
        "updated": "2012-08-29T14:39:39",
        "repo_id": "blog-repo",
        "created": "2012-08-29T14:39:39",
        "_ns": "repo_content_units",
        "unit_id": "1e6ef714-51fe-4233-976f-fc6374cbeb61",
        "metadata": {
            "_storage_path": "/var/lib/pulp/content/puppet_module/thias-apache_httpd-1.3.2.tar.gz",
            "license ": "Apache 2.0",
            "description": "Install and enable the Apache httpd web server and manage its configuration with snippets.",
            "author": "thias",
            "_ns": "units_puppet_module",
            "_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
            "project_page": "http://glee.thias.es/puppet",
            "summary": "Apache HTTP Daemon installation and configuration",
            "source": "git://github.com/thias/puppet-modules/modules/apache_httpd",
            "dependencies": [],
            "version": "1.3.2",
            "_content_type_id": "puppet_module",
            "checksums": [["files/trace.inc", "00b0ef3384ae0ae23641de16a4f409c2"],],
            "tag_list": ["webservers", "apache"],
            "types": [],
            "name": "apache_httpd"
        },
        "unit_type_id": "puppet_module",
        "_id": {"$oid": "503e61eb8a905b3cc5000034"},
        "id": "503e61eb8a905b3cc5000034"
    }
]

# -- test cases ---------------------------------------------------------------

class ModulesCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(ModulesCommandTests, self).setUp()
        self.command = modules.ModulesCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, DisplayUnitAssociationsCommand))
        self.assertEqual('modules', self.command.name)
        self.assertEqual(modules.DESC_SEARCH, self.command.description)

    def test_modules(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 200, SAMPLE_RESPONSE_BODY

        # Test
        self.command.run(**data)

        # Verify - make sure the first three lines are the correct order and do
        # not have the association information
        self.assertTrue(self.recorder.lines[0].startswith('Name'))
        self.assertTrue(self.recorder.lines[1].startswith('Version'))
        self.assertTrue(self.recorder.lines[2].startswith('Author'))

    def test_modules_with_metadata(self):
        # Setup
        data = {options.OPTION_REPO_ID.keyword : 'test-repo',
                DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: True}

        self.server_mock.request.return_value = 200, SAMPLE_RESPONSE_BODY

        # Test
        self.command.run(**data)

        # Verify - make sure the first line is from the association data
        self.assertTrue(self.recorder.lines[0].startswith('Created'))
