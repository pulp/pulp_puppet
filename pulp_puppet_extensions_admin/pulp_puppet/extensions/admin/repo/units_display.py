# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Methods to handle the rendering of a unit list returned from either the copy
or remove units commands.
"""

from gettext import gettext as _


MODULE_ID_TEMPLATE = '%(author)s-%(name)s-%(version)s'


def display_modules(prompt, modules, module_count_threshold):
    if len(modules) == 0:
        prompt.write(_('No modules matched the given criteria.'), tag='too-few')

    elif len(modules) >= module_count_threshold:
        prompt.write(_('%s modules were affected.') % len(modules), tag='too-many')

    else:
        prompt.write(_('Modules:'), tag='just-enough')
        modules.sort(key=lambda x : x['unit_key']['author'])
        for m in modules:
            module_id = MODULE_ID_TEMPLATE % m['unit_key']
            prompt.write('  %s' % module_id, tag='module')
