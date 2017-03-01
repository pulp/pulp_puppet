import subprocess
import unittest

import mock
from pulp.agent.lib.report import ContentReport
from pulp_puppet.common import constants

from pulp_puppet.handlers.puppet import ModuleHandler


def mock_puppet_pre33(f):
    return mock.patch.object(ModuleHandler, '_detect_puppet_version',
                             spec_set=ModuleHandler._detect_puppet_version,
                             return_value = (3, 1, 0))(f)


def mock_puppet_post33(f):
    return mock.patch.object(ModuleHandler, '_detect_puppet_version',
                             spec_set=ModuleHandler._detect_puppet_version,
                             return_value = (3, 3, 0))(f)


class ModuleHandlerTest(unittest.TestCase):
    def setUp(self):
        self.handler = ModuleHandler({})
        self.conduit = mock.MagicMock()
        self.conduit.consumer_id = 'consumer1'
        self.conduit.get_consumer_config.return_value = {
            'server': {'host': 'localhost'}
        }


class TestDetectPuppetVersion(ModuleHandlerTest):
    @mock.patch('subprocess.Popen')
    def test_version(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('3.4.2\n', '')

        version = self.handler._detect_puppet_version()

        self.assertEqual(version, (3, 4, 2))

    @mock.patch('subprocess.Popen')
    def test_args(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('3.4.2\n', '')

        self.handler._detect_puppet_version()

        mock_popen.assert_called_once_with(('puppet', '--version'), stdout=subprocess.PIPE)


class TestGenerateForgeURL(ModuleHandlerTest):
    @mock_puppet_pre33
    def test_with_repo_id_pre33(self, mock_detect):
        host = 'localhost'
        result = self.handler._generate_forge_url(self.conduit, host, 'repo1')

        self.assertEqual(result, 'http://.:repo1@%s' % host)

    @mock_puppet_pre33
    def test_without_repo_id_pre33(self, mock_detect):
        host = 'localhost'
        result = self.handler._generate_forge_url(self.conduit, host)

        self.assertEqual(result, 'http://consumer1:.@%s' % host)

    @mock_puppet_post33
    def test_with_repo_id_post33(self, mock_detect):
        host = 'localhost'
        result = self.handler._generate_forge_url(self.conduit, host, 'repo1')

        self.assertEqual(result, 'http://%s/pulp_puppet/forge/repository/repo1' % host)

    @mock_puppet_post33
    def test_without_repo_id_post33(self, mock_detect):
        host = 'localhost'
        result = self.handler._generate_forge_url(self.conduit, host)

        self.assertEqual(result, 'http://%s/pulp_puppet/forge/consumer/consumer1' % host)


class TestInstall(ModuleHandlerTest):
    UNITS = [
        {'author': 'puppetlabs', 'name': 'stdlib', 'version': '3.1.1'},
        {'author': 'puppetlabs', 'name': 'java'},
    ]

    POPEN_OUTPUT = [(
"""notice: Preparing to install into /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Installing -- do not interrupt ...
{"module_name":"puppetlabs-stdlib","module_version":null,"install_dir":"/etc/puppet/modules","result":"success","installed_modules":[{"module":"puppetlabs-stdlib","version":{"vstring":"3.1.1","semver":"v3.1.1"},"action":"install","previous_version":null,"file":"/system/releases/p/puppetlabs/puppetlabs-stdlib-3.1.1.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
""", ''),(
"""notice: Preparing to install into /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Installing -- do not interrupt ...
{"module_name":"puppetlabs-java","module_version":null,"install_dir":"/etc/puppet/modules","result":"success","installed_modules":[{"module":"puppetlabs-java","version":{"vstring":"0.2.0","semver":"v0.2.0"},"action":"install","previous_version":null,"file":"/system/releases/p/puppetlabs/puppetlabs-java-0.2.0.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
""", '')]
    POPEN_STDOUT_ERROR = """notice: Preparing to install into /etc/puppet/modules ...
{"module_name":"puppetlabs-stdlib","module_version":null,"install_dir":"/etc/puppet/modules","error":{"oneline":"'puppetlabs-stdlib' (best) requested; 'puppetlabs-stdlib' (v3.2.0) already installed","multiline":"Could not install module 'puppetlabs-stdlib' (best)\\n  Module 'puppetlabs-stdlib' (v3.2.0) is already installed\\n    Use `puppet module upgrade` to install a different version\\n    Use `puppet module install --force` to re-install only this module"},"result":"failure"}
"""
    @mock_puppet_post33
    def test_no_units(self, mock_version):
        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.install(self.conduit, [], options)

        self.assertTrue(isinstance(report, ContentReport))
        self.assertEqual(report.num_changes, 0)

    @mock_puppet_pre33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_units(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.side_effect = self.POPEN_OUTPUT
        mock_popen.return_value.returncode = 0

        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.install(self.conduit, self.UNITS, options)
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successes), 2)

        mock_popen.assert_any_call(
            ['puppet', 'module', 'install', '--render-as', 'json', '--module_repository',
                'http://consumer1:.@localhost', 'puppetlabs/java'],
            stdout=subprocess.PIPE
        )
        mock_popen.assert_any_call(
            ['puppet', 'module', 'install', '--render-as', 'json', '--module_repository',
             'http://consumer1:.@localhost', '--version', '3.1.1', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )

        # make sure the keys are present, and that the reports each have some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(successes.get('puppetlabs/java'))
        self.assertTrue(successes.get('puppetlabs/stdlib'))

    @mock_puppet_pre33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_units_and_repo_id(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.side_effect = self.POPEN_OUTPUT
        mock_popen.return_value.returncode = 0
        options = {
            constants.FORGE_HOST: 'localhost',
            constants.REPO_ID_OPTION: 'repo1'
        }

        report = self.handler.install(self.conduit, self.UNITS, options)

        mock_popen.assert_any_call(
            ['puppet', 'module', 'install', '--render-as', 'json', '--module_repository',
             'http://.:repo1@localhost', 'puppetlabs/java'],
            stdout=subprocess.PIPE
        )
        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 2)

    @mock_puppet_pre33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_error(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.return_value = (self.POPEN_STDOUT_ERROR, '')
        mock_popen.return_value.returncode = 1

        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.install(self.conduit, self.UNITS[:1], options)
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(successes), 0)

        mock_popen.assert_called_once_with(
            ['puppet', 'module', 'install', '--render-as', 'json', '--module_repository',
             'http://consumer1:.@localhost', '--version', '3.1.1', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(errors.get('puppetlabs/stdlib'))


class TestUpdate(ModuleHandlerTest):
    UNITS = [
        {'author': 'puppetlabs', 'name': 'stdlib'},
    ]

    POPEN_STDOUT = """notice: Preparing to upgrade 'puppetlabs-stdlib' ...
notice: Found 'puppetlabs-stdlib' (v3.1.1) in /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Upgrading -- do not interrupt ...
{"module_name":"puppetlabs-stdlib","installed_version":"v3.1.1","requested_version":"latest","result":"success","base_dir":"/etc/puppet/modules","affected_modules":[{"module":"puppetlabs-stdlib","version":{"vstring":"3.2.0","semver":"v3.2.0"},"action":"upgrade","previous_version":"3.1.1","file":"/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
"""
    POPEN_STDOUT_ERROR = """notice: Preparing to uninstall 'puppetlabs-stdlib' ...
{"module_name":"puppetlabs-stdlib","requested_version":null,"error":{"oneline":"Could not uninstall 'puppetlabs-stdlib'; module is not installed","multiline":"Could not uninstall module 'puppetlabs-stdlib'\\n  Module 'puppetlabs-stdlib' is not installed"},"result":"failure"}
"""
    @mock_puppet_post33
    def test_no_units(self, mock_version):
        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.update(self.conduit, [], options)

        self.assertTrue(isinstance(report, ContentReport))
        self.assertEqual(report.num_changes, 0)

    @mock_puppet_post33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_unit(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.return_value = (self.POPEN_STDOUT, '')
        mock_popen.return_value.returncode = 0

        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.update(self.conduit, self.UNITS, options)
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successes), 1)

        mock_popen.assert_called_once_with(
            ['puppet', 'module', 'upgrade', '--render-as', 'json', '--module_repository',
            'http://localhost/pulp_puppet/forge/consumer/consumer1', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(successes.get('puppetlabs/stdlib'))

    @mock_puppet_post33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_unit_and_repo_id(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.return_value = (self.POPEN_STDOUT, '')
        mock_popen.return_value.returncode = 0
        options = {
            constants.FORGE_HOST: 'localhost',
            constants.REPO_ID_OPTION: 'repo1'
        }

        report = self.handler.update(self.conduit, self.UNITS, options)

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)

        mock_popen.assert_called_once_with(
            ['puppet', 'module', 'upgrade', '--render-as', 'json', '--module_repository',
             'http://localhost/pulp_puppet/forge/repository/repo1', 'puppetlabs/stdlib'],
              stdout=subprocess.PIPE
        )

    @mock_puppet_post33
    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_error(self, mock_popen, mock_version):
        mock_popen.return_value.communicate.return_value = (self.POPEN_STDOUT_ERROR, '')
        mock_popen.return_value.returncode = 1

        options = {constants.FORGE_HOST: 'localhost'}
        report = self.handler.update(self.conduit, self.UNITS, options)
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(successes), 0)

        mock_popen.assert_called_once_with(
            ['puppet', 'module', 'upgrade', '--render-as', 'json', '--module_repository',
             'http://localhost/pulp_puppet/forge/consumer/consumer1', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(errors.get('puppetlabs/stdlib'))


class TestUninstall(ModuleHandlerTest):
    UNITS = [
        {'author': 'puppetlabs', 'name': 'stdlib'},
        {'author': 'puppetlabs', 'name': 'java'},
    ]

    # one failed attempt, then two successful attempts
    POPEN_OUTPUT = (
        ('\x1b[0;36mnotice: Preparing to uninstall \'puppetlabd-stdlib\' ...\x1b[0m\n{"module_name":"puppetlabd-stdlib","requested_version":null,"error":{"oneline":"Could not uninstall \'puppetlabd-stdlib\'; module is not installed","multiline":"Could not uninstall module \'puppetlabd-stdlib\'\\n  Module \'puppetlabd-stdlib\' is not installed"},"result":"failure"}\n',
            ''),
        ("""notice: Preparing to uninstall 'puppetlabs-java' ...
{"module_name":"puppetlabs-java","requested_version":null,"affected_modules":["Module java(/etc/puppet/modules/java)"],"result":"success"}
""", ''),
    ("""notice: Preparing to uninstall 'puppetlabs-stdlib' ...
{"module_name":"puppetlabs-stdlib","requested_version":null,"affected_modules":["Module stdlib(/etc/puppet/modules/stdlib)"],"result":"success"}
""", ''))

    def test_no_units(self):
        report = self.handler.uninstall(self.conduit, [], {})

        self.assertTrue(isinstance(report, ContentReport))
        self.assertEqual(report.num_changes, 0)

    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_units(self, mock_popen):
        mock_popen.return_value.communicate.return_value = self.POPEN_OUTPUT[2]
        mock_popen.return_value.returncode = 0

        report = self.handler.uninstall(self.conduit, self.UNITS[:1], {})
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successes), 1)

        mock_popen.assert_called_once_with(
            ['puppet', 'module', 'uninstall', '--render-as', 'json', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(successes.get('puppetlabs/stdlib'))

    @mock.patch('subprocess.Popen', autospec=True)
    def test_with_error(self, mock_popen):
        mock_popen.return_value.communicate.return_value = self.POPEN_OUTPUT[0]
        mock_popen.return_value.returncode = 1

        report = self.handler.uninstall(self.conduit, self.UNITS[:1], {})
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(successes), 0)

        mock_popen.assert_any_call(
            ['puppet', 'module', 'uninstall', '--render-as', 'json', 'puppetlabs/stdlib'],
            stdout=subprocess.PIPE
        )
        self.assertEqual(mock_popen.call_count, 2)

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(errors.get('puppetlabs/stdlib'))

    @mock.patch('subprocess.Popen', autospec=True)
    def test_retry(self, mock_popen):
        # simulates a dependency error where "java" must be uninstalled before
        # "stdlib". So the first pass will fail to uninstall "stdlib", succeed
        # at uninstalling "java", and then the second pass will retry "stdlib"
        # and succeed.

        # these two classes are necessary to have the "returncode" attribute of
        # the mock Popen object have different values for successive calls.
        class ReturnCode(object):
            def __init__(self):
                self.returncode = 1

            def __get__(self, obj, objtype):
                ret = self.returncode
                self.returncode = 0
                return ret

        class ReturnValue(mock.MagicMock):
            returncode = ReturnCode()

        mock_popen.return_value = ReturnValue()
        mock_popen.return_value.communicate.side_effect = self.POPEN_OUTPUT

        report = self.handler.uninstall(self.conduit, self.UNITS, {})
        successes = report.details['successes']
        errors = report.details['errors']

        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successes), 2)

        self.assertEqual(mock_popen.call_count, 3)

        # make sure the key is present, and that the report has some
        # content. Don't pay much attention to the content, since it is generated
        # by the puppet module tool, which is out of our control.
        self.assertTrue(successes.get('puppetlabs/stdlib'))
        self.assertTrue(successes.get('puppetlabs/java'))


class TestPerformOperation(ModuleHandlerTest):
    UNITS = [
        {'author': 'puppetlabs', 'name': 'stdlib', 'version': '3.1.1'},
        {'author': 'puppetlabs', 'name': 'java'},
    ]
    POPEN_OUTPUT = [(
"""notice: Preparing to install into /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Installing -- do not interrupt ...
{"module_name":"puppetlabs-stdlib","module_version":null,"install_dir":"/etc/puppet/modules","result":"success","installed_modules":[{"module":"puppetlabs-stdlib","version":{"vstring":"3.1.1","semver":"v3.1.1"},"action":"install","previous_version":null,"file":"/system/releases/p/puppetlabs/puppetlabs-stdlib-3.1.1.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
""", ''),(
"""notice: Preparing to install into /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Installing -- do not interrupt ...
{"module_name":"puppetlabs-java","module_version":null,"install_dir":"/etc/puppet/modules","result":"success","installed_modules":[{"module":"puppetlabs-java","version":{"vstring":"0.2.0","semver":"v0.2.0"},"action":"install","previous_version":null,"file":"/system/releases/p/puppetlabs/puppetlabs-java-0.2.0.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
""", '')]

    @mock.patch('subprocess.Popen', autospec=True)
    def test_arguments_set(self, mock_popen):
        mock_popen.return_value.communicate.side_effect = self.POPEN_OUTPUT
        mock_popen.return_value.returncode = 0

        successes, errors, num_changes = self.handler._perform_operation('upgrade', self.UNITS, 'foo', True, 'bar')

        # make sure there are as many calls as there are units
        self.assertEqual(len(mock_popen.call_args_list), len(self.UNITS))

        # make sure every call contains the arguments that should be included
        for call in mock_popen.call_args_list:
            self.assertTrue('--modulepath' and '--ignore-dependencies' and '--module_repository' in call[0][0])

    @mock.patch('subprocess.Popen', autospec=True)
    def test_os_error(self, mock_popen):
        # this probably means the "puppet module" tool isn't installed. This test
        # makes sure that this is caught the first time, and remaining units are
        # not attempted.
        mock_popen.side_effect = OSError

        successes, errors, num_changes = self.handler._perform_operation('upgrade', self.UNITS)

        self.assertEqual(len(successes), 0)
        # just one error, despite having 2 units, because it is designed to quit
        # after the first OSError
        self.assertEqual(len(errors), 1)
        self.assertEqual(num_changes, 0)

    @mock.patch.object(ModuleHandler, '_clean_successful_reports')
    @mock.patch('subprocess.Popen', autospec=True)
    def test_calls_clean(self, mock_popen, mock_clean):
        mock_popen.return_value.communicate.side_effect = self.POPEN_OUTPUT
        mock_popen.return_value.returncode = 0

        successes, errors, num_changes = self.handler._perform_operation('upgrade', self.UNITS)

        self.assertEqual(len(successes), 2)
        self.assertEqual(mock_clean.call_count, 1)


class TestInterpretReport(ModuleHandlerTest):
    POPEN_STDOUT = """notice: Preparing to upgrade 'puppetlabs-stdlib' ...
notice: Found 'puppetlabs-stdlib' (v3.1.1) in /etc/puppet/modules ...
notice: Downloading from http://forge.puppetlabs.com ...
notice: Upgrading -- do not interrupt ...
{"module_name":"puppetlabs-stdlib","installed_version":"v3.1.1","requested_version":"latest","result":"success","base_dir":"/etc/puppet/modules","affected_modules":[{"module":"puppetlabs-stdlib","version":{"vstring":"3.2.0","semver":"v3.2.0"},"action":"upgrade","previous_version":"3.1.1","file":"/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz","path":"/etc/puppet/modules","dependencies":[]}]}
"""

    def test_success(self):
        result = self.handler._interpret_operation_report(self.POPEN_STDOUT, 'upgrade', 'puppetlabs/stdlib')

        self.assertEqual(result.get('module_name'), 'puppetlabs-stdlib')

    def test_index_error(self):
        result = self.handler._interpret_operation_report('', 'upgrade', 'puppetlabs/stdlib')

        self.assertEqual(result, {})

    def test_value_error(self):
        result = self.handler._interpret_operation_report('\nnot valid json\n', 'upgrade', 'puppetlabs/stdlib')

        self.assertEqual(result, {})


# flake8: noqa
class TestCleanSuccessful(ModuleHandlerTest):
    def setUp(self):
        super(TestCleanSuccessful, self).setUp()
        self.sample = [{'install_dir': '/home/someuser/.puppet/modules',
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
                {'action': 'upgrade',
                 'dependencies': [],
                 'file': '/system/releases/p/puppetlabs/puppetlabs-stdlib-3.2.0.tar.gz',
                 'module': 'puppetlabs-stdlib',
                 'path': '/home/someuser/.puppet/modules',
                 'previous_version': '1.0.0',
                 'version': {'semver': 'v3.2.0', 'vstring': '3.2.0'}}],
               'file': '/system/releases/b/branan/branan-minecraft-1.0.0.tar.gz',
               'module': 'branan-minecraft',
               'path': '/home/someuser/.puppet/modules',
               'previous_version': None,
               'version': {'semver': 'v1.0.0', 'vstring': '1.0.0'}}],
             'module_name': 'branan-minecraft',
             'module_version': None,
             'result': 'success'}]

    def test_normal(self):
        self.handler._clean_successful_reports(self.sample, 'install')

        self.assertEqual(len(self.sample), 1)
        report = self.sample[0]
        self.assertTrue('module_version' not in report)

        installed_modules = report['installed_modules']
        self.assertEqual(len(installed_modules), 1)
        installed_module = installed_modules[0]
        for attr in ['action', 'file', 'path', 'previous_version', 'result']:
            self.assertTrue(attr not in installed_module)
        deps = installed_module['dependencies']
        for attr in ['action', 'dependencies', 'file', 'path', 'previous_version']:
            self.assertTrue(attr not in deps[0])

        # make sure it leaves this one, since it is a different action than
        # the primary one, which was an install
        self.assertEqual(deps[2].get('action'), 'upgrade')
        # This should also be present for upgrades
        self.assertEqual(deps[2].get('previous_version'), '1.0.0')

        # make sure the basic info is still present
        for dep in deps:
            for attr in ['module', 'version']:
                self.assertTrue(attr in dep)

    def test_no_data(self):
        self.handler._clean_successful_reports([], 'install')

    def test_empty_report(self):
        # the clean is meant to help improve the human-readability, but it should
        # not fail if the keys it looks for are not present.
        self.handler._clean_successful_reports([{}], 'install')

    def test_uninstall_report(self):
        output = [{'affected_modules': ['Module minecraft(/etc/puppet/modules/minecraft)'],
                  'module_name': 'branan-minecraft',
                  'requested_version': None,
                  'result': 'success'},
                  {'affected_modules': ['Module s3file(/etc/puppet/modules/s3file)'],
                   'module_name': 'branan-s3file',
                   'requested_version': None,
                   'result': 'success'}]

        self.handler._clean_successful_reports(output, 'uninstall')

        for attr in ['requested_version', 'result']:
            self.assertTrue(attr not in output[0])
