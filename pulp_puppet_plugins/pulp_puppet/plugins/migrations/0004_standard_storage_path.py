from pulp.server.db import connection

from pulp.plugins.migration.standard_storage_path import Migration, Plan


def migrate(*args, **kwargs):
    """
    Migrate content units to use the standard storage path introduced in pulp 2.8.
    """
    migration = Migration()
    migration.add(module_plan())
    migration()


def module_plan():
    """
    Factory to create an puppet module migration plan.

    :return: A configured plan.
    :rtype: Plan
    """
    key_fields = (
        'author',
        'name',
        'version'
    )
    collection = connection.get_collection('units_puppet_module')
    return Plan(collection, key_fields)
