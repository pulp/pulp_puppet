Installation
============

.. _Pulp User Guide: https://docs.pulpproject.org

.. note::
  If you followed the Pulp installation instructions you already have Puppet
  features installed. If not, this document will walk you through the installation.

Prerequisites
-------------

Puppet support requires the namespace ``/api/v1/`` at the root of your web server
in order to implement an API compatible with Puppet Forge. We don't like
taking that namespace, but it was the only way to support the use of Puppet
Labs' command line tool against a Pulp server.

Consumers must have Puppet 2.7.14 to 3.4.3 installed, and we recommend getting packages
directly from `Puppet Labs <http://puppetlabs.com>`_.

Please see the `Pulp User Guide`_ for other prerequisites including repository
setup.

.. note::
    Consumer install and update operations against a repository published over
    HTTPS will do SSL certificate verification. Thus, you must ensure that the
    ``puppet module`` tool is able to verify the server's certificate against a
    trusted CA in order to publish puppet repositories over HTTPS.

Server
------

If you followed the Pulp User Guide install instructions, you already have Puppet
support installed. If not, just install the following package.

::

  $ sudo yum install pulp-puppet-plugins

Then run ``pulp-manage-db`` to initialize the new types in Pulp's database.

::

  $ sudo -u apache pulp-manage-db

Then restart each pulp component, as documented in the `Pulp User Guide`_.

Admin Client
------------

If you followed the Pulp User Guide install instructions, you already have Puppet
support installed. If not, just install the following package.

::

  $ sudo yum install pulp-puppet-admin-extensions

