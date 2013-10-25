#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import optparse
import os
import shutil
import sys

WARNING_COLOR = '\033[31m'
WARNING_RESET = '\033[0m'

DIRS = (
    '/var/www/pulp_puppet/http/repos',
    '/var/www/pulp_puppet/https/repos',
)

#
# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
# Please keep alphabetized and by subproject

# Standard directories
DIR_PLUGINS = '/usr/lib/pulp/plugins'

LINKS = (
    ('pulp_puppet_plugins/etc/httpd/conf.d/pulp_puppet.conf', '/etc/httpd/conf.d/pulp_puppet.conf'),
    ('pulp_puppet_plugins/etc/pulp/vhosts80/pulp_puppet.conf', '/etc/pulp/vhosts80/pulp_puppet.conf'),
    ('pulp_puppet_plugins/srv/pulp/puppet_forge_api.wsgi', '/srv/pulp/puppet_forge_api.wsgi'),
    # Puppet Support Plugins
    ('pulp_puppet_plugins/pulp_puppet/plugins/types/puppet.json', DIR_PLUGINS + '/types/puppet.json'),
    # Puppet Support Admin Extensions
    ('pulp_puppet_extensions_admin/etc/pulp/admin/conf.d/puppet.conf', '/etc/pulp/admin/conf.d/puppet.conf'),
    # handlers
    ('pulp_puppet_handlers/etc/pulp/agent/conf.d/puppet_bind.conf', '/etc/pulp/agent/conf.d/puppet_bind.conf'),
    ('pulp_puppet_handlers/etc/pulp/agent/conf.d/puppet_module.conf', '/etc/pulp/agent/conf.d/puppet_module.conf'),
)

def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()

    parser.add_option('-I', '--install',
                      action='store_true',
                      help='install pulp development files')
    parser.add_option('-U', '--uninstall',
                      action='store_true',
                      help='uninstall pulp development files')
    parser.add_option('-D', '--debug',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)

    parser.set_defaults(install=False,
                        uninstall=False,
                        debug=True)

    opts, args = parser.parse_args()

    if opts.install and opts.uninstall:
        parser.error('both install and uninstall specified')

    if not (opts.install or opts.uninstall):
        parser.error('neither install or uninstall specified')

    return (opts, args)


def warning(msg):
    print "%s%s%s" % (WARNING_COLOR, msg, WARNING_RESET)


def debug(opts, msg):
    if not opts.debug:
        return
    sys.stderr.write('%s\n' % msg)


def create_dirs(opts):
    for d in DIRS:
        if os.path.exists(d) and os.path.isdir(d):
            debug(opts, 'skipping %s exists' % d)
            continue
        debug(opts, 'creating directory: %s' % d)
        os.makedirs(d, 0777)


def getlinks():
    links = []
    for l in LINKS:
        if isinstance(l, (list, tuple)):
            src = l[0]
            dst = l[1]
        else:
            src = l
            dst = os.path.join('/', l)
        links.append((src, dst))
    return links


def install(opts):
    warnings = []
    create_dirs(opts)
    currdir = os.path.abspath(os.path.dirname(__file__))
    for src, dst in getlinks():
        warning_msg = create_link(opts, os.path.join(currdir,src), dst)
        if warning_msg:
            warnings.append(warning_msg)

    os.system('chown -R apache:apache /var/www/pulp_puppet')

    if warnings:
        print "\n***\nPossible problems:  Please read below\n***"
        for w in warnings:
            warning(w)
    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks():
        debug(opts, 'removing link: %s' % dst)
        if not os.path.islink(dst):
            debug(opts, '%s does not exist, skipping' % dst)
            continue
        os.unlink(dst)

    return os.EX_OK


def create_link(opts, src, dst):
    if not os.path.lexists(dst):
        return _create_link(opts, src, dst)

    if not os.path.islink(dst):
        return "[%s] is not a symbolic link as we expected, please adjust if this is not what you intended." % (dst)

    if not os.path.exists(os.readlink(dst)):
        warning('BROKEN LINK: [%s] attempting to delete and fix it to point to %s.' % (dst, src))
        try:
            os.unlink(dst)
            return _create_link(opts, src, dst)
        except:
            msg = "[%s] was a broken symlink, failed to delete and relink to [%s], please fix this manually" % (dst, src)
            return msg

    debug(opts, 'verifying link: %s points to %s' % (dst, src))
    dst_stat = os.stat(dst)
    src_stat = os.stat(src)
    if dst_stat.st_ino != src_stat.st_ino:
        msg = "[%s] is pointing to [%s] which is different than the intended target [%s]" % (dst, os.readlink(dst), src)
        return msg


def _create_link(opts, src, dst):
        debug(opts, 'creating link: %s pointing to %s' % (dst, src))
        try:
            os.symlink(src, dst)
        except OSError, e:
            msg = "Unable to create symlink for [%s] pointing to [%s], received error: <%s>" % (dst, src, e)
            return msg

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
