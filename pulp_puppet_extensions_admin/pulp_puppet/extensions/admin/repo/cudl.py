from gettext import gettext as _

from pulp.client import arg_utils, parsers
from pulp.client.commands import options
from pulp.client.commands.repo.importer_config import ImporterConfigMixin
from pulp.client.extensions.extensions import PulpCliOption
from pulp.client.commands.repo.cudl import (CreateRepositoryCommand, ListRepositoriesCommand,
                                            UpdateRepositoryCommand)

from pulp_puppet.common import constants


DESC_FEED = _('URL of the external source from which to import Puppet modules')
OPTION_FEED = PulpCliOption('--feed', DESC_FEED, required=False)

DESC_QUERY = _(
    '(deprecated) ignored if "--queries" is specified. '
    'query to issue against the feed\'s modules.json file to scope which '
    'modules are imported; multiple queries may be added by specifying this '
    'argument multiple times'
)
OPTION_QUERY = PulpCliOption('--query', DESC_QUERY, required=False, allow_multiple=True)

DESC_QUERIES = _(
    'comma-separated list of queries to issue against the feed\'s modules.json '
    'file to scope which modules are imported. ignored when feed is static files.'
)
OPTION_QUERIES = PulpCliOption(
    '--queries', DESC_QUERIES, required=False, allow_multiple=False,
    parse_func=parsers.csv)

DESC_QUERIES_UPDATE = _(
    'comma-separated list of queries to issue against the feed\'s modules.json '
    'file to scope which modules are imported. overwrites previous values. '
    'ignored when feed is static files.'
)
OPTION_QUERIES_UPDATE = PulpCliOption(
    '--queries', DESC_QUERIES_UPDATE, required=False, allow_multiple=False,
    parse_func=parsers.csv)

DESC_HTTP = _('if "true", the repository will be served over HTTP; defaults to true')
OPTION_HTTP = PulpCliOption('--serve-http', DESC_HTTP, required=False)

DESC_HTTPS = _('if "true", the repository will be served over HTTPS; defaults to false')
OPTION_HTTPS = PulpCliOption('--serve-https', DESC_HTTPS, required=False)

DESC_SEARCH = _('searches for Puppet repositories on the server')

DESC_REMOVE_MISSING = _('if "true", units that were previously in the external feed but are '
                        'no longer found will be removed from the repository; defaults to false')
OPTION_REMOVE_MISSING = PulpCliOption('--remove-missing', DESC_REMOVE_MISSING, required=False,
                                      parse_func=parsers.pulp_parse_optional_boolean)


class CreatePuppetRepositoryCommand(CreateRepositoryCommand, ImporterConfigMixin):
    def __init__(self, context):
        CreateRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, include_unit_policy=False)

        self.add_option(OPTION_QUERIES)
        self.add_option(OPTION_QUERY)
        self.add_option(OPTION_HTTP)
        self.add_option(OPTION_HTTPS)
        self.add_option(OPTION_REMOVE_MISSING)

    def run(self, **kwargs):

        # -- repository metadata --
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        description = kwargs[options.OPTION_DESCRIPTION.keyword]
        notes = kwargs.pop(options.OPTION_NOTES.keyword) or {}

        # Add a note to indicate this is a Puppet repository
        notes[constants.REPO_NOTE_KEY] = constants.REPO_NOTE_PUPPET

        name = repo_id
        if options.OPTION_NAME.keyword in kwargs:
            name = kwargs[options.OPTION_NAME.keyword]

        # -- importer metadata --
        importer_config = self.parse_user_input(kwargs)
        importer_config.update({constants.CONFIG_QUERIES:
                                kwargs[OPTION_QUERIES.keyword] or kwargs[OPTION_QUERY.keyword]})
        arg_utils.convert_removed_options(importer_config)

        # -- distributor metadata --
        distributor_config = {
            constants.CONFIG_SERVE_HTTP: kwargs[OPTION_HTTP.keyword],
            constants.CONFIG_SERVE_HTTPS: kwargs[OPTION_HTTPS.keyword],
            }
        arg_utils.convert_removed_options(distributor_config)
        arg_utils.convert_boolean_arguments((constants.CONFIG_SERVE_HTTP,
                                             constants.CONFIG_SERVE_HTTPS), distributor_config)

        distributors = [
            dict(distributor_type_id=constants.DISTRIBUTOR_TYPE_ID,
                 distributor_config=distributor_config,
                 auto_publish=True, distributor_id=constants.DISTRIBUTOR_ID)
        ]

        # Create the repository
        self.context.server.repo.create_and_configure(repo_id, name, description, notes,
                                                      constants.IMPORTER_TYPE_ID,
                                                      importer_config, distributors)

        msg = _('Successfully created repository [%(r)s]')
        self.context.prompt.render_success_message(msg % {'r': repo_id})


