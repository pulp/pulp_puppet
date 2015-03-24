Plugin Configuration
====================

Importer
--------

Type ID: ``puppet_importer``

``feed``
 URL to an existing repository that should be imported, for example ``http://forge.puppetlabs.com``

 The repository may be either a Puppet Forge repository or a plain directory containing a
 pulp manifest and packaged puppet modules.  The pulp manifest is a file listing each puppet
 module contained in the directory. Each module is listed on a separate line which has the
 following format: <name>,<checksum>,<size>. The *name* is the file name. The *checksum* is
 SHA-256 digest of the file.  The *size* is the size of the file in bytes. The Pulp manifest
 must be named ``PULP_MANIFEST``.

 Example:

 Directory containing:

 - PULP_MANIFEST
 - module-a.tar.gz
 - module-b.tar.gz
 - module-c.tar.gz

 The PULP_MANIFEST:

 ::

  module-a.tar.gz,2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881,1763
  module-b.tar.gz,5dde896887f6754c9b15bfe3a441ae4806df2fde94001311e08bf110622e0bbe,1431
  module-c.tar.gz,cd2eb0837c9b4c962c22d2ff8b5441b7b45805887f051d39bf133b583baf6860,2213

 The URL:  ``file://myhost/modules/PULP_MANIFEST``

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
 Defaults to ``/var/lib/pulp/published/puppet/http/repos``.

``https_dir``
 Full path to the directory where HTTPS-published repositories should be created.
 Defaults to ``/var/lib/pulp/published/puppet/https/repos``.

``serve_http``
 Boolean indicating if the repository should be served over HTTP. Defaults to ``True``.

``serve_https``
 Boolean indicating if the repository should be served over HTTPS. Defaults to ``False``.


.. _install-distributor:

Install Distributor
-------------------

Type ID: ``puppet_install_distributor``

This distributor publishes modules by actually installing them into a given
``install_path`` on the Pulp server's filesystem. The use case is that you want
the contents of a repository to exactly be the collection of modules installed
in a puppet environment. This allows you to use Pulp's repository management
features to manage which modules are installed in puppet.

This distributor performs these operations in the following order:
 1. Creates a temporary directory in the parent directory of ``install_path``.
 2. Extracts each module in the repository to that temporary directory.
 3. Deletes every directory it finds in the ``install_path``.
 4. Moves the content of temporary directory into the ``install_path``.
 5. Removes the temporary directory.

.. warning:: This distributor deletes all directories found in the ``install_path``!

``install_path``
 This is a full path to the directory where modules should be installed. It is the user's
 responsibility to ensure that Pulp can write to this directory. The web server user (for example,
 ``apache``) must be granted filesystem permissions to write to this path and the parent directory.
 Additionally, the system SELinux policy must permit Pulp to write to this directory. Pulp's SELinux
 policy includes a ``pulp_manage_puppet`` boolean that allows Pulp to write to paths that have the
 ``puppet_etc_t`` label. You must ensure that the ``install_path`` and its parent directory have this
 label applied to it. This boolean is disabled by default for safety. If you wish to enable it, you
 can do this::

    $ sudo semanage boolean --modify --on pulp_manage_puppet

 ``/etc/puppet/`` has the ``puppet_etc_t`` label by default, so if you use this or a sub directory of
 it as your ``install_path`` and you enable the ``pulp_manage_puppet`` boolean, SELinux will allow
 Pulp to write to that path.

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
 Defaults to ``/var/lib/pulp/published/puppet/files``.
