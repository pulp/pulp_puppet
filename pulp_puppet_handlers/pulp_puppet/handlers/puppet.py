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

import logging
import subprocess

from pulp.agent.lib import handler
from pulp.agent.lib.report import BindReport, CleanReport, ContentReport
from pulp.common.compat import json

from pulp_puppet.common import constants


logger = logging.getLogger(__name__)


class ModuleHandler(handler.ContentHandler):
    @staticmethod
    def _generate_forge_url(conduit, repo_id=None):
        """
        Generate a URL for the forge to use, and encode consumer ID or repo ID
        as appropriate with basic auth credentials.

        :param conduit: A handler conduit
        :type  conduit: pulp.agent.gofer.pulp.Conduit
        :param repo_id: unique ID of a repo to which this operation should
                        be scoped
        :return: URL
        :rtype:  str
        """
        if repo_id:
            username = constants.FORGE_NULL_AUTH_VALUE
        else:
            username = conduit.consumer_id
        password = repo_id or constants.FORGE_NULL_AUTH_VALUE
        host = conduit.get_consumer_config()['server']['host']

        # the "puppet module" tool does not seem to support HTTPS, unfortunately
        return 'http://%s:%s@%s' % (username, password, host)

    @classmethod
    def install(cls, conduit, units, options):
        """
        Install content unit(s).

        :param  conduit: A handler conduit
        :type   conduit: pulp.agent.gofer.pulp.Conduit
        :param  units: A list of content unit (keys)
        :type   units: list
        :param  options: Unit install options.
        :type   options: dict

        :return:    An install report.
                    "details" contains a dict with keys "errors" and "successes".
                    "errors" are any operation where the "puppet module" tool
                    returned a non-zero exit code or where the output from that
                    tool indicated an error. Everything else is in "successes".
        :rtype:     pulp.agent.lib.report.ContentReport
        """
        successes, errors, num_changes = cls._perform_operation(
            'install', units, cls._generate_forge_url(conduit))
        report = ContentReport()
        report.set_succeeded({'successes': successes, 'errors': errors}, num_changes)
        return report

    @classmethod
    def update(cls, conduit, units, options):
        """
        Update content unit(s).

        :param  conduit: A handler conduit
        :type   conduit: pulp.agent.gofer.pulp.Conduit
        :param  units: A list of content unit (keys)
        :type   units: list
        :param  options: Unit update options.
        :type   options: dict
        :return:    An update report.
                    "details" contains a dict with keys "errors" and "successes".
                    "errors" are any operation where the "puppet module" tool
                    returned a non-zero exit code or where the output from that
                    tool indicated an error. Everything else is in "successes".
        :rtype:     pulp.agent.lib.report.ContentReport
        """
        successes, errors, num_changes = cls._perform_operation(
            'upgrade', units, cls._generate_forge_url(conduit))
        report = ContentReport()
        report.set_succeeded({'successes': successes, 'errors': errors}, num_changes)
        return report

    @classmethod
    def uninstall(cls, conduit, units, options):
        """
        Uninstall content unit(s). In case dependency conflicts cause an
        uninstall to fail, this will continue to retry the entire collection of
        failed operations until an entire pass results in no successes.

        :param  conduit: A handler conduit
        :type   conduit: pulp.agent.gofer.pulp.Conduit
        :param  units: A list of content unit (keys)
        :type   units: list
        :param  options: Unit uninstall options.
        :type   options: dict
        :return:    An uninstall report.
                    "details" contains a dict with keys "errors" and "successes".
                    "errors" are any operation where the "puppet module" tool
                    returned a non-zero exit code or where the output from that
                    tool indicated an error. Everything else is in "successes".
        :rtype:     pulp.agent.lib.report.ContentReport
        """
        previous_failure_count = 0
        successes, errors, num_changes = cls._perform_operation('uninstall', units)

        # need this so we can easily access original unit objects when constructing
        # new requests below
        units_by_full_name = dict(('%s/%s'% (u['author'], u['name']), u) for u in units)

        # loop over the results, and keep trying to uninstall failed attempts as
        # a dumb but effective way of dealing with dependency-related failures.
        # keep trying until we get to an iteration where no more modules are
        # uninstalled.
        while True:
            failed_names = errors.keys()
            if len(failed_names) == 0:
                # success all around! no need to retry
                break
            elif previous_failure_count == 0 or len(failed_names) < previous_failure_count:
                previous_failure_count = len(failed_names)
                failed_units = [units_by_full_name[full_name] for full_name in failed_names]
                # retry the failed attempts
                new_successes, new_errors, new_num_changes = cls._perform_operation('uninstall', failed_units)
                num_changes += new_num_changes
                # move new successes from "errors" to "successes"
                successes.update(new_successes)
                for full_name in new_successes.keys():
                    del errors[full_name]
            else:
                # non-zero failure count didn't change, so it's time to give up.
                break

        report = ContentReport()
        report.set_succeeded({'successes': successes, 'errors': errors}, num_changes)
        return report

    def profile(self, conduit):
        """
        Request the installed content profile be sent
        to the pulp server.

        :param  conduit: A handler conduit.
        :type   conduit: pulp.agent.lib.conduit.Conduit
        :return:    A profile report.
        :rtype:     pulp.agent.lib.report.ProfileReport
        """
        raise NotImplementedError()

    @classmethod
    def _perform_operation(cls, operation, units, forge_url=None):
        """
        For a list of units, attempt to perform the given operation. Separates
        results for each individual unit into "successes" and "errors". An error
        is any operation where the "puppet module" tool returned a non-zero exit
        code, or where the key "error" appears in that tool's JSON output.
        Everything else is a success.

        :param operation:   one of "install", "upgrade", or "uninstall"
        :type  operation:   str
        :param units:       list of puppet module keys
        :type  units:       list of dicts
        :param forge_url:   optional URL for a forge. By default, the "puppet
                            module" tool uses the official Puppet Forge.
        :type  forge_url:   str
        :return:    three-member tuple of successes, errors, and num_changes.
                    "successes" is a dict where keys are full package names and
                    values are dicts that come from the JSON output of the "puppet
                    module" tool, with some noise removed.
                    "errors" is a dict where keys are full package names and
                    values are dicts that come from the JSON output of the "puppet
                    module" tool.
                    "num_changes" is an integer representing how many actual
                    changes occurred.
        :rtype:     tuple(dict, dict, int)
        """
        errors = {}
        successes = {}
        num_changes = 0

        for unit in units:
            # prepare the command
            full_name = '%s/%s' % (unit['author'], unit['name'])
            args = ['puppet', 'module', operation, '--render-as', 'json']
            if forge_url:
                args.extend(['--module_repository', forge_url])
            if unit.get('version'):
                args.extend(['--version', unit['version']])
            args.append(full_name)

            # execute the command
            try:
                popen = subprocess.Popen(args, stdout=subprocess.PIPE)
            except OSError:
                logger.error('"puppet module" tool not found')
                errors[full_name] = {'error': '"puppet module" tool not found'}
                break

            stdout, stderr = popen.communicate()
            operation_report = cls._interpret_operation_report(stdout, operation, full_name)

            # 'success' means a change took place, so count it for the final report
            if operation_report.get('result') == 'success':
                num_changes += 1
            if popen.returncode == 0 and 'error' not in operation_report:
                logger.info('%s of module %s' % (operation, full_name))
                successes[full_name] = operation_report
            else:
                errors[full_name] = operation_report
        cls._clean_successful_reports(successes.values(), operation)
        return successes, errors, num_changes

    @staticmethod
    def _interpret_operation_report(output, operation, full_name):
        """
        Makes a best effort to locate and deserialize the JSON output from the
        "puppet module" tool. The tool does not document exactly how this will
        be included in the output, so this method

        :param output:      text output from the "puppet module" tool, which
                            presumably includes some JSON
        :type  output:      str
        :param operation:   one of "install", "upgrade", "uninstall", used only
                            for logging.
        :type  operation:   str
        :param full_name:   full name in form "author/title", used only for
                            logging

        :return:    deserialized JSON output from the "puppet module" tool
        :rtype:     dict
        """
        try:
            potential_json = output.split('\n')[-2]
            operation_report = json.loads(potential_json)
        # if there was any error trying to parse puppet's JSON output, make
        # an empty report
        except (IndexError, ValueError):
            logger.warning('failed to parse JSON output from %s of %s' % (operation, full_name))
            operation_report = {}
        return operation_report

    @classmethod
    def _clean_successful_reports(cls, reports, operation):
        """
        Take the deserialized output from successful actions by "puppet module"
        and remove pieces that we don't care about, for example keys whose value
        is None. Changes are made in-place.

        :param reports:     list of dicts that each represent the JSON output of
                            a call to "puppet module"
        :type  reports:     list of dicts
        :param operation:   one of "install", "upgrade", "uninstall"
        :type  operation:  str

        :return:    None
        """
        for report in reports:
            for attribute in ('install_dir', 'result'):
                if attribute in report:
                    del report[attribute]
            for attribute in ('requested_version', 'module_version'):
                if attribute in report and not report[attribute]:
                    del report[attribute]
            if operation == 'install':
                module_reports = report.get('installed_modules', [])
            elif operation == 'upgrade':
                module_reports = report.get('affected_modules', [])
            else:
                continue
            cls._clean_inner_module_reports(module_reports, operation)

    @classmethod
    def _clean_inner_module_reports(cls, module_reports, operation):
        """
        Some reports include actions on multiple modules, for example when an
        install requires the installation of dependencies. This iterates over
        each of them and descends into their dependencies recursively.

        Below is example output from the "puppet module install" command where
        "installed_modules" contains "inner reports", and this method descends
        from there into dependencies of each.

        {'install_dir': '/home/someuser/.puppet/modules',
         'installed_modules': [{'action': 'install',
           'dependencies': [{'action': 'install',
             'dependencies': [],
             'file': '/system/releases/b/branan/branan-s3file-1.0.0.tar.gz',
             'module': 'branan-s3file',
             'path': '/home/someuser/.puppet/modules',
             'previous_version': None,
             'version': {'semver': 'v1.0.0', 'vstring': '1.0.0'}},
            {'action': 'install',
             'dependencies': [],
             'file': '/system/releases/p/puppetlabs/puppetlabs-java-0.2.0.tar.gz',
             'module': 'puppetlabs-java',
             'path': '/home/someuser/.puppet/modules',
             'previous_version': None,
             'version': {'semver': 'v0.2.0', 'vstring': '0.2.0'}},
            {'action': 'install',
             'dependencies': [],
             'file': '/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz',
             'module': 'puppetlabs-stdlib',
             'path': '/home/someuser/.puppet/modules',
             'previous_version': None,
             'version': {'semver': 'v3.2.0', 'vstring': '3.2.0'}}],
           'file': '/system/releases/b/branan/branan-minecraft-1.0.0.tar.gz',
           'module': 'branan-minecraft',
           'path': '/home/someuser/.puppet/modules',
           'previous_version': None,
           'version': {'semver': 'v1.0.0', 'vstring': '1.0.0'}}],
         'module_name': 'branan-minecraft',
         'module_version': None,
         'result': 'success'}

        :param module_reports:  list of inner module reports.
        :param operation:       one of "install", "upgrade", "uninstall"
        :type  operation:       str

        :return:    None
        """
        for module in module_reports:
            for attribute in ('file', 'path'):
                if attribute in module:
                    del module[attribute]
            # only include the action if it is different than the primary action.
            # this will be the case if an install operation requires the upgrade
            # of a dependency
            if module.get('action') == operation:
                del module['action']
            # only include the "previous version" key if it has a value
            for attribute in ('previous_version', 'dependencies'):
                if attribute in module and not module[attribute]:
                    del module[attribute]
            # recursively clean down the dependency tree
            cls._clean_inner_module_reports(module.get('dependencies', []), operation)


