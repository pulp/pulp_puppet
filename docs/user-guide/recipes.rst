Recipes
=======


Mirror PuppetForge
------------------

Start by creating a new repository that includes the URL for Puppet Forge. Use
any repo-id you like, as long as it is unique within Pulp.

::

  $ pulp-admin puppet repo create --repo-id=forge --feed=http://forge.puppetlabs.com
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
