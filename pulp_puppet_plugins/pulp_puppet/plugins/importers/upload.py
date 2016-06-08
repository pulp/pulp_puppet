import os
import shutil

from mongoengine import NotUniqueError

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

    # Overwrite the author and name
    extracted_data.update(Module.split_filename(extracted_data['name']))

    uploaded_module = Module.from_metadata(extracted_data)

    # rename the file so it has the original module name
    new_file_path = os.path.join(os.path.dirname(file_path),
                                 uploaded_module.puppet_standard_filename())
    shutil.move(file_path, new_file_path)

    uploaded_module.set_storage_path(os.path.basename(new_file_path))
    try:
        uploaded_module.save_and_import_content(new_file_path)
    except NotUniqueError:
        uploaded_module = uploaded_module.__class__.objects.get(**uploaded_module.unit_key)
    repo_controller.associate_single_unit(repo.repo_obj, uploaded_module)

    return {'success_flag': True, 'summary': '', 'details': {}}
