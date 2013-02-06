Recipes
=======


Mirror Puppet Forge
-------------------

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

Installing With Puppet Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You might notice that this command does not work:

::

  $ puppet module install --module_repository http://localhost/pulp/puppet/forge author/name

For technical reasons described in the note below, the ``puppet module install``
tool ignores the part of the URL after the host name, which means we cannot put
the repository ID in the URL. We have a work-around that will still allow you to
use the ``puppet module install`` command with Pulp, and it involves the use of
basic auth credentials as part of the URL.

.. note:: Puppet Forge implements a web API that their client uses to obtain dependency
          data when installing a module. Unfortunately, their command line tool has
          hard-coded absolute paths instead of relative, which means the API must live at
          the root of a web server. As a result, we cannot put the repository ID in the
          path as you would expect with the above example.

- **Consumer ID** For a consumer registered with Pulp, just specify its consumer
  ID as the username in the URL, and a "." for the password. A consumer's ID is a
  unique identifier just like a username, so this isn't actually a bad use of
  that field. When a consumer ID is provided, Pulp searches all of that consumer's
  bound repositories for either the newest version of the requested module, or
  if a version is specified, searches for the exact version requested. Once a
  suitable module has been located in a bound repository, all dependency data
  returned is scoped to that same repository.

::

  $ puppet module install --module_repository http://consumer1:.@localhost

- **Repository ID** For machines that are not bound to a repository, or for a
  bound machine where you want to specify a repository, do so in the password
  field. If a repository ID is specified, any value in the username field is
  ignored. To keep the convention, use a single "." as a null value.

::

  $ puppet module install --module_repository http://.:forge@localhost

The repository URL can be set in ``/etc/puppet/puppet.conf`` so that it
does not need to be provided on the command line every time. See Puppet's own
documentation for details.

.. note:: The dependency API from Puppet Forge has been re-implemented by Pulp
          and can be accessed at /api/v1/releases.json. Puppet Forge also
          implements a search API that Pulp has not re-implemented due to even
          more restrictive use of absolute URLs in the puppet tool.

          At this time, Puppet Labs is working on a new version of their API that
          will include public documentation, and we believe that new API will be
          much easier to integrate with.
