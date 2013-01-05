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