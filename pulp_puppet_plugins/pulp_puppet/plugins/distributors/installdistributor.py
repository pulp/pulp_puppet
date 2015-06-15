import errno
from gettext import gettext as _
import logging
import os
import shutil
import tarfile
import tempfile

from pulp.plugins.distributor import Distributor
from pulp.server.controllers.repository import find_repo_content_units
from pulp.plugins.util.misc import get_parent_directory, mkdir

from pulp_puppet.common import constants
from pulp_puppet.plugins.db.models import Module

ERROR_MESSAGE_PATH = 'one or more units contains a path outside its base extraction path'
_LOGGER = logging.getLogger(__name__)


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor

    :return: distributor class and its config
    :rtype:  Distributor, {}
    """
    # there is never a default or global config for this distributor
    return PuppetModuleInstallDistributor, {}


class PuppetModuleInstallDistributor(Distributor):

    def __init__(self):
        super(PuppetModuleInstallDistributor, self).__init__()
        self.detail_report = DetailReport()

    @classmethod
    def metadata(cls):
        """
        Advertise the capabilities of the PuppetModuleInstallDistributor.

        :return: The description of PuppetModuleInstallDistributor's capabilities.
        :rtype:  dict
        """
        return {
            'id': constants.INSTALL_DISTRIBUTOR_TYPE_ID,
            'display_name': _('Puppet Install Distributor'),
            'types': [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, config_conduit):
        """
        Validate the configuration of the install distributor.

        :param repo: metadata describing the repository to which the configuration applies
        :type repo: pulp.plugins.model.Repository
        :param config: plugin configuration instance; contains the proposed repo configuration
        :type config: pulp.plugins.config.PluginCallConfiguration
        :param config_conduit: Configuration conduit
        :type config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

        :return: A tuple of validation results
        :rtype: tuple of length two. Either (False, str) or (True, None)
        """
        path = config.get(constants.CONFIG_INSTALL_PATH)
        if not isinstance(path, basestring):
            # path not here, nothing else to validate
            return True, None
        if not os.path.isabs(path):
            return False, _('install path is not absolute')
        return True, None

    def publish_repo(self, repo, publish_conduit, config):
        """
        Publish the repository by "installing" each puppet module into the given
        destination directory. This effectively means extracting each module's
        tarball in that directory.

        :param repo: plugin repository object
        :type repo: pulp.plugins.model.Repository
        :param publish_conduit: provides access to relevant Pulp functionality
        :type publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginConfiguration

        :return: report describing the publish run
        :rtype: pulp.plugins.model.PublishReport
        """
        # get dir from config
        destination = config.get(constants.CONFIG_INSTALL_PATH)
        if not destination:
            return publish_conduit.build_failure_report(_('install path not provided'),
                                                        self.detail_report.report)
        units = list(find_repo_content_units(repo.repo_obj, yield_content_unit=True))

        duplicate_units = self._find_duplicate_names(units)
        if duplicate_units:
            for unit in duplicate_units:
                self.detail_report.error(unit.unit_key,
                                         'another unit in this repo also has this name')
            return publish_conduit.build_failure_report(_('duplicate unit names'),
                                                        self.detail_report.report)

        # check for unsafe paths in tarballs, and fail early if problems are found
        self._check_for_unsafe_archive_paths(units, destination)
        if self.detail_report.has_errors:
            return publish_conduit.build_failure_report('failed', self.detail_report.report)

        # ensure the destination directory exists
        try:
            mkdir(destination)
            temporarydestination = self._create_temporary_destination_directory(destination)
        except OSError, e:
            return publish_conduit.build_failure_report(
                _('failed to create destination directory: %s') % str(e), self.detail_report.report)

        # actually publish
        for unit in units:
            try:
                archive = tarfile.open(unit.storage_path)
                try:
                    archive.extractall(temporarydestination)
                    self._rename_directory(unit, temporarydestination, archive.getnames())
                finally:
                    archive.close()
                self.detail_report.success(unit.unit_key)
            except (OSError, IOError, ValueError), e:
                self.detail_report.error(unit.unit_key, str(e))

        if self.detail_report.has_errors:
            return publish_conduit.build_failure_report(_('failed publishing units'),
                                                        self.detail_report.report)

        # remove old directory if exists
        try:
            self._clear_destination_directory(destination)
        except (IOError, OSError), e:
            return publish_conduit.build_failure_report(
                _('failed to clear destination directory: %s') % str(e),
                self.detail_report.report)

        # move the subdirs of the temporary dir to the destination dir
        try:
            self._move_to_destination_directory(temporarydestination, destination)
        except (IOError, OSError), e:
            return publish_conduit.build_failure_report(
                _('failed to move temporary destination to destination directory: %s') % str(e),
                self.detail_report.report)

        # return some kind of report
        if self.detail_report.has_errors:
            return publish_conduit.build_failure_report(_('failed'), self.detail_report.report)
        else:
            return publish_conduit.build_success_report(_('success'), self.detail_report.report)

    def distributor_removed(self, repo, config):
        """
        Remove the environment that is configured for use.

        :param repo: metadata describing the repository
        :type repo: pulp.plugins.model.Repository
        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginCallConfiguration
        """
        destination = config.get(constants.CONFIG_INSTALL_PATH)
        if destination:
            msg = _('removing installed modules from environment at %(directory)s')
            msg_dict = {'directory': destination}
            _LOGGER.info(msg, msg_dict)
            try:
                shutil.rmtree(destination)
            except Exception, e:
                msg = _('error removing environment: %(exc)s')
                msg_dict = {'exc': e}
                _LOGGER.error(msg, msg_dict)
                raise

    @staticmethod
    def _find_duplicate_names(units):
        """
        Returns a list of units that have the same name as at least one other
        unit in this repository. This is a problem because in order to "install"
        these modules, they must be extracted into the destination directory
        and renamed to just the "name" portion of their unit key. Multiple units
        with the name name will conflict on the filesystem.

        :param units: iterable of all units being published
        :type units: iterable

        :return: list of units that have conflicting names
        :rtype: list
        """
        names = {}
        for unit in units:
            name = unit.name
            if name not in names:
                names[name] = 1
            else:
                names[name] = names[name] + 1

        duplicates = set()
        for name, count in names.iteritems():
            if count > 1:
                duplicates.add(name)
        return [unit for unit in units if unit.name in duplicates]

    @staticmethod
    def _rename_directory(unit, destination, names):
        """
        Given a list of names from a unit's tarball and the destination, figure
        out the name of the directory that was extracted, and then move it to
        the name that puppet expects.

        :param unit: unit whose tarball was extracted at the destination
        :type unit: pulp.plugins.model.AssociatedUnit
        :param destination: absolute path to the destination where modules should be installed
        :type destination: str
        :param names: list of paths (relative or absolute) to files that are contained in the
                      archive that was just extracted.
        :type names: list

        :raise: IOError, ValueError
        """
        if not destination.endswith('/'):
            destination += '/'
        dest_length = len(destination)

        dir_names = set(
            [os.path.join(destination, name)[dest_length:].split('/')[0] for name in names]
        )
        if len(dir_names) != 1:
            raise ValueError('too many directories extracted')

        before = os.path.normpath(os.path.join(destination, dir_names.pop()))
        after = os.path.normpath(os.path.join(destination, unit.name))
        if before != after:
            shutil.move(before, after)

    def _check_for_unsafe_archive_paths(self, units, destination):
        """
        Check the paths of files in each tarball to make sure none include path
        components, such as "../", that would cause files to be placed outside of
        the destination directory. Adds errors to the detail report for each unit
        that has one or more offending paths.

        :param units: list of units whose tarballs should be checked for unsafe paths
        :type units: list of pulp_puppet.plugins.db.models.Module objects
        :param destination: absolute path to the destination where modules should be installed
        :type destination: str
        """
        for unit in units:
            try:
                archive = tarfile.open(unit.storage_path)
                try:
                    if not self._archive_paths_are_safe(destination, archive):
                        self.detail_report.error(unit.unit_key, ERROR_MESSAGE_PATH)
                finally:
                    archive.close()
            except (OSError, IOError), e:
                self.detail_report.error(unit.unit_key, str(e))

    @staticmethod
    def _archive_paths_are_safe(destination, archive):
        """
        Checks a tarball archive for paths that include components such as "../"
        that would cause files to be placed outside of the destination_path.

        :param destination: absolute path to the destination where modules should be installed
        :type destination: str
        :param archive: tarball archive that should be checked
        :type archive: tarfile.TarFile

        :return: True iff all paths in the archive are safe, else False
        :rtype: bool
        """
        for name in archive.getnames():
            result = os.path.normpath(os.path.join(destination, name))
            if not destination.endswith('/'):
                destination += '/'
            if not result.startswith(destination):
                return False
        return True

    @staticmethod
    def _clear_destination_directory(destination):
        """
        Deletes every directory found in the given destination.

        :param destination: absolute path to the destination where modules should be installed
        :type destination: str
        """
        for directory in os.listdir(destination):
            path = os.path.join(destination, directory)
            if os.path.isdir(path):
                shutil.rmtree(path)

    @staticmethod
    def _create_temporary_destination_directory(destination, mode=0755):
        """
        Create the temporary destination directory as a peer of the target destination.
        This is so that the move is hopefully taking place on the same filesystem so it
        will be as fast as possible.

        :param destination: absolute path to the destination where modules should be installed
        :type destination: str
        :param mode: the directory permissions
        :type mode: int

        :return: absolute path to temporary created directory
        :rtype: str
        """
        basedir = get_parent_directory(destination)
        try:
            os.makedirs(basedir, mode)
        except OSError, e:
            if e.errno == errno.EEXIST and os.path.isdir(basedir):
                pass
            else:
                raise
        return tempfile.mkdtemp(prefix='pulp', dir=basedir)

    @staticmethod
    def _move_to_destination_directory(source, destination):
        """
        Move the subdirectories of a source directory to a destination directory and then delete
        the source directory.

        :param source: absolute path to where modules are installed
        :type source: str
        :param destination: absolute path to where the modules should be copied to
        :type destination: str
        """
        for directory in os.listdir(source):
            path = os.path.join(source, directory)
            if os.path.isdir(path):
                shutil.move(path, destination)
        shutil.rmtree(source)


class DetailReport(object):
    """
    convenience class to manage the structure of the "detail" report
    """
    def __init__(self):
        self.report = {
            'success_unit_keys': [],
            'errors': [],
        }

    def success(self, unit_key):
        """
        Call for each unit that is successfully published. This adds that unit key to the report.

        :param unit_key: unit key for a successfully published unit
        :type unit_key: dict
        """
        self.report['success_unit_keys'].append(unit_key)

    def error(self, unit_key, error_message):
        """
        Call for each unit that has an error during publish. This adds that unit
        key to the report.

        :param unit_key: unit key for unit that had an error during publish
        :type unit_key: dict
        :param error_message: error message indicating what went wrong for this particular unit
        :type error_message: str
        """
        self.report['errors'].append((unit_key, error_message))

    @property
    def has_errors(self):
        """
        :return: True iff this report has one or more errors, else False
        :rtype: bool
        """
        return bool(self.report['errors'])
