Plugin Configuration
======================

Importer
--------

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
 
