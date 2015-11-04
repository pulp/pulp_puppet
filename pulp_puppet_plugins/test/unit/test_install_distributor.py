from cStringIO import StringIO
import os
import tarfile
import unittest
import tempfile
import shutil
import errno

import mock
from pulp.devel.unit.util import touch
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, PublishReport

from pulp_puppet.common import constants
from pulp_puppet.plugins.db.models import Module
from pulp_puppet.plugins.distributors import installdistributor


class TestEntryPoint(unittest.TestCase):
    def test_everything(self):
        """everything isn't much"""
        plugin_class, config = installdistributor.entry_point()

        self.assertTrue(plugin_class is installdistributor.PuppetModuleInstallDistributor)
        # there is never a global config for this distributor
        self.assertEqual(config, {})


@mock.patch('tarfile.TarInfo.fromtarfile')
class TestNormalizingTarInfo(unittest.TestCase):
    def setUp(self):
        self.tarfile = mock.MagicMock()
        self.tarinfo = tarfile.TarInfo(name='foo')
        self.tarinfo.uid = 1000
        self.tarinfo.gid = 1000
        self.tarinfo.type = tarfile.REGTYPE

    def test_resets_uid(self, mock_fromtarfile):
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.uid, 0)

    def test_resets_gid(self, mock_fromtarfile):
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.gid, 0)

    def test_adds_min_file_perms(self, mock_fromtarfile):
        self.tarinfo.mode = 0
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.mode, int('0644', base=8))

    def test_preserve_extra_file_perms(self, mock_fromtarfile):
        self.tarinfo.mode = int('0700', base=8)
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.mode, int('0744', base=8))

    def test_adds_min_dir_perms(self, mock_fromtarfile):
        self.tarinfo.mode = 0
        self.tarinfo.type = tarfile.DIRTYPE
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.mode, int('0755', base=8))

    def test_preserve_extra_dir_perms(self, mock_fromtarfile):
        self.tarinfo.mode = int('0770', base=8)
        self.tarinfo.type = tarfile.DIRTYPE
        mock_fromtarfile.return_value = self.tarinfo

        ret = installdistributor.NormalizingTarInfo.fromtarfile(self.tarfile)

        self.assertEqual(ret.mode, int('0775', base=8))


class TestValidateConfig(unittest.TestCase):
    def setUp(self):
        self.distributor = installdistributor.PuppetModuleInstallDistributor()
        self.repo = Repository('repo1', '', {})

    def test_not_present(self):
        config = PluginCallConfiguration({}, {})

        result, message = self.distributor.validate_config(self.repo, config, [])

        self.assertTrue(result)

    def test_relative_path(self):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: 'a/b/c'})

        result, message = self.distributor.validate_config(self.repo, config, [])

        self.assertFalse(result)
        self.assertTrue(len(message) > 0)

    def test_with_permission(self):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: '/tmp'})

        result, message = self.distributor.validate_config(self.repo, config, [])

        self.assertTrue(result)


