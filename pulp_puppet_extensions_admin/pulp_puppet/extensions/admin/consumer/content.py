# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.consumer import content
from pulp.client import parsers
from pulp.client.extensions.extensions import PulpCliOption, PulpCliCommand

from pulp_puppet.common import constants


TAG_CHANGE_MADE = 'change was made'
TAG_NO_CHANGES = 'no changes'
TAG_ERROR = 'operation error'
TAG_INVALID_INPUT = 'invalid input'
TAG_TRUNCATED = 'truncated'


def parse_units(units):
    """
    parse function compatible with okaara

    :param units:   list of strings passes on the command line that each
                    represent a puppet module in the form "author/title/version"
                    where the version is optional.
    :type  units:   list

    :return:    list of puppet modules suitable for passing directly to a
                handler. Each is a dict with keys 'type_id' and 'unit_key'.
    :rtype:     list
    """
    ret = []

    for unit in units:
        parts = unit.split('/', 2)
        if len(parts) < 2:
            raise ValueError
        unit_key = {'author': parts[0], 'name': parts[1]}
        if len(parts) == 3:
            unit_key['version'] = parts[2]
        ret.append({'type_id': constants.TYPE_PUPPET_MODULE, 'unit_key': unit_key})
    return ret


OPTION_CONTENT_UNIT_REQUIRED = PulpCliOption(
    '--content-unit',
    _('module name with optional version as "author/title[/version]"'),
    required=True,
    allow_multiple=True,
    aliases=['-u'],
    parse_func=parse_units
)

OPTION_CONTENT_UNIT = PulpCliOption(
    '--content-unit',
    _('module name with optional version as "author/title[/version]"'),
    allow_multiple=True,
    required=False,
    aliases=['-u'],
    parse_func=parse_units
)

OPTION_WHOLE_REPO = PulpCliOption(
    '--whole-repo',
    _('install all modules from the repository with this ID'),
    required=False,
    aliases=['-w'],
)

OPTION_SKIP_DEP = PulpCliOption(
    '--skip-dep',
    _('if "true", skip installing any modules required by this module'),
    required=False,
    aliases=['-s'],
    parse_func=parsers.parse_boolean
)

OPTION_MODULEPATH = PulpCliOption(
    '--modulepath',
    _('the target directory'),
    required=False,
    aliases=['-m'],
)

class ContentMixin(PulpCliCommand):
    def add_content_options(self):
        self.add_option(OPTION_CONTENT_UNIT_REQUIRED)

    def get_content_units(self, kwargs):
        """
        Returns a list of puppet modules

        :param kwargs: kwargs passed to the "run" method, aka all the CLI input
        :type  kwargs: dict

        :return: list of dicts representing puppet modules
        :rtype:  list
        """
        return kwargs[OPTION_CONTENT_UNIT.keyword]

    def succeeded(self, task):
        """
        Display a success message. This method is called if the task succeeds,
        which only means that it executed on the consumer. There may still be
        errors, so this method tries to find reports of individual operation
        errors (like specific modules that couldn't be upgraded) and display
        them to the user.

        :param task:    task object that executed successfully on a consumer
        :type  task:    pulp.bindings.responses.Task

        :return: None
        """
        self._render_error_messages(task.result)
        num_changes = task.result['num_changes']
        if num_changes == 0:
            self.context.prompt.render_failure_message(
                _('Operation executed, but no changes were made.'),
                tag=TAG_NO_CHANGES
            )
        else:
            if num_changes == 1:
                message = _('1 change was made')
            else:
                message = _('%(c)d changes were made') % {'c': num_changes}
            self.context.prompt.render_success_message(message, tag=TAG_CHANGE_MADE)
            super(ContentMixin, self).succeeded(task)

    def _render_error_messages(self, result):
        """
        Given the result from a content task, makes a best effort to find and
        display error messages. Currently limited to the first 5 errors it finds.

        :param result:  'result' attribute of a puppet content-related Task
        :type  result:  dict

        :return: None
        """
        errors = result['details'][constants.TYPE_PUPPET_MODULE]['details'].get('errors', {})
        count = 0
        for module_name in errors:
            if count >= 5:
                self.context.prompt.render_failure_message(_('(additional errors truncated)'),
                                                           tag=TAG_TRUNCATED)
                break
            unknown_message = _('unknown error with module %(m)s') % {'m': module_name}
            message = errors[module_name].get('error', {}).get('oneline') or unknown_message
            self.context.prompt.render_failure_message(message, tag=TAG_ERROR)
            count += 1


