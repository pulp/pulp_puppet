from pulp.server.controllers.repository import find_repo_content_units
from pulp.server.db.model import Repository


def copy_units(import_conduit, units):
    """
    Copies puppet modules from one repo into another. There is nothing that
    the importer needs to do; it maintains no state in the working directory
    so the process is to simply tell Pulp to import each unit specified.
    """

    # Determine which units are being copied
    if units is None:
        repo = Repository.objects.get(repo_id=import_conduit.source_repo_id)
        units = find_repo_content_units(repo, yield_content_unit=True)

    # Associate to the new repository
    units_to_return = []
    for u in units:
        units_to_return.append(u)
        import_conduit.associate_unit(u)

    return units_to_return
