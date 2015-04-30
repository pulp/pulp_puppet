Type
====

The programmatic identifier for this type is ``puppet_module``.

When identifying modules on Puppet Forge or on the command line, the indentifier
takes the form ``author/name``. For example: ``puppetlabs/stdlib``. These
"author" and "name" fields are used individually as part of the unit key.

Unit Key
--------

``author``
 Module's author, in the form of a "username" on Puppet Forge. For example, the
 contributor "Puppet Labs" has the username "puppetlabs".

``name``
 Module's name only, not including the author section. For the module
 identified as "puppetlabs/stdlib", this field would be "stdlib".

``version``
 Module's version, which according to Puppet Labs' documentation, should follow
 `Semantic Versioning <http://semver.org/>`_. 


Metadata
--------

``dependencies``
 List of dictionaries describing modules on which this module depends. Each
 dictionary has a key ``name`` which includes the full ``author/name`` notation,
 and a key ``version_requirement`` which describes what versions are acceptable
 to satisfy this dependency. This is an empty list if there are no dependencies.
 The format for this value is described in detail in Puppet Labs' own
 `documentation <http://docs.puppetlabs.com/puppet/latest/reference/modules_publishing.html#write-a-metadatajson-file>`_.

``description``
 Longer description of the module.

``license``
 Name of the license with which the module is distributed.

``project_page``
 URL to a web site for the module.

``source``
 URL to the module's source.

``summary``
 Short description of the module, 1 line only.

``tag_list``
 List of tags assigned to this module on Puppet Forge. This is an empty list if
 there are no tags.

