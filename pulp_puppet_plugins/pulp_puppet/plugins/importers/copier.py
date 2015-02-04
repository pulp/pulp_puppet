from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_puppet.common import constants


def copy_units(import_conduit, units):
    """
    Copies puppet modules from one repo into another. There is nothing that
    the importer needs to do; it maintains no state in the working directory
    so the process is to simply tell Pulp to import each unit specified.
    """

    # Determine which units are being copied
    if units is None:
        criteria = UnitAssociationCriteria(type_ids=[constants.TYPE_PUPPET_MODULE])
        units = import_conduit.get_source_units(criteria=criteria)

    # Associate to the new repository
    for u in units:
        import_conduit.associate_unit(u)

    return units