class TestPublishRepo(unittest.TestCase):
    def setUp(self):
        self.distributor = installdistributor.PuppetModuleInstallDistributor()
        self.puppet_dir = '/opt/my/modules/'
        self.repo = Repository('repo1', '', repo_obj=mock.MagicMock())
        self.conduit = RepoPublishConduit('repo1', self.distributor.metadata()['id'])
        self.uk1 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.2.0'}
        self.uk2 = {'author': 'puppetlabs', 'name': 'java', 'version': '1.3.1'}
        self.units = [
            Module(_storage_path='/a/b/x', **self.uk1),
            Module(_storage_path='/a/b/y', **self.uk2)
        ]
        self.conduit.get_units = mock.MagicMock(return_value=self.units, spec_set=self.conduit.get_units)

    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_move_to_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_rename_directory',
                       return_value=None)
    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_check_for_unsafe_archive_paths',
                       return_value=None)
    def test_workflow(self, mock_check_paths, mock_clear, mock_open, mock_rename,
                      mock_move, mock_create_tmp_dir, mock_mkdir, mock_find_units):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_open.return_value.getnames.return_value = ['a/b', 'a/c']
        mock_find_units.return_value = self.units

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        mock_mkdir.assert_called_once_with(self.puppet_dir)
        mock_create_tmp_dir.assert_called_once_with(self.puppet_dir)

        self.assertTrue(isinstance(report, PublishReport))
        self.assertTrue(report.success_flag)
        self.assertEqual(len(report.details['errors']), 0)
        self.assertEqual(len(report.details['success_unit_keys']), 2)
        self.assertTrue(self.uk1 in report.details['success_unit_keys'])
        self.assertTrue(self.uk2 in report.details['success_unit_keys'])

        self.assertEqual(mock_open.call_count, 2)
        mock_open.assert_any_call(self.units[0]._storage_path,
                                  tarinfo=installdistributor.NormalizingTarInfo)
        mock_open.assert_any_call(self.units[1]._storage_path,
                                  tarinfo=installdistributor.NormalizingTarInfo)

        self.assertEqual(mock_rename.call_count, 2)

        mock_find_units.assert_called_once_with(self.repo.repo_obj, yield_content_unit=True)
        mock_mkdir.assert_called_once_with(self.puppet_dir)
        mock_clear.assert_called_once_with(self.puppet_dir)
        mock_check_paths.assert_called_once_with(self.units, self.puppet_dir)

        self.assertEqual(mock_move.call_count, 1)

    def test_no_destination(self):
        """this one should fail very early since the destination is missing"""
        config = PluginCallConfiguration({}, {})

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['errors']), 0)
        self.assertEqual(len(report.details['success_unit_keys']), 0)

    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    def test_duplicate_unit_names(self, mock_find):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        uk3 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.3.1'}
        unit3 = Module(_storage_path='/a/b/y', **uk3)
        self.units.append(unit3)
        mock_find.return_value = self.units

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['errors']), 2)
        self.assertTrue(report.summary.find('duplicate') >= 0)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_archive_paths_are_safe',
                       return_value=False)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    def test_unsafe_paths(self, mock_clear, mock_open, mock_find_units, mock_safe):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_find_units.return_value = self.units

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['errors']), 2)
        self.assertTrue(report.details['errors'][0][0] in [self.uk1, self.uk2])
        self.assertTrue(report.details['errors'][1][0] in [self.uk1, self.uk2])
        self.assertEqual(len(report.details['success_unit_keys']), 0)
        self.assertTrue(mock_safe.call_count > 0)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    def test_cannot_create_tmp_dir(self, mock_find_units, mock_mkdir, mock_create_tmp_dir):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_find_units.return_value = []
        mock_create_tmp_dir.side_effect = OSError

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['success_unit_keys']), 0)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_move_to_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    def test_no_units(self, mock_clear, mock_get_units, mock_mkdir, mock_create_tmp_dir,
                      mock_move):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_get_units.return_value = []

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertTrue(report.success_flag)
        self.assertEqual(len(report.details['errors']), 0)
        self.assertEqual(len(report.details['success_unit_keys']), 0)

        # we still need to clear the destination
        mock_clear.assert_called_once_with(self.puppet_dir)
        mock_mkdir.assert_called_once_with(self.puppet_dir)
        mock_create_tmp_dir.assert_called_once_with(self.puppet_dir)
        mock_move.assert_called_once_with(mock_create_tmp_dir.return_value, self.puppet_dir)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_check_for_unsafe_archive_paths',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    def test_cannot_extract_tarballs(self, mock_find_units, mock_clear, mock_check, mock_open,
                                     mock_mkdir, mock_create_tmp_dir):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_find_units.return_value = self.units
        mock_open.return_value.extractall.side_effect = OSError

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['errors']), 2)
        self.assertTrue(report.details['errors'][0][0] in [self.uk1, self.uk2])
        self.assertTrue(report.details['errors'][1][0] in [self.uk1, self.uk2])
        self.assertEqual(len(report.details['success_unit_keys']), 0)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_check_for_unsafe_archive_paths',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    def test_cannot_clear_destination(self, mock_find_units, mock_clear, mock_check, mock_open,
                                     mock_mkdir, mock_create_tmp_dir):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_find_units.return_value = []
        mock_clear.side_effect = OSError

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['success_unit_keys']), 0)
        mock_clear.assert_called_once_with(self.puppet_dir)

    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_move_to_destination_directory',
                       side_effect=OSError)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_create_temporary_destination_directory',
                       return_value=None)
    @mock.patch.object(installdistributor, 'mkdir', return_value=None)
    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_check_for_unsafe_archive_paths',
                       return_value=None)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor,
                       '_clear_destination_directory',
                       return_value=None)
    @mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    def test_cannot_move_to_destination(self, mock_find_units, mock_clear, mock_check, mock_open,
                                        mock_mkdir, mock_create_tmp_dir, mock_move):
        config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.puppet_dir})
        mock_find_units.return_value = []

        report = self.distributor.publish_repo(self.repo, self.conduit, config)

        self.assertFalse(report.success_flag)
        self.assertTrue(isinstance(report.summary, basestring))
        self.assertEqual(len(report.details['success_unit_keys']), 0)
        mock_move.assert_called_once_with(mock_create_tmp_dir.return_value, self.puppet_dir)


