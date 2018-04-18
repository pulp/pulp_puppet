Recipes
=======


Mirror Puppet Forge
-------------------

Start by creating a new repository that includes the URL for Puppet Forge. Use
any repo-id you like, as long as it is unique within Pulp.

::

  $ pulp-admin puppet repo create --repo-id=forge --feed=http://forge.puppet.com
  Successfully created repository [forge]

Next synchronize the repository, which downloads all of the modules into the local
repository.

::

  $ pulp-admin puppet repo sync run --repo-id=forge
  +----------------------------------------------------------------------+
                      Synchronizing Repository [forge]
  +----------------------------------------------------------------------+

  This command may be exited by pressing ctrl+c without affecting the actual
  operation on the server.

  Downloading metadata...
  [==================================================] 100%
  Metadata Query: 1/1 items
  ... completed

  Downloading new modules...
  [==================================================] 100%
  Module: 669/669 items
  ... completed

  Publishing modules...
  [==================================================] 100%
  Module: 669/669 items
  ... completed

  Generating repository metadata...
  [\]
  ... completed

  Publishing repository over HTTP...
  ... completed

  Publishing repository over HTTPS...
  ... skipped

Let's take a moment to display the repository and admire your work!

::

  $ pulp-admin puppet repo list
  +----------------------------------------------------------------------+
                            Puppet Repositories
  +----------------------------------------------------------------------+

  Id:                 forge
  Display Name:       forge
  Description:        None
  Content Unit Count: 669

Also point a browser to
`http://localhost/pulp/puppet/forge/ <http://localhost/pulp/puppet/forge/>`_
(adjust the host name as needed) to view the published repository.

Install Modules
---------------

.. _install_post_33:

Installing With Puppet Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install from a specific pulp repository, the forge URL is formed
as ``http://.:<repository_id>@<hostname>``. To
install as a consumer from any bound repository, the URL is formed
as ``http://<consumer_id>:.@<hostname>``.

For example, to install module puppetlabs-stdlib from the repository "demo",
run the following command.

::

  $ puppet module install --module_repository=http://.:demo@localhost/ puppetlabs-stdlib

Or to install module puppetlabs-stdlib as the consumer "con1" from any repository
to which that consumer is bound, run the following command.

::

  $ puppet module install --module_repository=http://con1:.@localhost/ puppetlabs-stdlib

Installing With r10k
^^^^^^^^^^^^^^^^^^^^

.. note:: r10k is not currently compatible with Pulp due to changes in r10k that now requires
          the Forge API's ``/v3/modules`` endpoint in addition to the ``/v3/releases`` endpoint.
          Issue is being tracked in https://pulp.plan.io/issues/1848 


Puppet Consumers
----------------

Puppet modules installed on puppet masters can be managed with Pulp's consumer
features. Start by registering the system as a consumer. This process only
needs to happen once, after which the consumer can bind to repositories of any
content type (puppet modules, RPMs, or any other content supported by Pulp).
Note that the following command requires root privileges.

::

    $ sudo pulp-consumer register --consumer-id=fred
    Enter password:
    Consumer [fred] successfully registered

Next the consumer should be bound to a repository. This can be done with the
``pulp-consumer`` command from a shell on the consumer machine.

::

    $ pulp-consumer puppet bind --repo-id=forge
    Bind tasks successfully created:

    Task Id: 9531a15f-d19d-4c77-9a61-ac67e1223c93

    Task Id: 9f06e091-e54c-47d4-8b17-cebfc4451215

The same could be accomplished using the pulp-admin command, which interacts with
the Pulp server. The server then notifies the consumer of the binding.

::

    $ pulp-admin puppet consumer bind --repo-id=forge --consumer-id=fred
    Bind tasks successfully created:

    Task Id: 88a49289-2dc8-49f3-9050-92bcd8ddc8de

    Task Id: 8e8f3cd7-420e-447c-8feb-8cf5703a2324

Either way, we can now see from pulp-admin that the consumer is bound to the
repository with ID "forge".

::

    $ pulp-admin consumer list
    +----------------------------------------------------------------------+
                                   Consumers
    +----------------------------------------------------------------------+

    Id:            fred
    Display Name:  fred
    Description:   None
    Bindings:
      Confirmed:   forge
      Unconfirmed:
    Notes:


Install
^^^^^^^

For install requests, Pulp will search all repositories to which the consumer is
bound to find the requested module. If no version is specified, it will find the
newest version available. Once the module has been found in a repository,
dependency resolution will occur only within that repository. The install
command will automatically install any dependencies.

This example installs a specific version of the ``puppetlabs/stdlib`` module.

::

    $ pulp-admin puppet consumer install run --consumer-id=fred -u puppetlabs/stdlib/3.1.1
    This command may be exited via ctrl+c without affecting the request.

    [\]
    1 change was made

    Install Succeeded


