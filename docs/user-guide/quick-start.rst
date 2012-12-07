Quick Start
===========

Login
-----

The default admin password is "admin".

::

  $ pulp-admin login -u admin
  Enter password:
  Successfully logged in. Session certificate will expire at Dec 14 18:50:41 2012
  GMT.

Create a Repository
-------------------

::

  $ pulp-admin puppet repo create --repo-id=repo1 --description="Mirror of Puppet Forge" --display-name="Repo 1" --feed=http://forge.puppetlabs.com
  Successfully created repository [repo1]

Update a Repository
-------------------

Let's add a query to limit the scope of how many modules get synced.

::

  $ pulp-admin puppet repo update --repo-id=repo1 --query=libvirt
  Repository [repo1] successfully updated

List Repositories
-----------------

::

  $ pulp-admin puppet repo list
  +----------------------------------------------------------------------+
                            Puppet Repositories
  +----------------------------------------------------------------------+

  Id:                 repo1
  Display Name:       Repo 1
  Description:        Mirror of Puppet Forge
  Content Unit Count: 0

To include more details, use the ``--details`` flag.

::

  $ pulp-admin puppet repo list --details
  +----------------------------------------------------------------------+
                            Puppet Repositories
  +----------------------------------------------------------------------+

  Id:                 repo1
  Display Name:       Repo 1
  Description:        Mirror of Puppet Forge
  Content Unit Count: 0
  Notes:
  Importers:
    Config:
      Feed:    http://forge.puppetlabs.com
      Queries: libvirt
    Id:               puppet_importer
    Importer Type Id: puppet_importer
    Last Sync:        None
    Repo Id:          repo1
    Scheduled Syncs:
    Scratchpad:       None
  Distributors:
    Auto Publish:        True
    Config:
    Distributor Type Id: puppet_distributor
    Id:                  puppet_distributor
    Last Publish:        None
    Repo Id:             repo1
    Scheduled Publishes:
    Scratchpad:          None

Search Repositories
-------------------

This is a search for all repositories with more than 0 modules.

::

  $ pulp-admin puppet repo search --gt='content_unit_count=0'
  +----------------------------------------------------------------------+
                                Repositories
  +----------------------------------------------------------------------+

  Id:                 forge
  Display Name:       forge
  Description:        None
  Content Unit Count: 669
  Notes:
  Scratchpad:

  Id:                 repo1
  Display Name:       Repo 1
  Description:        Mirror of Puppet Forge
  Content Unit Count: 2
  Notes:
  Scratchpad:


Sync a Repository
-----------------

::

  $ pulp-admin puppet repo sync run --repo-id=repo1
  +----------------------------------------------------------------------+
                      Synchronizing Repository [repo1]
  +----------------------------------------------------------------------+

  This command may be exited by pressing ctrl+c without affecting the actual
  operation on the server.

  Downloading metadata...
  [==================================================] 100%
  Metadata Query: 1/1 items
  ... completed

  Downloading new modules...
  [==================================================] 100%
  Module: 2/2 items
  ... completed

  Publishing modules...
  [==================================================] 100%
  Module: 2/2 items
  ... completed

  Generating repository metadata...
  [-]
  ... completed

  Publishing repository over HTTP...
  ... completed

  Publishing repository over HTTPS...
  ... skipped

At this point, the repository has been published and is available via HTTP.

List Modules in a Repository
----------------------------

::

  $ pulp-admin puppet repo modules --repo-id=repo1
  Name:         libvirt
  Version:      0.0.1
  Author:       thias
  Dependencies:
  Description:  Install, configure and enable libvirt.
  License:      Apache 2.0
  Project Page: http://glee.thias.es/puppet
  Source:       git://github.com/thias/puppet-modules/modules/libvirt
  Summary:      Libvirt virtualization API and capabilities
  Tag List:     rhel, libvirt, kvm, CentOS
  Types:

  Name:         virt
  Version:      1.0.0
  Author:       carlasouza
  Dependencies:
  Description:  None
  License:      GPLv3
  Project Page: None
  Source:
  Summary:      None
  Tag List:     virtualization, kvm, xen, openvz, libvirt
  Types:

To be more specific, we can search by name.

::

  $ pulp-admin puppet repo modules --repo-id=repo1 --str-eq='name=libvirt'
  Name:         libvirt
  Version:      0.0.1
  Author:       thias
  Dependencies:
  Description:  Install, configure and enable libvirt.
  License:      Apache 2.0
  Project Page: http://glee.thias.es/puppet
  Source:       git://github.com/thias/puppet-modules/modules/libvirt
  Summary:      Libvirt virtualization API and capabilities
  Tag List:     rhel, libvirt, kvm, CentOS
  Types:

Or by license, and for fun let's use a regex.

::

  $ pulp-admin puppet repo modules --repo-id=repo1 --match='license=^GPL.*'
  Name:         virt
  Version:      1.0.0
  Author:       carlasouza
  Dependencies:
  Description:  None
  License:      GPLv3
  Project Page: None
  Source:
  Summary:      None
  Tag List:     virtualization, kvm, xen, openvz, libvirt
  Types:

Copy Modules Between Repositories
---------------------------------

Assuming we have repositories "repo1" and "repo2", and "repo1" has two units as
resulted from the above sync.

::

  $ pulp-admin puppet repo create --repo-id=repo2
  Successfully created repository [repo2]

  $ pulp-admin puppet repo copy --from-repo-id=repo1 --to-repo-id=repo2 --str-eq='name=libvirt'
  Progress on this task can be viewed using the commands under "repo tasks".

  $ pulp-admin repo tasks list --repo-id=repo1
  +----------------------------------------------------------------------+
                                   Tasks
  +----------------------------------------------------------------------+

  Operations:  associate
  Resources:   repo2 (repository), repo1 (repository)
  State:       Successful
  Start Time:  Unstarted
  Finish Time: 2012-12-07T19:04:54Z
  Result:      Incomplete
  Task Id:     54459b2f-6ed9-4918-94c9-63e2b3370554

Publish a Repository
--------------------

By default, repositories are auto-published following a sync. However, if you create
an new repository and populate it with content by copying and/or uploading modules,
you will need to publish manually. Since that is the case for "repo2" into which
we just copied a module, let's publish that repo.

::

  $ pulp-admin puppet repo publish run --repo-id=repo2
  +----------------------------------------------------------------------+
                       Publishing Repository [repo2]
  +----------------------------------------------------------------------+

  This command may be exited by pressing ctrl+c without affecting the actual
  operation on the server.

  Publishing modules...
  [==================================================] 100%
  Module: 1/1 items
  ... completed

  Generating repository metadata...
  [-]
  ... completed

  Publishing repository over HTTP...
  ... completed

  Publishing repository over HTTPS...
  ... skipped

Delete a Repository
-------------------

::

  $ pulp-admin puppet repo delete --repo-id=repo1
  Repository [repo1] successfully deleted

