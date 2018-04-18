Introduction
============

Puppet support for Pulp allows you to create and publish repositories of Puppet
modules. One common use case is to mirror `Puppet Forge <http://forge.puppet.com>`_.
You can synchronize an existing repository such as all or part of Puppet Forge,
upload your own Puppet modules, and publish the result as a repository inside
your own network.

Another common use case is to copy synced modules into a custom repository and add
additional modules by uploading them directly. This allows you to test new modules
or new versions of existing modules and then easily promote them into a production
repository.

Puppet modules must adhere to the Puppet `4.10+ metadata guidelines
<https://puppet.com/docs/puppet/4.10/modules_publishing.html>`_,
which require a valid `metadata.json` file to be present in the puppet module. Also, each tag.gz
file must contain only one Puppet module inside it. Extra directories or Puppet modules can cause
unexpected behavior.

Consumers must have Puppet 4.10.x to 5.x installed, and we recommend getting the Puppet client
packages directly from `Puppet, Inc <http://puppet.com>`_.
