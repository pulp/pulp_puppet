import os
import shutil

from pulp.server.controllers import repository as repo_controller

from pulp_puppet.common import constants
from pulp_puppet.plugins.db.models import Module
from pulp_puppet.plugins.importers import metadata as metadata_parser


def handle_uploaded_unit(repo, type_id, unit_key, metadata, file_path, conduit):
    """
    Handles an upload unit request to the importer. This call is responsible
    for moving the unit from its temporary location where Pulp stored the
    upload to the final storage location (as dictated by Pulp) for the unit.
    This call will also update the database in Pulp to reflect the unit
    and its association to the repository.

    :param repo: repository into which the unit is being uploaded
    :type repo: pulp.plugins.model.Repository
    :param type_id: type of unit being uploaded
    :type type_id: str
    :param unit_key: unique identifier for the unit
    :type unit_key: dict
    :param metadata: extra data about the unit
    :type metadata: dict
    :param file_path: temporary location of the uploaded file
    :type file_path: str
    :param conduit: for calls back into Pulp
    :type conduit: pulp.plugins.conduit.upload.UploadConduit
    """
    if type_id != constants.TYPE_PUPPET_MODULE:
        raise NotImplementedError()

    # Extract the metadata from the module
    extracted_data = metadata_parser.extract_metadata(file_path, repo.working_dir)

    # rename the file so it has the original module name
    original_filename = extracted_data['name'] + '-' + extracted_data['version'] + '.tar.gz'
    new_file_path = os.path.join(os.path.dirname(file_path), original_filename)
    shutil.move(file_path, new_file_path)

    # Overwrite the author and name
    extracted_data.update(Module.split_filename(extracted_data['name']))

    uploaded_module = Module.from_metadata(extracted_data)
    uploaded_module.set_content(new_file_path)
    uploaded_module.save()

    repo_controller.associate_single_unit(repo.repo_obj, uploaded_module)
    repo_controller.rebuild_content_unit_counts(repo.repo_obj)

    return {'success_flag': True, 'summary': '', 'details': {}}
