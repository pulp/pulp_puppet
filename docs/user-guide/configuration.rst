#############
Configuration
#############

**********************
Importer Configuration
**********************

The Puppet importer is configured by editing
``/etc/pulp/server/plugins.conf.d/puppet_importer.json``. This file must be valid `JSON`_. The
following key value pairs are supported by the importer below.

.. _JSON: http://json.org/

``proxy_url``: A string in the form of scheme://host, where scheme is either ``http`` or ``https``

``proxy_port``: An integer representing the port number to use when connecting to the proxy server

``proxy_username``: If provided, Pulp will attempt to use basic auth with the proxy server using this
                    as the username

``proxy_password``: If provided, Pulp will attempt to use basic auth with the proxy server using this
                    as the password
