# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0


%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}


# ---- Pulp (puppet) -----------------------------------------------------------

Name: pulp-puppet
Version: 2.0.6
Release: 0.10.beta
Summary: Support for Puppet content in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
BuildRequires:  rpm-python

%description
Provides a collection of platform plugins, client extensions and agent
handlers that provide Puppet support.

%prep
%setup -q

%build
pushd pulp_puppet_common
%{__python} setup.py build
popd
pushd pulp_puppet_extensions_admin
%{__python} setup.py build
popd
pushd pulp_puppet_plugins
%{__python} setup.py build
popd
pushd pulp_puppet_handlers
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}
pushd pulp_puppet_common
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd pulp_puppet_extensions_admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd pulp_puppet_plugins
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd pulp_puppet_handlers
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

# Directories
mkdir -p %{buildroot}/%{_sysconfdir}/pulp/agent/conf.d
mkdir -p %{buildroot}/%{_usr}/lib
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins/types
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/agent/handlers
mkdir -p %{buildroot}/%{_var}/www/pulp_puppet
mkdir -p %{buildroot}/%{_var}/www/pulp_puppet/http
mkdir -p %{buildroot}/%{_var}/www/pulp_puppet/https

# Configuration
cp -R pulp_puppet_plugins/etc/httpd %{buildroot}/%{_sysconfdir}
cp -R pulp_puppet_extensions_admin/etc/pulp %{buildroot}/%{_sysconfdir}

# Agent Handlers
cp pulp_puppet_handlers/etc/pulp/agent/conf.d/* %{buildroot}/%{_sysconfdir}/pulp/agent/conf.d/

# Types
cp -R pulp_puppet_plugins/pulp_puppet/plugins/types/* %{buildroot}/%{_usr}/lib/pulp/plugins/types/

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}


# define required pulp platform version
%global pulp_version %{version}-%{release}


# ---- Puppet Common -----------------------------------------------------------

%package -n python-pulp-puppet-common
Summary: Pulp Puppet support common library
Group: Development/Languages
Requires: python-pulp-common = %{pulp_version}
Requires: python-setuptools

%description -n python-pulp-puppet-common
A collection of modules shared among all Puppet components.

%files -n python-pulp-puppet-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/pulp_puppet
%{python_sitelib}/pulp_puppet/__init__.py*
%{python_sitelib}/pulp_puppet/common/
%{python_sitelib}/pulp_puppet_common*.egg-info
%doc


# ---- Plugins -----------------------------------------------------------------

%package plugins
Summary: Pulp Puppet plugins
Group: Development/Languages
Requires: python-pulp-common = %{pulp_version}
Requires: python-pulp-puppet-common = %{pulp_version}
Requires: pulp-server = %{pulp_version}
Requires: python-setuptools

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Puppet specific support.

%files plugins

%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_puppet.conf
%{_usr}/lib/pulp/plugins/types/puppet.json
%{python_sitelib}/pulp_puppet_plugins*.egg-info

%defattr(-,apache,apache,-)
%{_var}/www/pulp_puppet/

%doc


# ---- Admin Extensions --------------------------------------------------------

%package admin-extensions
Summary: The Puppet admin client extensions
Group: Development/Languages
Requires: python-pulp-common = %{pulp_version}
Requires: python-pulp-puppet-common = %{pulp_version}
Requires: pulp-admin-client = %{pulp_version}
Requires: python-setuptools
Obsoletes: python-pulp-puppet-extension

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Puppet specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/admin/conf.d/puppet.conf
%{python_sitelib}/pulp_puppet/extensions/
%{python_sitelib}/pulp_puppet_extensions_admin*.egg-info
%doc


# ---- Agent Handlers ----------------------------------------------------------

%package handlers
Summary: Pulp agent puppet handlers
Group: Development/Languages
Requires: python-pulp-agent-lib = %{pulp_version}

%description handlers
A collection of handlers that provide both Linux and Puppet specific
functionality within the Pulp agent.  This includes Puppet install, update,
uninstall; Puppet profile reporting; binding through yum repository
management and Linux specific commands such as system reboot.

%files handlers
%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet/handlers/
%{_sysconfdir}/pulp/agent/conf.d/puppet.conf
%{python_sitelib}/pulp_puppet_handlers*.egg-info
%doc


%changelog
* Thu Nov 29 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.10.beta
- 866491 - Added translation from server-side property name to client-side flag
  (jason.dobies@redhat.com)
- 862290 - Added support for non-Puppet repo listing (jason.dobies@redhat.com)
- 880229 - I think we need to create these as well. (jason.dobies@redhat.com)
- 880229 - Apache needs to be able to write to the publish directories
  (jason.dobies@redhat.com)

* Mon Nov 26 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.9.beta
- 

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.8.beta
- 

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.7.beta
- 

* Tue Nov 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.3.beta
- 

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.2.beta
- 

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.1.beta
- 

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 0.0.338-1
- 

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 0.0.337-1
- 873739 - using the new entry point name that specifies these as admin
  extensions. (mhrivnak@redhat.com)

* Mon Nov 05 2012 Jeff Ortel <jortel@redhat.com> 0.0.336-1
- 868022 - updating CLI section descriptions (mhrivnak@redhat.com)

* Tue Oct 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.335-1
- 871151 - Updated repo create for new API (jason.dobies@redhat.com)

* Mon Oct 29 2012 Jeff Ortel <jortel@redhat.com> 0.0.334-1
- version alignemnt

* Mon Oct 22 2012 Jeff Ortel <jortel@redhat.com> 0.0.333-1
- version alignment

* Wed Oct 17 2012 Jeff Ortel <jortel@redhat.com> 0.0.332-1
- Version alignment

* Tue Oct 16 2012 Jeff Ortel <jortel@redhat.com> 0.0.331-1
- new package built with tito

* Fri Oct 05 2012 Jeff Ortel <jortel@redhat.com> 0.0.331-1
- 860408 - repo group member adding and removing now honors the --repo-id
  option, includes a new --all flag, and fails if no matching options are
  passed. (mhrivnak@redhat.com)

* Tue Oct 02 2012 Jeff Ortel <jortel@redhat.com> 0.0.330-1
- Version alignment.

* Sun Sep 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.329-1
- Version alignment.

* Fri Sep 21 2012 Jeff Ortel <jortel@redhat.com> 0.0.328-1
- Version alignment.

* Thu Sep 20 2012 Jeff Ortel <jortel@redhat.com> 0.0.327-2
- Fix build errors.

* Thu Sep 20 2012 Jeff Ortel <jortel@redhat.com> 0.0.327-1
- new package built with tito