class TestMoveToDestinationDirectory(unittest.TestCase):
    def setUp(self):
        self.working_dir = tempfile.mkdtemp()
        self.destination_dir = os.path.join(self.working_dir, 'target')
        os.makedirs(self.destination_dir)
        self.source_dir = os.path.join(self.working_dir, 'source')
        os.makedirs(self.source_dir)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def existing_files_saved(self):
        existing_file = os.path.join(self.destination_dir, 'foo.txt')
        touch(existing_file)
        new_dir = os.path.join(self.source_dir, 'bar')
        os.makedirs(new_dir)
        installdistributor.PuppetModuleInstallDistributor.\
            _move_to_destination_directory(self.source_dir, self.destination_dir)

        self.assertTrue(os.path.exists(existing_file))

    def test_source_dir_removed(self):
        installdistributor.PuppetModuleInstallDistributor.\
            _move_to_destination_directory(self.source_dir, self.destination_dir)
        self.assertFalse(os.path.exists(self.source_dir))

    def test_move_dirs(self):
        new_dir = os.path.join(self.source_dir, 'bar')
        os.makedirs(new_dir)
        installdistributor.PuppetModuleInstallDistributor.\
            _move_to_destination_directory(self.source_dir, self.destination_dir)

        self.assertTrue(os.path.exists(os.path.join(self.destination_dir, 'bar')))


class TestRenameDirectory(unittest.TestCase):
    def setUp(self):
        self.unit = mock.Mock()
        self.unit.name = 'foobar'
        self.method = installdistributor.PuppetModuleInstallDistributor._rename_directory

    @mock.patch('shutil.move', autospec=True)
    def test_trailing_slash(self, mock_move):
        self.method(self.unit, '/tmp/', ['a/b', 'a/c'])

        mock_move.assert_called_once_with('/tmp/a', '/tmp/foobar')

    @mock.patch('shutil.move', autospec=True)
    def test_no_trailing_slash(self, mock_move):
        self.method(self.unit, '/tmp', ['a/b', 'a/c'])

        mock_move.assert_called_once_with('/tmp/a', '/tmp/foobar')

    @mock.patch('shutil.move', autospec=True)
    def test_too_many_dirs(self, mock_move):
        self.assertRaises(ValueError, self.method, self.unit, '/tmp', ['a/b', 'c/b'])

    @mock.patch('shutil.move', autospec=True)
    def test_no_dirs(self, mock_move):
        self.assertRaises(ValueError, self.method, self.unit, '/tmp', [])

    @mock.patch('shutil.move', autospec=True)
    def test_absolute_paths(self, mock_move):
        self.method(self.unit, '/tmp', ['/tmp/a/b', '/tmp/a/c'])

        mock_move.assert_called_once_with('/tmp/a', '/tmp/foobar')

    @mock.patch('shutil.move', autospec=True)
    def test_empty_dir(self, mock_move):
        """weird scenario, but you never know..."""
        self.method(self.unit, '/tmp', ['a'])

        mock_move.assert_called_once_with('/tmp/a', '/tmp/foobar')

    @mock.patch('shutil.move', autospec=True)
    def test_same_dir(self, mock_move):
        self.method(self.unit, '/tmp', ['foobar'])

        self.assertFalse(mock_move.called)


