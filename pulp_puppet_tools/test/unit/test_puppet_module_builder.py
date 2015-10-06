import os

from unittest import TestCase
from optparse import OptionParser, OptionGroup, Values
from hashlib import sha256

from mock import Mock, patch

from pulp_puppet.tools import puppet_module_builder as builder


class TestOptions(TestCase):

    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser')
    def test_parser(self, mock_parser):
        parser = OptionParser()
        parser._get_args = Mock(return_value=[])
        mock_parser.return_value = parser

        # test

        builder.get_options()

        # validation

        mock_parser.assert_called_with(usage=builder.USAGE, description=builder.DESCRIPTION)

    @patch('pulp_puppet.tools.puppet_module_builder.OptionGroup')
    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser')
    def test_options(self, mock_parser, mock_group):
        parser = OptionParser()
        mock_parser.return_value = parser
        parser.add_option = Mock(side_effect=parser.add_option)
        parser.add_option_group = Mock(side_effect=parser.add_option_group)
        parser._get_args = Mock(return_value=[])

        group = OptionGroup(parser, '')
        mock_group.return_value = group
        group.add_option = Mock(side_effect=group.add_option)

        # test

        builder.get_options()

        # validation

        parser.add_option.assert_any_call(
            '-w', '--working-dir', dest='working_dir', help=builder.WORKING_DIR)
        parser.add_option.assert_any_call(
            '-o', '--output-dir', dest='output_dir', help=builder.OUTPUT_DIR)
        parser.add_option.assert_any_call(
            '-c', '--clean', default=False, action='store_true', help=builder.CLEAN)

        parser.add_option.assert_any_call('-p', '--path', help=builder.PATH)
        parser.add_option_group.assert_called_with(group)

        group.add_option.assert_any_call('-u', '--url', help=builder.URL)
        group.add_option.assert_any_call('-b', '--branch', help=builder.BRANCH)
        group.add_option.assert_any_call('-t', '--tag', help=builder.TAG)

    @patch('sys.exit')
    @patch('sys.stdout.write')
    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser.parse_args')
    def test_validate_path(self, mock_parse, mock_stdout, mock_exit):
        parsed_options = {
            'working_dir': None,
            'output_dir': None,
            'path': '/',
            'branch': None,
            'tag': None
        }

        mock_parse.return_value = (Values(defaults=parsed_options), [])

        # test

        builder.get_options()

        # validation

        mock_stdout.assert_any_call(builder.BAD_PATH)
        mock_exit.assert_called_with(os.EX_USAGE)

    @patch('sys.exit')
    @patch('sys.stdout.write')
    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser.parse_args')
    def test_validate_both_branch_and_tag(self, mock_parse, mock_stdout, mock_exit):
        parsed_options = {
            'working_dir': None,
            'output_dir': None,
            'path': None,
            'branch': 'br',
            'tag': 'tg'
        }

        mock_parse.return_value = (Values(defaults=parsed_options), [])

        # test

        builder.get_options()

        # validation

        mock_stdout.assert_any_call(builder.BAD_BRANCH_AND_TAG)
        mock_exit.assert_called_with(os.EX_USAGE)

    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser.parse_args')
    def test_expanded_paths(self, mock_parse):
        parsed_options = {
            'working_dir': '~/',
            'output_dir': '~/',
            'path': None,
            'branch': None,
            'tag': None
        }

        mock_parse.return_value = (Values(defaults=parsed_options), [])

        # test

        options = builder.get_options()

        # validation

        self.assertEqual(options.working_dir, os.path.expanduser('~/'))
        self.assertEqual(options.output_dir, os.path.expanduser('~/'))

    @patch('pulp_puppet.tools.puppet_module_builder.OptionParser.parse_args')
    def test_defaulting(self, mock_parse):
        parsed_options = {
            'working_dir': None,
            'output_dir': None,
            'path': None,
            'branch': None,
            'tag': None
        }

        # working_dir defaulted to CWD
        mock_parse.return_value = (Values(defaults=parsed_options), [])
        options = builder.get_options()
        self.assertEqual(options.working_dir, os.getcwd())

        # working_dir defaulted to args[0]
        mock_parse.return_value = (Values(defaults=parsed_options), ['/tmp'])
        options = builder.get_options()
        self.assertEqual(options.working_dir, '/tmp')

        # output_dir defaulted to working_dir
        parsed_options['working_dir'] = '/abc'
        mock_parse.return_value = (Values(defaults=parsed_options), ['/tmp'])
        options = builder.get_options()
        self.assertEqual(options.output_dir, '/abc')


