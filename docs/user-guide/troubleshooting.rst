Troubleshooting
===============

SSL Certificate Verification Fails for Consumer Install
-------------------------------------------------------

Symptom
^^^^^^^

Installing a module on a consumer results in an "unknown error".

::

    $ pulp-admin puppet consumer install run --consumer-id client2 -u puppetlabs/stdlib
    This command may be exited via ctrl+c without affecting the request.

    [|]
    unknown error with module puppetlabs/stdlib

    Operation executed, but no changes were made.

Problem
^^^^^^^

This can be caused by an SSL verification error on the client. If the repository
is published over HTTPS and the ``puppet module install`` tool is not able to
verify the server's SSL certificate against a trusted CA, the ``puppet module install``
tool will return an error. Unfortunately, this is one of the cases where that tool
offers to return JSON output but then fails to do so, and thus Pulp is not able
to parse the error message. As soon as that behavior is fixed upstream, Pulp
will pass the error message through instead of reporting "unknown error".

Verification
^^^^^^^^^^^^

You can verify by running the following command on the consumer machine and
looking for a similar error message about SSL. Adjust the "consumer_id" and
"hostname" as appropriate.

::

    $ sudo puppet module install --module_repository=http://consumer_id:.@hostname puppetlabs/stdlib
    Preparing to install into /etc/puppet/modules ...
    Downloading from http://consumer_id:.@hostname ...
    Error: SSL_connect returned=1 errno=0 state=SSLv3 read server certificate B: certificate verify failed
    Error: Try 'puppet help module install' for usage

Solution
^^^^^^^^

Either don't publish repositories over HTTPS, or make sure the ``puppet module
install`` tool is able to verify the server's SSL certificate with a trusted CA.
Details on how to install a new trusted CA are outside the scope of this
document.

