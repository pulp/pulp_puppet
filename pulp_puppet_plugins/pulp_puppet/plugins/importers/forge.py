from datetime import datetime
from gettext import gettext as _
import logging
import os
import sys

from pulp.server.controllers import repository as repo_controller

from pulp_puppet.common import constants
from pulp_puppet.common.constants import (STATE_FAILED, STATE_RUNNING,
                                          STATE_SUCCESS, STATE_CANCELED)
from pulp_puppet.common.sync_progress import SyncProgressReport
from pulp_puppet.plugins.db.models import Module, RepositoryMetadata
from pulp_puppet.plugins.importers import metadata as metadata_module
from pulp_puppet.plugins.importers.downloaders import factory as downloader_factory


_logger = logging.getLogger(__name__)


class SynchronizeWithPuppetForge(object):
    """
    Used to perform a single sync of a puppet repository. This class will
    maintain state relevant to the run and should not be reused across runs.
    """

    def __init__(self, repo, sync_conduit, config):
        self.repo = repo
        self.sync_conduit = sync_conduit
        self.config = config

        self.progress_report = SyncProgressReport(sync_conduit)
        self.downloader = None
        # Since SynchronizeWithPuppetForge creates a Nectar downloader for each unit, we cannot
        # rely on telling the current downloader to cancel. Therefore, we need another state
        # tracker to check in the download units loop.
        self._canceled = False

    def __call__(self):
        """
        Sync according to the configured state of the instance and return a report.

        This function will make update progress as appropriate.

        This function executes serially, and does not create any threads. It will not return until
        either a step fails or the entire sync is complete.

        :return: the report object to return to Pulp from the sync call
        :rtype: SyncProgressReport
        """
        msg = _('Beginning sync for repository <%(repo_id)s>')
        msg_dict = {'repo_id': self.repo.id}
        _logger.info(msg, msg_dict)

        # quit now if there is no feed URL defined
        if not self.config.get(constants.CONFIG_FEED):
            self.progress_report.metadata_state = STATE_FAILED
            msg = _('Cannot perform repository sync on a repository with no feed')
            self.progress_report.metadata_error_message = msg
            self.progress_report.update_progress()
            return self.progress_report.build_final_report()

        try:
            metadata = self._parse_metadata()
            if not metadata:
                report = self.progress_report.build_final_report()
                return report

            self._import_modules(metadata)
        finally:
            # One final progress update before finishing
            self.progress_report.update_progress()

            return self.progress_report

    def cancel(self):
        """
        Cancel an in-progress sync, if there is one.
        """
        self._canceled = True
        if self.downloader is None:
            return
        self.downloader.cancel()

    def _parse_metadata(self):
        """
        Takes the necessary actions (according to the run configuration) to
        retrieve and parse the repository's metadata. This call will return
        either the successfully parsed metadata or None if it could not
        be retrieved or parsed. The progress report will be updated with the
        appropriate description of what went wrong in the event of an error,
        so the caller should interpret a None return as an error occurring and
        not continue the sync.

        :return: object representation of the metadata
        :rtype:  RepositoryMetadata
        """
        msg = _('Beginning metadata retrieval for repository <%(repo_id)s>')
        msg_dict = {'repo_id': self.repo.id}
        _logger.info(msg, msg_dict)

        self.progress_report.metadata_state = STATE_RUNNING
        self.progress_report.update_progress()

        start_time = datetime.now()

        # Retrieve the metadata from the source
        try:
            downloader = self._create_downloader()
            self.downloader = downloader
            metadata_json_docs = downloader.retrieve_metadata(self.progress_report)

        except Exception as e:
            if self._canceled:
                msg = _('Exception occurred on canceled metadata download: %(exc)s')
                msg_dict = {'exc': e}
                _logger.warn(msg, msg_dict)
                self.progress_report.metadata_state = STATE_CANCELED
                return None
            msg = _('Exception while retrieving metadata for repository <%(repo_id)s>')
            msg_dict = {'repo_id': self.repo.id}
            _logger.exception(msg, msg_dict)
            self.progress_report.metadata_state = STATE_FAILED
            self.progress_report.metadata_error_message = _('Error downloading metadata')
            self.progress_report.metadata_exception = e
            self.progress_report.metadata_traceback = sys.exc_info()[2]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.metadata_execution_time = duration.seconds

            self.progress_report.update_progress()

            return None

        finally:
            self.downloader = None

        # Parse the retrieved metadata documents
        try:
            metadata = RepositoryMetadata()
            for doc in metadata_json_docs:
                metadata.update_from_json(doc)
        except Exception as e:
            msg = _('Exception parsing metadata for repository <%(repo_id)s>')
            msg_dict = {'repo_id': self.repo.id}
            _logger.exception(msg, msg_dict)
            self.progress_report.metadata_state = STATE_FAILED
            self.progress_report.metadata_error_message = _('Error parsing repository modules metadata document')
            self.progress_report.metadata_exception = e
            self.progress_report.metadata_traceback = sys.exc_info()[2]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.metadata_execution_time = duration.seconds

            self.progress_report.update_progress()

            return None

        # Last update to the progress report before returning
        self.progress_report.metadata_state = STATE_SUCCESS

        end_time = datetime.now()
        duration = end_time - start_time
        self.progress_report.metadata_execution_time = duration.seconds

        self.progress_report.update_progress()

        return metadata

    def _import_modules(self, metadata):
        """
        Imports each module in the repository into Pulp.

        This method is mostly just a wrapper on top of the actual logic
        of performing an import to set the stage for the progress report and
        more importantly catch any rogue exceptions that crop up.

        :param metadata: object representation of the repository metadata
               containing the modules to import
        :type  metadata: RepositoryMetadata
        """
        msg = _('Retrieving modules for repository <%(repo_id)s>')
        msg_dict = {'repo_id': self.repo.id}
        _logger.info(msg, msg_dict)

        self.progress_report.modules_state = STATE_RUNNING

        # Do not send the update about the state yet. The counts need to be
        # set later once we know how many are new, so to prevent a situation
        # where the report reflects running but does not have counts, wait
        # until they are populated before sending the update to Pulp.

        start_time = datetime.now()

        try:
            self._do_import_modules(metadata)
        except Exception as e:
            msg = _('Exception importing modules for repository <%(repo_id)s>')
            msg_dict = {'repo_id': self.repo.id}
            _logger.exception(msg, msg_dict)
            self.progress_report.modules_state = STATE_FAILED
            self.progress_report.modules_error_message = _('Error retrieving modules')
            self.progress_report.modules_exception = e
            self.progress_report.modules_traceback = sys.exc_info()[2]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.modules_execution_time = duration.seconds

            self.progress_report.update_progress()

            return

        # Last update to the progress report before returning
        self.progress_report.modules_state = STATE_SUCCESS

        end_time = datetime.now()
        duration = end_time - start_time
        self.progress_report.modules_execution_time = duration.seconds

        self.progress_report.update_progress()

    def _do_import_modules(self, metadata):
        """
        Actual logic of the import. This method will do a best effort per module;
        if an individual module fails it will be recorded and the import will
        continue. This method will only raise an exception in an extreme case
        where it cannot react and continue.
        """
        downloader = self._create_downloader()
        self.downloader = downloader

        # Ease module lookup
        metadata_modules_by_key = dict([(m.unit_key_str, m) for m in metadata.modules])

        # Collect information about the repository's modules before changing it
        existing_module_ids_by_key = {}
        for module in Module.objects.only(*Module.unit_key_fields).all():
            existing_module_ids_by_key[module.unit_key_str] = module.id

        new_unit_keys = self._resolve_new_units(existing_module_ids_by_key.keys(),
                                                metadata_modules_by_key.keys())

        # Once we know how many things need to be processed, we can update the progress report
        self.progress_report.modules_total_count = len(new_unit_keys)
        self.progress_report.modules_finished_count = 0
        self.progress_report.modules_error_count = 0
        self.progress_report.update_progress()

        # Add new units
        for key in new_unit_keys:
            if self._canceled:
                break
            module = metadata_modules_by_key[key]
            try:
                self._add_new_module(downloader, module)
                self.progress_report.modules_finished_count += 1
            except Exception as e:
                self.progress_report.add_failed_module(module, e, sys.exc_info()[2])

            self.progress_report.update_progress()

        # Remove missing units if the configuration indicates to do so
        if self._should_remove_missing():
            remove_unit_keys = self._resolve_remove_units(existing_module_ids_by_key.keys(),
                                                          metadata_modules_by_key.keys())
            doomed_ids = [existing_module_ids_by_key[key] for key in remove_unit_keys]
            doomed_module_iterator = Module.objects.in_bulk(doomed_ids).itervalues()
            repo_controller.disassociate_units(self.repo, doomed_module_iterator)

        repo_controller.rebuild_content_unit_counts(self.repo.repo_obj)
        self.downloader = None

    def _add_new_module(self, downloader, module):
        """
        Performs the tasks for downloading and saving a new unit in Pulp.

        This method entirely skips modules that are already in the repository.

        :param downloader: downloader instance to use for retrieving the unit
        :type downloader: child of pulp_puppet.plugins.importers.downloaders.base.BaseDownloader

        :param module: module to download and add
        :type  module: pulp_puppet.plugins.db.models.Module
        """
        try:
            # Download the bits
            downloaded_filename = downloader.retrieve_module(self.progress_report, module)

            # Extract the extra metadata into the module
            metadata = metadata_module.extract_metadata(downloaded_filename,
                                                         self.repo.working_dir)

            # Overwrite the author and name
            metadata.update(Module.split_filename(metadata['name']))

            # Create and save the Module
            module = Module.from_metadata(metadata)
            module.set_storage_path(os.path.basename(downloaded_filename))
            module.save()
            module.import_content(downloaded_filename)

            # Associate the module with the repo
            repo_controller.associate_single_unit(self.repo.repo_obj, module)
        finally:
            downloader.cleanup_module(module)

    def _resolve_new_units(self, existing_unit_keys, metadata_unit_keys):
        """
        Returns a list of metadata keys that are new to the repository.

        :return: list of unit keys; empty list if none are new
        :rtype:  list
        """
        return list(set(metadata_unit_keys) - set(existing_unit_keys))

    def _resolve_remove_units(self, existing_unit_keys, metadata_unit_keys):
        """
        Returns a list of unit keys that are in the repository but not in
        the current repository metadata.

        :return: list of unit keys; empty list if none have been removed
        :rtype:  list
        """
        return list(set(existing_unit_keys) - set(metadata_unit_keys))

    def _create_downloader(self):
        """
        Uses the configuratoin to determine which downloader style to use
        for this run.

        :return: one of the *Downloader classes in the downloaders module
        """

        feed = self.config.get(constants.CONFIG_FEED)
        return downloader_factory.get_downloader(feed, self.repo, self.sync_conduit, self.config)

    def _should_remove_missing(self):
        """
        Returns whether or not missing units should be removed.

        :return: true if missing units should be removed; false otherwise
        :rtype:  bool
        """

        if constants.CONFIG_REMOVE_MISSING not in self.config.keys():
            return constants.DEFAULT_REMOVE_MISSING
        else:
            return self.config.get_boolean(constants.CONFIG_REMOVE_MISSING)
