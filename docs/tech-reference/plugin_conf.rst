Plugin Configuration
====================

Importer
--------

Type ID: ``puppet_importer``

``feed``
 URL to an existing repository that should be imported, for example ``http://forge.puppetlabs.com``

``queries``
 Comma-separated list of queries that should be run against the upstream
 repository. Each query is used separately to retrieve a result set, and each
 resulting module will be imported.

``remove_missing``
 Boolean indicating whether or not previously-synced modules should be removed
 from the local repository if they were removed in the upstream repository.
 Defaults to ``False``.


Distributor
-----------

Type ID: ``puppet_distributor``

This distributor publishes a forge-like API. The user guide explains in detail
how to use the ``puppet module`` tool to install, update, and remove modules
on a puppet installation using a repository hosted by Pulp. This distributor does
not support the search functionality that Puppet Forge offers, primarily because
that feature is not compatible with the concept of hosting multiple repositories
at one FQDN.

``absolute_path``
 Base absolute URL path where all Puppet repositories are published. Defaults
 to ``/pulp/puppet``.

``http_dir``
 Full path to the directory where HTTP-published repositories should be created.
 Defaults to ``/var/www/pulp_puppet/http/repos``.

``https_dir``
 Full path to the directory where HTTPS-published repositories should be created.
 Defaults to ``/var/www/pulp_puppet/https/repos``.

``serve_http``
 Boolean indicating if the repository should be served over HTTP. Defaults to ``True``.

``serve_https``
 Boolean indicating if the repository should be served over HTTPS. Defaults to ``False``.


Install Distributor
-------------------

Type ID: ``puppet_install_distributor``

This distributor publishes modules by actually installing them into a given
``install_path`` on the Pulp server's filesystem. The use case is that you want
the contents of a repository to exactly be the collection of modules installed
in a puppet environment. This allows you to use Pulp's repository management
features to manage which modules are installed in puppet.

This distributor starts by deleting every directory it finds in the
``install_path``, and then it extracts each module in the repository to that
directory.

.. warning:: This distributor deletes all directories found in the ``install_path``!

``install_path``
 Full path to the directory where modules should be installed. It is the user's
 responsibility to ensure that Pulp can write to this directory.

File Distributor
-------------------

Type ID: ``puppet_file_distributor``

This distributor publishes modules by making them available in a flattened format in
a single directory on the file system and served via HTTPS.  The files are published
to the ``https_files_dir`` specified in the plugin configuration.  A repository is
placed in a subdirectory of the ```https_files_dir`` with the same name as the repository
id.  The base URL path where all Puppet repositories are published is ``/pulp/puppet/files``.

``https_files_dir``
 Full path to the directory where HTTPS published file repositories will be created.
 Defaults to ``/var/www/pulp_puppet/files``.
