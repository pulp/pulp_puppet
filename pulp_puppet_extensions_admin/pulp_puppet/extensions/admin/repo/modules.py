"""
Commands related to searching for modules in a Puppet repository.
"""

from gettext import gettext as _

from pulp.client.commands import options
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand

from pulp_puppet.common import constants

# -- constants ----------------------------------------------------------------

DESC_SEARCH = _('search for modules in a repository')

# -- commands -----------------------------------------------------------------


class ModulesCommand(DisplayUnitAssociationsCommand):
    def __init__(self, context):
        super(ModulesCommand, self).__init__(self.run, name='modules',
                                             description=DESC_SEARCH)
        self.context = context
        self.prompt = context.prompt

    def run(self, **kwargs):
        # Retrieve the modules
        repo_id = kwargs.pop(options.OPTION_REPO_ID.keyword)
        kwargs['type_ids'] = [constants.TYPE_PUPPET_MODULE]
        modules = self.context.server.repo_unit.search(repo_id, **kwargs).response_body

        # Strip out checksum information; not sure how to render it yet
        # or if it's even useful
        map(lambda x: x['metadata'].pop('checksums', None), modules)

        order = []

        if not kwargs.get(self.ASSOCIATION_FLAG.keyword):
            # Remove types from the metadata as it can be very long by default
            # and only display the module metadata, not the association
            map(lambda x: x['metadata'].pop('types', None), modules)
            modules = [m['metadata'] for m in modules]
            # Make sure the key info is at the top; the rest can be alpha
            order = ['name', 'version', 'author']

        self.prompt.render_document_list(modules, order=order)
