Introduction
============

Puppet support for Pulp allows you to create and publish repositories of Puppet
modules. One common use case is to mirror `Puppet Forge <http://forge.puppetlabs.com>`_.
You can synchronize an existing repository such as all or part of Puppet Forge,
upload your own Puppet modules, and publish the result as a repository inside
your own network.

Another common use case is to copy synced modules into a custom repository and add
additional modules by uploading them directly. This allows you to test new modules
or new versions of existing modules and then easily promote them into a production
repository.

Puppet modules must adhere to the Puppet `3.6+ metadata guidelines
<https://docs.puppetlabs.com/puppet/latest/reference/modules_publishing.html#publishing-modules-on-the-puppet-forge>`_,
which require a valid `metadata.json` file to be present in the puppet module. Also, each tag.gz
file must contain only one Puppet module inside it. Extra directories or Puppet modules can cause
unexpected behavior.

Consumers must have Puppet 2.7.14 to 3.4.3 installed, and we recommend getting the Puppet client
packages directly from `Puppet Labs <http://puppetlabs.com>`_.
