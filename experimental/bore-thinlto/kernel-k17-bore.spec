%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
%global kver 7.2.4-k17bore1+
Name: kernel
Version: 7.2.4
Release: k17bore1
Summary: K17 BORE 6.8.0 and Clang ThinLTO experimental kernel
License: GPL-2.0-only
URL: https://github.com/OpenGamingCollective/linux
Source0: kernel-bore-stage.tar.gz
Requires: kernel-core = %{version}-%{release}
Requires: kernel-modules = %{version}-%{release}
%description
Hardware test candidate: existing K17 FRL/VRR, BORE 6.8.0, ThinLTO, Wi-Fi backports and rebuilt xone. No AutoFDO.
%package core
Summary: K17 experimental kernel image
Provides: kernel-uname-r = %{kver}
Provides: kernel-core-uname-r = %{kver}
Provides: installonlypkg(kernel)
Provides: kernel-drm-nouveau = 16
Requires: kernel-modules = %{version}-%{release}
Requires: linux-firmware
%description core
Experimental boot image and kernel configuration.
%package modules
Summary: K17 experimental kernel modules
Provides: kernel-modules-uname-r = %{kver}
Provides: kernel-modules-core-uname-r = %{kver}
Provides: kernel-modules-extra-uname-r = %{kver}
Provides: kernel-modules-core = %{version}-%{release}
Provides: kernel-modules-extra = %{version}-%{release}
Provides: xone-kmod = 1000.0.0.git.1442.85e53359
Provides: kmod(usbip-core.ko)
Provides: kmod(usbip-host.ko)
Provides: kmod(vhci-hcd.ko)
Provides: installonlypkg(kernel-module)
Requires: kmod
%description modules
In-tree modules built together with the experimental kernel.
%package devel
Summary: K17 experimental kernel build headers
Provides: kernel-devel-uname-r = %{kver}
Provides: installonlypkg(kernel)
AutoReqProv: no
%description devel
Build files corresponding to this test kernel.
%package devel-matched
Summary: Matching K17 kernel and development files
Requires: kernel-core = %{version}-%{release}
Requires: kernel-devel = %{version}-%{release}
%description devel-matched
Dependency package for the matching experimental kernel.
%prep
%setup -q -c -T
%build
%install
mkdir -p %{buildroot}
tar -xzf %{SOURCE0} -C %{buildroot}
%files
%files core
/usr/lib/modules/%{kver}/vmlinuz
/usr/lib/modules/%{kver}/System.map
/usr/lib/modules/%{kver}/config
/usr/lib/modules/%{kver}/symvers.gz
%files modules
%dir /usr/lib/modules/%{kver}
/usr/lib/modules/%{kver}/kernel
/usr/lib/modules/%{kver}/extra
/usr/lib/modules/%{kver}/modules.*
%files devel
/usr/src/kernels/%{kver}
/usr/lib/modules/%{kver}/build
%files devel-matched