class TestCheckForUnsafeArchivePaths(unittest.TestCase):
    def setUp(self):
        self.distributor = installdistributor.PuppetModuleInstallDistributor()
        self.uk1 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.2.0'}
        self.uk2 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.2.1'}
        self.units = [
            Module(_storage_path='/a/b/x', **self.uk1),
            Module(_storage_path='/a/b/y', **self.uk2)
        ]

    def test_does_not_exist(self):
        self.distributor._check_for_unsafe_archive_paths(self.units, '/foo/bar')

        self.assertEqual(len(self.distributor.detail_report.report['errors']), 2)
        self.assertTrue(self.distributor.detail_report.report['errors'][0][0] in [self.uk1, self.uk2])
        self.assertTrue(isinstance(self.distributor.detail_report.report['errors'][0][1], basestring))
        self.assertTrue(self.distributor.detail_report.report['errors'][1][0] in [self.uk1, self.uk2])
        self.assertTrue(isinstance(self.distributor.detail_report.report['errors'][1][1], basestring))

    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor, '_archive_paths_are_safe')
    def test_safe(self, mock_archive_paths_are_safe, mock_open):
        mock_archive_paths_are_safe.return_value = True

        self.distributor._check_for_unsafe_archive_paths(self.units, '/foo/bar')

        mock_archive_paths_are_safe.assert_any_call('/foo/bar', mock_open.return_value)
        self.assertEqual(mock_archive_paths_are_safe.call_count, 2)
        self.assertEqual(len(self.distributor.detail_report.report['errors']), 0)

    @mock.patch('tarfile.open', autospec=True)
    @mock.patch.object(installdistributor.PuppetModuleInstallDistributor, '_archive_paths_are_safe')
    def test_unsafe(self, mock_archive_paths_are_safe, mock_open):
        mock_archive_paths_are_safe.return_value = False

        self.distributor._check_for_unsafe_archive_paths(self.units, '/foo/bar')

        mock_archive_paths_are_safe.assert_any_call('/foo/bar', mock_open.return_value)
        self.assertEqual(mock_archive_paths_are_safe.call_count, 2)
        self.assertEqual(len(self.distributor.detail_report.report['errors']), 2)

        self.assertEqual(mock_open.call_count, 2)
        mock_open.assert_any_call('/a/b/x')
        mock_open.assert_any_call('/a/b/y')


class TestArchivePathsAreSafe(unittest.TestCase):
    def setUp(self):
        self.tarball = tarfile.TarFile(fileobj=StringIO(), mode='w')
        self.tarball.getnames = mock.MagicMock(spec_set=self.tarball.getnames)

    def test_safe_names(self):
        self.tarball.getnames.return_value = [
            'a/b/c',
            'd/e/f',
            'g/h/../i',
            '/foo/a/b/', # this is a terrible thing to have in a tarball, but just in case...
        ]

        ret = installdistributor.PuppetModuleInstallDistributor._archive_paths_are_safe(
            '/foo', self.tarball)

        self.assertTrue(ret)

    def test_unsafe_relative_name(self):
        self.tarball.getnames.return_value = [
            'a/b/c',
            'd/e/f',
            '../i',
        ]

        ret = installdistributor.PuppetModuleInstallDistributor._archive_paths_are_safe(
            '/foo', self.tarball)

        self.assertFalse(ret)

    def test_unsafe_absolute_name(self):
        """
        I'm not actually sure if this is possible with a tarball
        """
        self.tarball.getnames.return_value = [
            'a/b/c',
            'd/e/f',
            '/i',
        ]

        ret = installdistributor.PuppetModuleInstallDistributor._archive_paths_are_safe(
            '/foo', self.tarball)

        self.assertFalse(ret)


