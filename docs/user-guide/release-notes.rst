=============
Release Notes
=============

Pulp 2.1.0
==========

New Features
------------

#. Pulp 2.1 now supports Fedora 18 and Apache 2.4.
#. We now support the use of the ``puppet module`` tool (provided by Puppet) against a Pulp server.
#. Pulp can now manage installation, upgrade, and removal of puppet modules on Pulp consumers."

Upgrade Instructions
--------------------

Upgrade the Platform and Pulp Puppet Software
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please see the
`Pulp Platform upgrade instructions <https://pulp-user-guide.readthedocs.org/en/pulp-2.1/release-notes.html#upgrade-instructions-for-2-0-2-1>`_
to upgrade the Pulp and Puppet RPMs and database.

Republish Puppet Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Puppet Forge API will not work for previously published repositories. Those repositories must be
republished. You can find out the repository IDs on your system with this command::

    $ sudo pulp-admin puppet repo list --fields repo_id

For each ID in that list, you can republish it with this command, substituting <repo_id> with the ID of the
repository you wish to republish::

    $ sudo pulp-admin puppet repo publish run --repo-id=<repo_id>