class TestClean(TestCase):

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_clean(self, mock_shell):
        parsed_options = {
            'url': 'http://',
            'working_dir': '/tmp/working',
            'clean': True
        }

        options = Values(defaults=parsed_options)

        # test

        builder.clean(options)

        # validation

        path = os.path.join(options.working_dir, os.path.basename(options.url))
        mock_shell.assert_called_with('rm -rf %s' % path)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_clean_not_requested(self, mock_shell):
        parsed_options = {
            'url': 'http://',
            'working_dir': '/tmp/working',
            'clean': False
        }

        options = Values(defaults=parsed_options)

        # test

        builder.clean(options)

        # validation

        self.assertFalse(mock_shell.called)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_clean_no_url(self, mock_shell):
        parsed_options = {
            'url': None,
            'working_dir': '/tmp/working',
            'clean': True
        }

        options = Values(defaults=parsed_options)

        # test

        builder.clean(options)

        # validation

        self.assertFalse(mock_shell.called)


class TestBuilder(TestCase):

    @patch('pulp_puppet.tools.puppet_module_builder.build_manifest')
    @patch('pulp_puppet.tools.puppet_module_builder.build_puppet_modules')
    @patch('pulp_puppet.tools.puppet_module_builder.git_checkout')
    @patch('pulp_puppet.tools.puppet_module_builder.set_origin')
    @patch('pulp_puppet.tools.puppet_module_builder.git_clone')
    @patch('pulp_puppet.tools.puppet_module_builder.chdir')
    @patch('pulp_puppet.tools.puppet_module_builder.clean')
    @patch('pulp_puppet.tools.puppet_module_builder.get_options')
    def test_main(self,
                  mock_get_options,
                  mock_clean,
                  mock_chdir,
                  mock_git_clone,
                  mock_set_origin,
                  mock_git_checkout,
                  mock_build_modules,
                  mock_build_manifest):

        parsed_options = {
            'working_dir': '/tmp/working',
            'output_dir': '/tmp/output',
            'path': None
        }

        options = Values(defaults=parsed_options)

        mock_get_options.return_value = options

        # test

        builder.main()

        # validation

        mock_get_options.assert_called_with()
        mock_clean.assert_called_with(options)
        mock_chdir.assert_any_call(options.working_dir)
        mock_git_clone.assert_called_with(options)
        mock_set_origin.assert_called_with(options)
        mock_git_checkout.assert_called_with(options)
        mock_build_modules.assert_called_with(options)
        mock_build_manifest.assert_called_with(options)

        self.assertEqual(mock_clean.call_count, 2)

    @patch('os.listdir')
    @patch('os.path.getsize')
    @patch('__builtin__.open')
    @patch('pulp_puppet.tools.puppet_module_builder.digest')
    @patch('pulp_puppet.tools.puppet_module_builder.chdir')
    def test_build_manifest(self, mock_chdir, mock_digest, mock_open, mock_getsize, mock_listdir):
        parsed_options = {
            'output_dir': '/tmp/output',
        }

        options = Values(defaults=parsed_options)

        files = [
            'file_1%s' % builder.ARCHIVE_SUFFIX,
            'file_2%s' % builder.ARCHIVE_SUFFIX,
            'file_3',  # not a module
        ]

        digests = ['hash_1', 'hash_2']
        mock_digest.side_effect = digests
        mock_listdir.return_value = files
        mock_getsize.side_effect = [10, 20]

        manifest = []
        mock_fp = Mock()
        mock_fp.write = manifest.append
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp

        # test

        builder.build_manifest(options)

        # validation

        _manifest = [
            'file_1.tar.gz',
            ',hash_1',
            ',10\n',
            'file_2.tar.gz',
            ',hash_2',
            ',20\n'
        ]

        mock_open.assert_called_with('PULP_MANIFEST', 'w+')
        mock_chdir.assert_called_with(os.getcwd())
        self.assertEqual(manifest, _manifest)

    @patch('__builtin__.open')
    def test_build_digest(self, mock_open):
        data = 'puppet-module'
        mock_fp = Mock()
        mock_fp.read = Mock(return_value=data)
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp

        # test

        path = '/tmp/abc'
        digest = builder.digest(path)

        # validation

        h = sha256()
        h.update(data)

        mock_open.assert_called_with(path)
        self.assertEqual(digest, h.hexdigest())

    @patch('pulp_puppet.tools.puppet_module_builder.publish_module')
    @patch('pulp_puppet.tools.puppet_module_builder.find_modules')
    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_build_modules(self, mock_shell, mock_find, mock_publish):
        parsed_options = {
            'output_dir': '/tmp/output',
        }

        options = Values(defaults=parsed_options)

        module_paths = ['path_1', 'path_2']
        mock_find.return_value = module_paths

        # test

        builder.build_puppet_modules(options)

        # validation

        command = 'puppet module build %s'

        mock_find.assert_called_with()
        mock_shell.assert_any_call(command % module_paths[0])
        mock_shell.assert_any_call(command % module_paths[1])

        mock_publish.assert_any_call('%s/pkg' % module_paths[0], parsed_options['output_dir'])
        mock_publish.assert_any_call('%s/pkg' % module_paths[1], parsed_options['output_dir'])

    @patch('os.listdir')
    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_publish_module(self, mock_shell, mock_listdir):
        module_path = '/tmp/module/pkg'
        output_dir = '/tmp/output'

        files = [
            'path_1%s' % builder.ARCHIVE_SUFFIX,
            'path_2%s' % builder.ARCHIVE_SUFFIX,
            'path_3',  # not a module
        ]

        mock_listdir.return_value = files

        # test

        builder.publish_module(module_path, output_dir)

        # validation

        mock_shell.assert_any_call('mkdir -p %s' % output_dir)
        mock_shell.assert_any_call('cp %s %s' % (os.path.join(module_path, files[0]), output_dir))
        mock_shell.assert_any_call('cp %s %s' % (os.path.join(module_path, files[1]), output_dir))

        self.assertEqual(mock_shell.call_count, 3)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_find_modules(self, mock_shell):
        mock_shell.return_value = (0, """
            module_1/Modulefile
            module_1/metadata.json
            nested/module_2/Modulefile
            nested/module_3/metadata.json
            nested/module_3/pkg/module_3/metadata.json
            """)

        # test

        modules = builder.find_modules()

        # validation
        self.assertEquals(2, mock_shell.call_count)
        self.assertEqual(sorted(list(modules)), sorted(['module_1', 'nested/module_2', 'nested/module_3']))

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_checkout_branch(self, mock_shell):
        parsed_options = {
            'origin': 'git://',
            'branch': 'mybranch',
            'tag': None,
        }

        options = Values(defaults=parsed_options)

        # test

        builder.git_checkout(options)

        # validation

        mock_shell.assert_any_call('git fetch')
        mock_shell.assert_any_call('git fetch --tags')
        mock_shell.assert_any_call('git checkout %s' % options.branch)
        mock_shell.assert_any_call('git pull')

        self.assertEqual(mock_shell.call_count, 4)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_checkout_tag(self, mock_shell):
        parsed_options = {
            'origin': 'git://',
            'branch': None,
            'tag': 'mytag',
        }

        options = Values(defaults=parsed_options)

        # test

        builder.git_checkout(options)

        # validation

        mock_shell.assert_any_call('git fetch')
        mock_shell.assert_any_call('git fetch --tags')
        mock_shell.assert_any_call('git checkout %s' % options.tag)

        self.assertEqual(mock_shell.call_count, 3)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_checkout_not_in_repository(self, mock_shell):
        options = Values(defaults={'origin': None})

        # test

        builder.git_checkout(options)

        # validation

        self.assertFalse(mock_shell.called)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_clone_no_url(self, mock_shell):
        parsed_options = {
            'url': None
        }

        options = Values(defaults=parsed_options)

        # test

        builder.git_clone(options)

        # validation

        self.assertEqual(mock_shell.call_count, 0)

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_clone_override_path(self, mock_shell):
        parsed_options = {
            'url': 'git://puppet/project.git',
            'path': None
        }

        options = Values(defaults=parsed_options)

        # test

        builder.git_clone(options)

        # validation

        mock_shell.assert_called_with('git clone --recursive %s' % options.url)

        self.assertEqual(mock_shell.call_count, 1)
        self.assertEqual(options.path, 'project')

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_git_clone(self, mock_shell):
        parsed_options = {
            'url': 'git://puppet/project.git',
            'path': 'puppet/modules'
        }

        options = Values(defaults=parsed_options)

        # test

        builder.git_clone(options)

        # validation

        mock_shell.assert_called_with('git clone --recursive %s' % options.url)

        self.assertEqual(mock_shell.call_count, 1)
        self.assertEqual(options.path, 'puppet/modules')

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_set_origin(self, mock_shell):
        options = Values()

        git_show = """
            * remote origin
              Fetch URL: git@github.com:pulp/pulp_puppet.git
              Push  URL: git@github.com:pulp/pulp_puppet.git
              HEAD branch: (not queried)
              Remote branches: (status not queried)
                branch_1
              Local branches configured for 'git pull':
                branch_2
              Local ref configured for 'git push' (status not queried):
                (matching) pushes to (matching)
            """

        mock_shell.side_effect = [
            (0, None),
            (0, git_show)
        ]

        # test

        builder.set_origin(options)

        # validation

        mock_shell.assert_any_call('git status', False)
        mock_shell.assert_any_call('git remote show -n origin')

        self.assertEqual(options.origin, 'git@github.com:pulp/pulp_puppet.git')

    @patch('pulp_puppet.tools.puppet_module_builder.shell')
    def test_set_origin_outside_repository(self, mock_shell):
        options = Values()
        mock_shell.return_value = (1, None)

        # test

        builder.set_origin(options)

        # validation

        mock_shell.assert_any_call('git status', False)

        self.assertTrue(options.origin is None)

    @patch('pulp_puppet.tools.puppet_module_builder.Popen')
    def test_shell(self, mock_popen):
        p = Mock()
        p.wait = Mock(return_value=0)
        p.stdout = Mock()
        p.stdout.read = Mock(return_value='result')
        mock_popen.return_value = p

        # test

        command = 'ls -Fal'
        status, output = builder.shell(command)

        # validate

        mock_popen.assert_called_with(command.split(), stdout=builder.PIPE, stderr=builder.PIPE)

        self.assertEqual(status, 0)
        self.assertEqual(output, p.stdout.read())

    @patch('sys.exit')
    @patch('pulp_puppet.tools.puppet_module_builder.Popen')
    def test_shell_failed(self, mock_popen, mock_exit):
        p = Mock()
        p.wait = Mock(return_value=1)
        p.stdout = Mock()
        p.stdout.read = Mock(return_value='')
        p.stderr = Mock()
        p.stderr.read = Mock(return_value='No such directory')
        mock_popen.return_value = p

        # test

        command = 'ls -Fal'
        status, output = builder.shell(command)

        # validate

        mock_popen.assert_called_with(command.split(), stdout=builder.PIPE, stderr=builder.PIPE)
        mock_exit.assert_called_with(1)

        self.assertEqual(status, 1)
        self.assertEqual(output, '')

    @patch('sys.exit')
    @patch('pulp_puppet.tools.puppet_module_builder.Popen')
    def test_shell_failed_no_exit(self, mock_popen, mock_exit):
        p = Mock()
        p.wait = Mock(return_value=1)
        p.stdout = Mock()
        p.stdout.read = Mock(return_value='')
        p.stderr = Mock()
        p.stderr.read = Mock(return_value='No such directory')
        mock_popen.return_value = p

        # test

        command = 'ls -Fal'
        status, output = builder.shell(command, False)

        # validate

        mock_popen.assert_called_with(command.split(), stdout=builder.PIPE, stderr=builder.PIPE)

        self.assertEqual(status, 1)
        self.assertEqual(output, '')
        self.assertFalse(mock_exit.called)

    @patch('os.chdir')
    def test_chdir(self, mock_chdir):
        builder.chdir(None)
        self.assertFalse(mock_chdir.called)

        path = '/tmp'
        builder.chdir(path)
        mock_chdir.assert_called_with(path)
