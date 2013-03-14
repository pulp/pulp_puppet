Installation
============

.. _Pulp User Guide: http://pulp-user-guide.readthedocs.org

.. note::
  If you followed the installation instructions in the `Pulp User Guide`_,
  you already have Puppet features installed. If not, this document will walk
  you through the installation.

Prerequisites
-------------

Puppet support requires the namespace ``/api/v1/`` at the root of your web server
in order to implement an API compatible with Puppet Forge. We don't like
taking that namespace, but it was the only way to support the use of Puppet
Labs' command line tool against a Pulp server.

Consumers must have Puppet 2.7.14+ installed, and we recommend getting packages
directly from `Puppet Labs <http://puppetlabs.com>`_.

Please see the `Pulp User Guide`_ for other prerequisites including repository
setup.

Server
------

If you followed the Pulp User Guide install instructions, you already have Puppet
support installed. If not, just install the following package.

::

  $ sudo yum install pulp-puppet-plugins

Then run ``pulp-manage-db`` to initialize the new types in Pulp's database.

::

  $ sudo pulp-manage-db

Finally, restart Apache.

::

  $ sudo apachectl restart

Admin Client
------------

If you followed the Pulp User Guide install instructions, you already have Puppet
support installed. If not, just install the following package.

::

  $ sudo yum install pulp-puppet-admin-extensions