class BindHandler(handler.BindHandler):
    @staticmethod
    def bind(conduit, binding, options):
        """
        Bind a repository. This is a no-op since the consumer does not need
        to keep any state with regard to bindings.

        :param  conduit: A handler conduit.
        :type   conduit: pulp.agent.lib.conduit.Conduit
        :param  binding: A binding to add/update.
          A binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
        :type   binding: dict
        :param  options: Bind options.
        :type   options: dict

        :return: A bind report.
        :rtype:  BindReport
        """
        repo_id = binding['repo_id']
        logger.info('binding to repo %s' % repo_id)

        report = BindReport(repo_id)
        report.set_succeeded()
        return report

    @staticmethod
    def unbind(conduit, repo_id, options):
        """
        Unbind a repository. This is a no-op since the consumer does not need
        to keep any state with regard to bindings.

        :param  conduit: A handler conduit.
        :type   conduit:  pulp.agent.lib.conduit.Conduit
        :param  repo_id: A repository ID.
        :type   repo_id: str
        :param  options: Unbind options.
        :type   options: dict

        :return:    An unbind report.
        :rtype:     BindReport
        """
        report = BindReport(repo_id)
        report.set_succeeded()
        return report

    @staticmethod
    def clean(conduit):
        """
        Clean up. This is a no-op since the consumer does not need
        to keep any state with regard to bindings.

        :param  conduit: A handler conduit.
        :type   conduit: pulp.agent.lib.conduit.Conduit

        :return:    A clean report.
        :rtype:     CleanReport
        """
        report = CleanReport()
        report.set_succeeded()
        return report
