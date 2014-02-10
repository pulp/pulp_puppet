Forge API
=========

Puppet Forge implements a basic API that is not currently documented. The
challenging aspect of re-implementing the API is that prior to puppet version
3.3, the ``puppet module`` tool used hard-coded absolute paths, so the API must
exist at the root of the web server. This also prevents the inclusion of a
repository ID in the URL.

Search
------

Pulp does not implement the search API, so using ``puppet module search``
against a Pulp repository will not work. This was not implemented because of the
URL namespace problem.

Dependency
----------

When the ``puppet module`` tool needs to know what the dependencies are for a
particular module (such as at install time), it queries the dependency API. For
a module named ``puppetlabs/java``, the following request would be made against
the Puppet Forge repository.

::

  http://forge.puppetlabs.com/api/v1/releases.json?module=puppetlabs/java

Because of the URL namespace limitation described above, Pulp had to take a
creative approach to identifing which repositories should be considered when
determining the dependencies for a module.

Basic Auth
^^^^^^^^^^

For puppet versions prior to 3.3, basic authentication credentials included in
the URL are used to specify either a repository ID or a consumer ID. When a
consumer ID is specified, all repositories to which it is bound are searched for
the specified module. If a verison was not specified, the repository with the
newest version is then queried for dependency information.

This is an example request with a consumer ID:

::

  http://consumer1:.@localhost/api/v1/releases.json?module=puppetlabs/java

This is an example with a repository ID and a version:

::

  http://.:repo1@localhost/api/v1/releases.json?module=puppetlabs/java&version=0.2.0

When specifying a repository ID or a consumer ID, use a single "." in place of
the other value.


Under the Hood
^^^^^^^^^^^^^^

When a Puppet repository is published by Pulp, a small
`gdbm <http://docs.python.org/2/library/gdbm.html>`_ database is generated and
placed at the root of the repository containing all of the data necessary to
respond to dependency queries. This ensures that when dependency data is
returned, it corresponds to the state of the repository at the time it was
published, and does not reflect any changes made in the database since. The
name of this file is ``.dependency_db``, and it is not visible when accessing
the repository over HTTP because Apache excludes files whose names begin with ".".
