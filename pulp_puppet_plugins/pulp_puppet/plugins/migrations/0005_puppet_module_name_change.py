from gettext import gettext as _
import logging
import os
import tempfile

from mongoengine import NotUniqueError, Q
from pulp.server.controllers import repository as repo_controller
from pulp.server.db import model

from pulp_puppet.plugins.db.models import Module

_log = logging.getLogger('pulp')


def migrate(*args, **kwargs):
    """
    For each puppet module check and if needed update module name format.

    There was a discrepancy in the way puppet module's name was stored in pulp, depending
    if it was synced from filesystem or uploaded. This migration finds puppet module units
    that have wrong format name and replaces it with a correct format name.
    """

    modules = Module.objects.filter(Q(name__contains='/') | Q(name__contains='-'))
    repos_to_rebuild = set()
    for puppet_unit in modules:
        try:
            author, name = puppet_unit['name'].split("-", 1)
        except ValueError:
            # This is the forge format, but Puppet still allows it
            author, name = puppet_unit['name'].split("/", 1)
        try:
            puppet_unit.name = name
            puppet_unit.save()
        except NotUniqueError:
            # find all repos that have this unit
            repos_with_unit = model.RepositoryContentUnit.objects.filter(unit_id=puppet_unit.id)
            repos_to_rebuild.update(repos_with_unit)
            # find unit with correct name
            correct_unit = Module.objects.filter(name=name).first()
            for repo in repos_with_unit:
                # unassociate wrong unit
                repo_controller.disassociate_units(repo, [puppet_unit])
                # associate correct unit to the list of the repos
                repo_controller.associate_single_unit(repo, correct_unit)

    repo_list = []
    for repo in repos_to_rebuild:
        repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo.repo_id)
        repo_controller.rebuild_content_unit_counts(repo_obj)
        repo_list.append(repo.repo_id)

    repos_to_republish = model.Distributor.objects.filter(repo_id__in=repo_list,
                                                          last_publish__ne=None)
    # redirect output to file
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, 'repos_to_republish.txt')
    f = open(path, 'w')
    f.write(str([repo.repo_id for repo in repos_to_republish]))
    f.close()
    msg = _('***Note. You may want to re-publish the list of repos found in %s.\n'
            '   This migration fixed an issue with modules installation related to wrong '
            'puppet_module name.' % f.name)
    _log.info(msg)
