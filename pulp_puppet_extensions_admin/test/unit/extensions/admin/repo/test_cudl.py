from mock import Mock
from pulp.client.commands import options, polling
from pulp.client.commands.repo import cudl as pulp_cudl
from pulp.client.extensions.core import TAG_SUCCESS
from pulp.common.compat import json
from pulp.devel.unit.util import compare_dict

from pulp_puppet.common import constants
from pulp_puppet.devel import base_cli
from pulp_puppet.extensions.admin import pulp_cli as commands
from pulp_puppet.extensions.admin.repo import cudl


class CreatePuppetRepositoryCommandTests(base_cli.ExtensionTests):
    def setUp(self):
        super(CreatePuppetRepositoryCommandTests, self).setUp()
        self.command = commands.CreatePuppetRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure the required options
        expected_options = set([options.OPTION_REPO_ID, options.OPTION_DESCRIPTION,
                                options.OPTION_NAME, options.OPTION_NOTES,
                                cudl.OPTION_HTTP, cudl.OPTION_HTTPS, cudl.OPTION_QUERY,
                                cudl.OPTION_QUERIES])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, pulp_cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            cudl.OPTION_FEED.keyword: 'http://localhost',
            cudl.OPTION_HTTP.keyword: 'true',
            cudl.OPTION_HTTPS.keyword: 'true',
            cudl.OPTION_QUERY.keyword: ['q1', 'q2'],
            cudl.OPTION_QUERIES.keyword: None
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])
        self.assertTrue(self.server_mock.request.call_args[0][1].endswith('/v2/repositories/'))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual('test-repo', body['id'])
        self.assertEqual('Test Name', body['display_name'])
        self.assertEqual('Test Description', body['description'])

        expected_notes = {'a': 'a', constants.REPO_NOTE_KEY: constants.REPO_NOTE_PUPPET}
        self.assertEqual(expected_notes, body['notes'])

        self.assertEqual(constants.IMPORTER_TYPE_ID, body['importer_type_id'])
        expected_config = {
            u'feed': u'http://localhost',
            u'queries': [u'q1', u'q2'],
        }
        self.assertEqual(expected_config, body['importer_config'])

        dist = body['distributors'][0]
        self.assertEqual(constants.DISTRIBUTOR_TYPE_ID, dist['distributor_type_id'])
        self.assertEqual(True, dist['auto_publish'])
        self.assertEqual(constants.DISTRIBUTOR_ID, dist['distributor_id'])

        expected_config = {
            u'serve_http': True,
            u'serve_https': True,
        }
        self.assertEqual(expected_config, dist['distributor_config'])

        self.assertEqual([TAG_SUCCESS], self.prompt.get_write_tags())

    def test_queries_overrides_query(self):
        # make sure --queries overrides --query, which is deprecated
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            cudl.OPTION_FEED.keyword: 'http://localhost',
            cudl.OPTION_HTTP.keyword: 'true',
            cudl.OPTION_HTTPS.keyword: 'true',
            cudl.OPTION_QUERY.keyword: ['q1', 'q2'],
            cudl.OPTION_QUERIES.keyword: ['x', 'y']
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        expected_config = {
            u'feed': u'http://localhost',
            u'queries': [u'x', u'y'],
        }
        self.assertEqual(expected_config, body['importer_config'])


