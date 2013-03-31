=============
Release Notes
=============

Pulp 2.1.0
==========

New Features
------------

#. Pulp 2.1 now supports Fedora 18 and Apache 2.4.
#. We now support the Puppet Forge API.

Upgrade Instructions
--------------------

Upgrade the Platform and Pulp Puppet Software
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To upgrade to the new Pulp release, you should begin by using yum to install the latest RPMs from the Pulp
repository, run the database migrations, and cleanup orphaned packages::

    $ sudo yum upgrade
    $ sudo pulp-manage-db
    $ sudo pulp-admin orphan remove --all

Republish Puppet Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Puppet Forge API will not work for previously published repositories. Those repositories must be
republished. You can find out the repository IDs on your system with this command::

    pulp-admin puppet repo list --fields repo_id

For each ID in that list, you can republish it with this command, substituting <repo_id> with the ID of the
repository you wish to republish::

    pulp-admin puppet repo publish run --repo-id=<repo_id>