class InstallCommand(ContentMixin, content.ConsumerContentInstallCommand):
    def add_content_options(self):
        self.add_option(OPTION_CONTENT_UNIT)

    def add_install_options(self):
        self.add_option(OPTION_WHOLE_REPO)
        self.add_option(OPTION_SKIP_DEP)
        self.add_option(OPTION_MODULEPATH)

    def get_content_units(self, kwargs):
        """
        Checks to make sure that either the whole-repo option was specified, or
        that one or more units were specified.

        :param kwargs:  dict of arguments passed on the command line
        :type  kwargs:  dict

        :return:    list of content units
        :rtype:     list
        """
        if kwargs.get(OPTION_WHOLE_REPO.keyword):
            return [{'unit_key': None, 'type_id': constants.TYPE_PUPPET_MODULE}]
        else:
            return super(InstallCommand, self).get_content_units(kwargs)

    def get_install_options(self, kwargs):
        """
        Looks for the --whole-repo, --skip-dep, --modulepath options and returns an corresponding "options"
        dict appropriate for a handler

        :param kwargs:  arguments passed on the command line
        :type  kwargs:  dict

        :return:    a dict suitable to pass to a puppet content handler's
                    "options" parameter.
        """
        repo_id = kwargs.get(OPTION_WHOLE_REPO.keyword)
        skip_dep = kwargs.get(OPTION_SKIP_DEP.keyword)
        module_path = kwargs.get(OPTION_MODULEPATH.keyword)
        options = {}
        if repo_id:
            options[constants.REPO_ID_OPTION] = repo_id
            options[constants.WHOLE_REPO_OPTION] = 'True'
        if skip_dep:
            options[constants.SKIP_DEP_OPTION] = skip_dep
        if module_path:
            options[constants.MODULEPATH_OPTION] = module_path
        if options:
            return options
        else:
            return super(InstallCommand, self).get_install_options(kwargs)

    def run(self, **kwargs):
        """
        Validates that either some units or a repo ID were passed in before
        letting the real "run" command run.
        """
        if not (kwargs[OPTION_CONTENT_UNIT.keyword] or kwargs[OPTION_WHOLE_REPO.keyword]):
            self.context.prompt.render_failure_message(_('no units specified'),
                                                       tag=TAG_INVALID_INPUT)
            return
        else:
            return super(InstallCommand, self).run(**kwargs)


class UpdateCommand(ContentMixin, content.ConsumerContentUpdateCommand):
    def add_update_options(self):
        self.add_option(OPTION_SKIP_DEP)
        self.add_option(OPTION_MODULEPATH)

    def get_update_options(self, kwargs):
        """
        Looks for the --skip-dep, --modulepath options and returns an corresponding "options"
        dict appropriate for a handler

        :param kwargs:  arguments passed on the command line
        :type  kwargs:  dict

        :return:    a dict suitable to pass to a puppet content handler's
                    "options" parameter.
        """
        skip_dep = kwargs.get(OPTION_SKIP_DEP.keyword)
        module_path = kwargs.get(OPTION_MODULEPATH.keyword)
        options = {}
        if skip_dep:
            options[constants.SKIP_DEP_OPTION] = skip_dep
        if module_path:
            options[constants.MODULEPATH_OPTION] = module_path
        return options


class UninstallCommand(ContentMixin, content.ConsumerContentUninstallCommand):
    def add_uninstall_options(self):
        self.add_option(OPTION_MODULEPATH)
  
    def get_uninstall_options(self, kwargs):
        """
        Looks for the --modulepath option and returns an corresponding "options"
        dict appropriate for a handler

        :param kwargs:  arguments passed on the command line
        :type  kwargs:  dict

        :return:    a dict suitable to pass to a puppet content handler's
                    "options" parameter.
        """
        module_path = kwargs.get(OPTION_MODULEPATH.keyword)
        options = {}
        if module_path:
            options[constants.MODULEPATH_OPTION] = module_path
        return options