class TestClearDestinationDirectory(unittest.TestCase):
    def setUp(self):
        self.distributor = installdistributor.PuppetModuleInstallDistributor()

    @mock.patch('shutil.rmtree', autospec=True)
    def test_real_dir(self, mock_rmtree):
        destination = os.path.dirname(os.path.dirname(__file__))

        self.distributor._clear_destination_directory(destination)

        # makes sure it only tries to remove the directories, and not any of the
        # regular files that appear within "destination"
        self.assertEqual(mock_rmtree.call_count, 3)
        mock_rmtree.assert_any_call(os.path.join(destination, 'data'))
        mock_rmtree.assert_any_call(os.path.join(destination, 'integration'))
        mock_rmtree.assert_any_call(os.path.join(destination, 'unit'))


class TestCreateTemporaryDestinationDirectory(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_no_dir(self):
        destination = os.path.join(self.tmp_dir, 'puppet')
        distributor = installdistributor.PuppetModuleInstallDistributor()
        destination_dir = distributor._create_temporary_destination_directory(destination)
        self.assertTrue(os.path.isdir(destination_dir))

    def test_dir_already_exists(self):
        destination = os.path.join(self.tmp_dir, 'puppet')
        os.makedirs(destination)
        distributor = installdistributor.PuppetModuleInstallDistributor()
        destination_dir = distributor._create_temporary_destination_directory(destination)
        self.assertTrue(os.path.isdir(destination_dir))
        self.assertTrue(os.path.isdir(destination))

    @mock.patch('os.makedirs', side_effect=OSError(errno.EPERM))
    def test_dir_permission_denied(self, *unused):
        destination = os.path.join(self.tmp_dir, 'puppet')
        distributor = installdistributor.PuppetModuleInstallDistributor()
        self.assertRaises(OSError, distributor._create_temporary_destination_directory, destination)


class TestDetailReport(unittest.TestCase):
    def setUp(self):
        self.report = installdistributor.DetailReport()
        self.uk1 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.2.0'}
        self.uk2 = {'author': 'puppetlabs', 'name': 'stdlib', 'version': '1.2.1'}

    def test_success(self):
        self.report.success(self.uk1)

        self.assertTrue(self.uk1 in self.report.report['success_unit_keys'])

    def test_error(self):
        self.report.error(self.uk1, 'failed')

        self.assertTrue((self.uk1, 'failed') in self.report.report['errors'])

    def test_has_errors_true(self):
        self.report.error(self.uk1, 'failed')

        self.assertTrue(self.report.has_errors)

    def test_has_errors_false_success(self):
        self.report.success(self.uk1)

        self.assertFalse(self.report.has_errors)

    def test_has_errors_false_empty(self):
        self.report.success(self.uk1)

        self.assertFalse(self.report.has_errors)

    def test_report_is_dict(self):
        self.assertTrue(isinstance(self.report.report, dict))


class TestException(Exception):
    pass


class TestDistributorRemoved(unittest.TestCase):
    def setUp(self):
        self.distributor = installdistributor.PuppetModuleInstallDistributor()
        self.repo = Repository('repo1', '', '')
        self.path = '/a/b/c/'
        self.config = PluginCallConfiguration({}, {constants.CONFIG_INSTALL_PATH: self.path})

    @mock.patch('shutil.rmtree', spec_set=True)
    def test_calls_rmtree(self, mock_rmtree):
        self.distributor.distributor_removed(self.repo, self.config)

        mock_rmtree.assert_called_once_with(self.path)

    @mock.patch.object(installdistributor._LOGGER, 'error', spec_set=True)
    @mock.patch('shutil.rmtree', spec_set=True, side_effect=TestException)
    def test_rmtree_exception(self, mock_rmtree, mock_error):
        self.assertRaises(TestException, self.distributor.distributor_removed, self.repo, self.config)
        # make sure the error was logged
        self.assertEqual(mock_error.call_count, 1)

    @mock.patch('shutil.rmtree', spec_set=True)
    def test_without_configured_path(self, mock_rmtree):
        self.distributor.distributor_removed(self.repo, PluginCallConfiguration({}, {}))

        self.assertEqual(mock_rmtree.call_count, 0)
