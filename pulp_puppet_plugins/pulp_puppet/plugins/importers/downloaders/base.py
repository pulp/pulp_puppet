class BaseDownloader(object):
    """
    Base class all downloaders should extend. The factory will pass the
    necessary data to the constructor; any subclass should support the
    same signature to ensure the factory can create it.
    """

    def __init__(self, repo, conduit, config):
        self.repo = repo
        self.conduit = conduit
        self.config = config
        self.downloader = None

    def retrieve_metadata(self, progress_report):
        """
        Retrieves all metadata documents needed to fulfill the configuration
        set for the repository. The progress report will be updated as the
        downloads take place.

        :param progress_report: used to communicate the progress of this operation
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :return: list of JSON documents describing all modules to import
        :rtype: list
        """
        raise NotImplementedError()

    def retrieve_module(self, progress_report, module):
        """
        Retrieves the given module and returns where on disk it can be
        found. It is the caller's job to copy this file to where Pulp
        wants it to live as its final resting place. This downloader will
        then be allowed to clean up the downloaded file in the
        cleanup_module call.

        :param progress_report: used if any updates need to be made as the
               download runs
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module: module to download
        :type module: pulp_puppet.common.model.Module

        :return: full path to the temporary location where the module file is
        :rtype: str
        """
        raise NotImplementedError()

    def retrieve_modules(self, progress_report, module_list):
        """
        Batch version of the retrieve_module method

        :param progress_report: used if any updates need to be made as the
               download runs
        :type progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module_list: list of modules to be downloaded
        :type module_list: iterable

        :return: list of full paths to the temporary locations where the modules are
        :rtype: list
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Cancel the current operation.
        """
        raise NotImplementedError()

    def cleanup_module(self, module):
        """
        Called once the unit has been copied into Pulp's storage location to
        let the downloader do any post-processing it needs (for instance,
        deleting any temporary copies of the file).

        :param module: module to clean up
        :type module: pulp_puppet.common.model.Module
        """
        raise NotImplementedError()
