from gettext import gettext as _

from pulp.common.error_codes import Error

PUP0001 = Error("PUP0001", _("Could not find metadata file inside Puppet module"), [])
PUP0002 = Error("PUP0002", _("Could not extract Puppet module."), [])
PUP0003 = Error("PUP0003", _("Invalid Puppet module name %(name)s in module metadata."),
                ['name'])