class UpdatePuppetRepositoryCommand(UpdateRepositoryCommand, ImporterConfigMixin):

    def __init__(self, context):
        UpdateRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, include_unit_policy=False)

        self.add_option(OPTION_QUERIES_UPDATE)
        self.add_option(OPTION_QUERY)
        self.add_option(OPTION_HTTP)
        self.add_option(OPTION_HTTPS)
        self.add_option(OPTION_REMOVE_MISSING)

    def run(self, **kwargs):
        # -- importer metadata --
        queries = kwargs.pop(OPTION_QUERIES.keyword, None)
        if queries is None:
            queries = kwargs.pop(OPTION_QUERY.keyword, None)
        importer_config = self.parse_user_input(kwargs)
        importer_config.update({constants.CONFIG_QUERIES: queries})
        if importer_config:
            arg_utils.convert_removed_options(importer_config)
            kwargs['importer_config'] = importer_config

        # Remove the importer keys from kwargs so they don't get added to the repo config
        for key in importer_config:
            kwargs.pop(key.replace('_', '-'), None)

        # -- distributor metadata --
        distributor_config = {
            constants.CONFIG_SERVE_HTTP: kwargs.pop(OPTION_HTTP.keyword, None),
            constants.CONFIG_SERVE_HTTPS: kwargs.pop(OPTION_HTTPS.keyword, None)
        }
        arg_utils.convert_removed_options(distributor_config)
        arg_utils.convert_boolean_arguments((constants.CONFIG_SERVE_HTTP,
                                             constants.CONFIG_SERVE_HTTPS), distributor_config)
        # Remove the distributor keys from kwargs so they don't get added to the repo config
        for key in distributor_config:
            kwargs.pop(key, None)

        kwargs['distributor_configs'] = {}
        if distributor_config:
            kwargs['distributor_configs'][constants.DISTRIBUTOR_ID] = distributor_config
        super(UpdatePuppetRepositoryCommand, self).run(**kwargs)


class ListPuppetRepositoriesCommand(ListRepositoriesCommand):

    def __init__(self, context):
        repos_title = _('Puppet Repositories')
        super(ListPuppetRepositoriesCommand, self).__init__(context,
                                                            repos_title=repos_title)

        # Both get_repositories and get_other_repositories will act on the full
        # list of repositories. Lazy cache the data here since both will be
        # called in succession, saving the round trip to the server.
        self.all_repos_cache = None

    def get_repositories(self, query_params, **kwargs):
        all_repos = self._all_repos(query_params, **kwargs)

        puppet_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if constants.REPO_NOTE_KEY in notes and \
                    notes[constants.REPO_NOTE_KEY] == constants.REPO_NOTE_PUPPET:
                puppet_repos.append(repo)

        for repo in puppet_repos:
            if repo.get('distributors'):
                repo['distributors'][0]['relative_path'] = 'puppet/%s/' % repo['id']

        return puppet_repos

    def get_other_repositories(self, query_params, **kwargs):
        all_repos = self._all_repos(query_params, **kwargs)

        non_puppet_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if notes.get(constants.REPO_NOTE_KEY, None) != constants.REPO_NOTE_PUPPET:
                non_puppet_repos.append(repo)

        return non_puppet_repos

    def _all_repos(self, query_params, **kwargs):

        # This is safe from any issues with concurrency due to how the CLI works
        if self.all_repos_cache is None:
            all_repos_cache = self.context.server.repo.repositories(query_params).response_body
            self.all_repos_cache = all_repos_cache

        return self.all_repos_cache