class UpdatePuppetRepositoryCommandTests(base_cli.ExtensionTests):
    def setUp(self):
        super(UpdatePuppetRepositoryCommandTests, self).setUp()
        self.command = commands.UpdatePuppetRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure the required options
        expected_options = set([options.OPTION_REPO_ID, options.OPTION_DESCRIPTION,
                                options.OPTION_NAME, options.OPTION_NOTES,
                                cudl.OPTION_HTTP, cudl.OPTION_HTTPS, cudl.OPTION_QUERY,
                                cudl.OPTION_QUERIES_UPDATE, polling.FLAG_BACKGROUND])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'update')
        self.assertEqual(self.command.description, pulp_cudl.DESC_UPDATE)

    def test_run(self):
        # Setup
        user_input = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            cudl.OPTION_FEED.keyword: 'http://localhost',
            cudl.OPTION_HTTP.keyword: 'true',
            cudl.OPTION_HTTPS.keyword: 'true',
            cudl.OPTION_QUERY.keyword: ['q1', 'q2']
        }
        self.mock_repo_response = Mock(response_body={})
        self.context.server.repo = Mock()
        self.context.server.repo.repository.return_value = self.mock_repo_response
        self.command.poll = Mock()

        self.command.run(**user_input)
        repo_config = {'display_name': 'Test Name', 'description': 'Test Description',
                       'notes': {'a': 'a'}}
        importer_config = {'feed': 'http://localhost', 'queries': ['q1', 'q2']}
        dist_config = {'puppet_distributor': {'serve_https': True, 'serve_http': True}}
        call_details = self.context.server.repo.update.call_args[0]
        self.assertEquals('test-repo', call_details[0])
        compare_dict(repo_config, call_details[1])
        compare_dict(importer_config, call_details[2])
        compare_dict(dist_config, call_details[3])

    def test_queries_overrides_query(self):
        # make sure --queries overrides --query, which is deprecated
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            cudl.OPTION_FEED.keyword: 'http://localhost',
            cudl.OPTION_HTTP.keyword: 'true',
            cudl.OPTION_HTTPS.keyword: 'true',
            cudl.OPTION_QUERY.keyword: ['q1', 'q2'],
            cudl.OPTION_QUERIES_UPDATE.keyword: ['x', 'y']
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        expected_config = {
            u'feed': u'http://localhost',
            u'queries': [u'x', u'y'],
        }
        self.assertEqual(expected_config, body['importer_config'])

    def test_unset_queries(self):
        # make sure an empty list gets sent as the new value for "queries",
        # and definitely not None
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            cudl.OPTION_FEED.keyword: 'http://localhost',
            cudl.OPTION_HTTP.keyword: 'true',
            cudl.OPTION_HTTPS.keyword: 'true',
            cudl.OPTION_QUERY.keyword: None,
            cudl.OPTION_QUERIES_UPDATE.keyword: []
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        expected_config = {
            u'feed': u'http://localhost',
            u'queries': [],  # this is the key part of this test
        }
        self.assertEqual(expected_config, body['importer_config'])


class ListPuppetRepositoriesCommandTests(base_cli.ExtensionTests):
    def setUp(self):
        super(ListPuppetRepositoriesCommandTests, self).setUp()
        self.command = commands.ListPuppetRepositoriesCommand(self.context)

    def test_get_repositories(self):
        # Setup
        repos = [
            {'id': 'repo-1', 'notes': {constants.REPO_NOTE_KEY: constants.REPO_NOTE_PUPPET}},
            {'id': 'repo-2', 'notes': {constants.REPO_NOTE_KEY: constants.REPO_NOTE_PUPPET}},
            {'id': 'repo-3', 'notes': {constants.REPO_NOTE_KEY: 'rpm'}},
            {'id': 'repo-4', 'notes': {}},
        ]

        self.server_mock.request.return_value = 200, repos

        # Test
        repos = self.command.get_repositories({})

        # Verify
        self.assertEqual(2, len(repos))

        repo_ids = [r['id'] for r in repos]
        self.assertTrue('repo-1' in repo_ids)
        self.assertTrue('repo-2' in repo_ids)

    def test_get_other_repositories(self):
        # Setup
        repos = [
            {'id': 'repo-1', 'notes': {constants.REPO_NOTE_KEY: constants.REPO_NOTE_PUPPET}},
            {'id': 'repo-2', 'notes': {constants.REPO_NOTE_KEY: 'rpm'}},
            {'id': 'repo-3', 'notes': {}},
        ]

        self.server_mock.request.return_value = 200, repos

        # Test
        repos = self.command.get_other_repositories({})

        # Verify
        self.assertEqual(2, len(repos))

        repo_ids = [r['id'] for r in repos]
        self.assertTrue('repo-2' in repo_ids)
        self.assertTrue('repo-3' in repo_ids)

    def test_get_with_distributors(self):
        # Setup
        repos = [
            {
                'id': 'repo-1',
                'notes': {constants.REPO_NOTE_KEY: constants.REPO_NOTE_PUPPET},
                'distributors': [{}],
            },
        ]

        self.server_mock.request.return_value = 200, repos

        # Test
        repos = self.command.get_repositories({})

        # make sure the "relative_path" attribute was added correctly
        # to the distributor
        self.assertEqual(
            repos[0]['distributors'][0].get('relative_path'), 'puppet/repo-1/')