Update
^^^^^^

Updates follow the same repository matching process as installs. This example
updates the ``puppetlabs/stdlib`` module. Since a version is not specified, the
newest available version will be installed.

::

    $ pulp-admin puppet consumer update run --consumer-id=fred -u puppetlabs/stdlib
    Update task created with id [ 672d34e9-e0c3-40ea-942f-76da2d7dbad1 ]

    This command may be exited via ctrl+c without affecting the request.

    [|]
    1 change was made

    Update Succeeded


Uninstall
^^^^^^^^^

Uninstall requests merely uninstall the specified module.

::

    $ pulp-admin puppet consumer uninstall run --consumer-id=fred -u puppetlabs/stdlib
    Uninstall task created with id [ 0f040d05-d37d-4a4d-a1aa-1c882aeea771 ]

    This command may be exited via ctrl+c without affecting the request.

    [-]
    Waiting to begin
    1 change was made

    Uninstall Succeeded


Building and Importing Modules
------------------------------

Start by creating a working directory. The directory will be used for git cloning and for building
puppet modules.  This directory will be the *feed* for our Pulp repository.  Use any directory you
like so long as you have *write* and *execute* permissions.

::

 $ sudo mkdir -p /opt/puppet/modules
 $ sudo chmod -R 777 /opt/puppet

Next, create a new repository that specifies a feed URL for the directory that will be created in a
subsequent step. Use any repo-id you like, as long as it is unique within Pulp.

::

  $ pulp-admin puppet repo create --repo-id=puppet-builds --feed=file:///opt/puppet/modules/
  Successfully created repository [puppet-builds]

Next, build the puppet modules from source. The ``pulp-puppet-module-builder`` tool is provided
with Pulp puppet support to make this step easier. The tool uses the
`puppet module <https://puppet.com/docs/puppet/4.10/man/module.html>`_ tool to build
modules.  It also supports basic `Git <http://git-scm.com>`_ repository operations such a cloning and
the checkout of branches and tags to simplify the building and importing of pupppet modules from
git repositories.

.. seealso:: ``pulp-puppet-module-builder --help`` for usage and options.

In this example, we will build the ``puppetlabs-xinitd`` module provided by the Puppet Labs git
repository using ``pulp-puppet-module-builder``.

::

 $ cd /opt/puppet
 $ pulp-puppet-module-builder --url=https://github.com/puppetlabs/puppetlabs-xinetd -o ../modules
 cd /opt/puppet
 git clone --recursive https://github.com/puppetlabs/puppetlabs-xinetd
 cd puppetlabs-xinetd
 git status
 git remote show -n origin
 git fetch
 git fetch --tags
 git pull
 find . -name init.pp
 puppet module build .
 mkdir -p ../modules
 cp ./pkg/puppetlabs-xinetd-1.2.0.tar.gz ../modules
 cd ../modules
 cd /opt/puppet/puppetlabs-xinetd
 cd /opt/puppet

Listing of ``/opt/puppet/modules``:

::

 -rw-rw-r-- 1 demo demo  101 Jan 29 09:46 PULP_MANIFEST
 -rw-rw-r-- 1 demo demo 6127 Jan 29 09:46 puppetlabs-xinetd-1.2.0.tar.gz

The content of PULP_MANIFEST:

::

 puppetlabs-xinetd-1.2.0.tar.gz,344bfa47dc88b17d91a8b4a32ab6b8cbc12346a59e9898fce29c235eab672958,6127

Next synchronize the repository, which imports all of the modules into the local Pulp repository.
When the directory containing the built modules is located on another host and served by http,
the feed URL for the manifest may be ``http://`` instead of `file://`` in which case, the manifest
and modules are downloaded into a temporary location.

::

  $ pulp-admin puppet repo sync run --repo-id=puppet-builds
  +----------------------------------------------------------------------+
                 Synchronizing Repository [puppet-builds]
  +----------------------------------------------------------------------+

  This command may be exited by pressing ctrl+c without affecting the actual
  operation on the server.

  Downloading metadata...
  [==================================================] 100%
  Metadata Query: 1/1 items
  ... completed

  Downloading new modules...
  [==================================================] 100%
  Module: 1/1 items
  ... completed

  Publishing modules...
  [==================================================] 100%
  Module: 1/1 items
  ... completed

  Generating repository metadata...
  [\]
  ... completed

  Publishing repository over HTTP...
  ... completed

  Publishing repository over HTTPS...
  ... skipped


.. note::
 The ``pulp-puppet-module-builder`` requires that module source layout conform to
 Puppet Labs standard module
 `layout <https://puppet.com/docs/puppet/4.10/modules_fundamentals.html#module-layout>`_






