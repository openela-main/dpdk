# Add option to build with examples
%bcond_with examples
# Add option to build without tools
%bcond_without tools

# Dont edit Version: and Release: directly, only these:
#% define commit0 7001c8fdb27357c67147c0a13cb3826e48c0f2bf
#% define date 20191128
#% define shortcommit0 %(c=%{commit0}; echo ${c:0:7})

%define ver 24.11.2
%define rel 3

%define srcname dpdk%(awk -F. '{ if (NF > 2) print "-stable" }' <<<%{version})

%define pyelftoolsver 0.27

Name: dpdk
Version: %{ver}
Release: %{rel}%{?commit0:.%{date}git%{shortcommit0}}%{?dist}
%if 0%{?fedora} || 0%{?rhel} > 8
Epoch: 2
%endif
URL: http://dpdk.org
%if 0%{?commit0:1}
Source: https://dpdk.org/browse/dpdk/snapshot/dpdk-%{commit0}.tar.xz
%else
Source: https://fast.dpdk.org/rel/dpdk-%{ver}.tar.xz
%endif

# Only needed for creating snapshot tarballs, not used in build itself
Source100: dpdk-snapshot.sh

Patch1: 0001-net-mlx5-avoid-setting-kernel-MTU-if-not-needed.patch

Summary: Set of libraries and drivers for fast packet processing

#
# Note that, while this is dual licensed, all code that is included with this
# Pakcage are BSD licensed. The only files that aren't licensed via BSD is the
# kni kernel module which is dual LGPLv2/BSD, and thats not built for fedora.
#
License: BSD and LGPLv2 and GPLv2

#
# The DPDK is designed to optimize througput of network traffic using, among
# other techniques, carefully crafted assembly instructions.  As such it
# needs extensive work to port it to other architectures.
ExclusiveArch: x86_64 aarch64 ppc64le

%define sdkdir  %{_datadir}/%{name}
%define docdir  %{_docdir}/%{name}
%define incdir  %{_includedir}/%{name}
%define pmddir  %{_libdir}/%{name}-pmds

%if 0%{?rhel} && 0%{?rhel} < 9
# Fix conflicts with README and MAINTAINERS (included in dpdk-doc < 18.11-2),
# this affects only RHEL8.
Conflicts: dpdk-doc < 18.11-2
%endif

BuildRequires: meson
Source1: https://github.com/eliben/pyelftools/archive/refs/tags/v%{pyelftoolsver}.tar.gz#/pyelftools-%{pyelftoolsver}.tar.gz
%if 0%{?rhel} > 8 || 0%{?fedora}
BuildRequires: python3-pyelftools
%endif
BuildRequires: gcc, zlib-devel, numactl-devel, libarchive-devel
BuildRequires: doxygen, python3-sphinx
%ifarch aarch64 x86_64
BuildRequires: rdma-core-devel >= 44
%endif

%description
The Data Plane Development Kit is a set of libraries and drivers for
fast packet processing in the user space.

%package devel
Summary: Data Plane Development Kit development files
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%ifarch x86_64
Requires: rdma-core-devel
%endif

%description devel
This package contains the headers and other files needed for developing
applications with the Data Plane Development Kit.

%package doc
Summary: Data Plane Development Kit API documentation
BuildArch: noarch

%description doc
API programming documentation for the Data Plane Development Kit.

%if %{with tools}
%package tools
Summary: Tools for setting up Data Plane Development Kit environment
Requires: %{name} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: kmod pciutils findutils iproute python3

%description tools
%{summary}
%endif

%if %{with examples}
%package examples
Summary: Data Plane Development Kit example applications
BuildRequires: libvirt-devel

%description examples
Example applications utilizing the Data Plane Development Kit, such
as L2 and L3 forwarding.
%endif

%prep
%if 0%{?rhel} && 0%{?rhel} < 9
%setup -q -a 1 -n %{srcname}-%{?commit0:%{commit0}}%{!?commit0:%{ver}}
%else
%setup -q -n %{srcname}-%{?commit0:%{commit0}}%{!?commit0:%{ver}}
%endif
%autopatch -p1

%build
%if 0%{?rhel} && 0%{?rhel} < 9
export PYTHONPATH=$(pwd)/pyelftools-%{pyelftoolsver}
%endif

ENABLED_APPS=(
    test-pmd
    test-bbdev
)

for app in "${ENABLED_APPS[@]}"; do
    enable_apps="${enable_apps:+$enable_apps,}"$app
done

ENABLED_DRIVERS=(
    bus/pci
    bus/vdev
    mempool/ring
    net/failsafe
    net/i40e
    net/ring
    net/vhost
    net/virtio
    net/tap
)

%ifarch x86_64
ENABLED_DRIVERS+=(
    baseband/acc
    bus/vmbus
    common/iavf
    common/nfp
    net/bnxt
    net/ena
    net/enic
    net/iavf
    net/ice
    net/mana
    net/netvsc
    net/nfp
    net/qede
    net/vdev_netvsc
)
%endif

%ifarch aarch64 x86_64
ENABLED_DRIVERS+=(
    bus/auxiliary
    common/mlx5
    net/e1000
    net/ixgbe
    net/mlx5
)
%endif

for driver in "${ENABLED_DRIVERS[@]}"; do
    enable_drivers="${enable_drivers:+$enable_drivers,}"$driver
done

# If doing any updates, this must be aligned with:
# https://access.redhat.com/articles/3538141
ENABLED_LIBS=(
    bbdev
    bitratestats
    bpf
    cmdline
    cryptodev
    dmadev
    gro
    gso
    hash
    ip_frag
    latencystats
    member
    meter
    metrics
    pcapng
    pdump
    security
    stack
    timer
    vhost
)

for lib in "${ENABLED_LIBS[@]}"; do
    enable_libs="${enable_libs:+$enable_libs,}"$lib
done

ln -s /usr/bin/true mandb
export PATH=$(pwd):$PATH
%meson --includedir=include/dpdk \
       --default-library=shared \
       -Ddeveloper_mode=disabled \
       -Denable_libs="$enable_libs" \
       -Ddrivers_install_subdir=dpdk-pmds \
       -Denable_apps="$enable_apps" \
       -Denable_docs=true \
       -Denable_drivers="$enable_drivers" \
       -Dplatform=generic \
       -Dmax_ethports=32 \
       -Dmax_numa_nodes=8 \
       -Dtests=false

# Check drivers and libraries
for driver in "${ENABLED_DRIVERS[@]}"; do
	config_token="RTE_$(echo "$driver" | tr [a-z/] [A-Z_])"
	! grep -Fqw "$config_token" */rte_build_config.h || continue
	echo "!!! Could not find $driver in rte_build_config.h, please check dependencies. !!!"
	false
done
for lib in "${ENABLED_LIBS[@]}"; do
	config_token="RTE_LIB_$(echo "$lib" | tr [a-z/] [A-Z_])"
	! grep -Fqw "$config_token" */rte_build_config.h || continue
	echo "!!! Could not find $lib in rte_build_config.h, please check dependencies. !!!"
	false
done
%meson_build

%install
%meson_install

rm -f %{buildroot}%{_libdir}/*.a
# Taken from debian/rules
rm -f %{buildroot}%{docdir}/html/.buildinfo
rm -f %{buildroot}%{docdir}/html/objects.inv
rm -rf %{buildroot}%{docdir}/html/.doctrees
find %{buildroot}%{_datadir}/man/ -type f -a ! -iname "*rte_*" -exec rm {} \;

%files
# BSD
%doc README MAINTAINERS
%{_bindir}/dpdk-testpmd
%{_bindir}/dpdk-test-bbdev
%dir %{pmddir}
%{_libdir}/*.so.*
%{pmddir}/*.so.*

%files doc
#BSD
%exclude %{docdir}/README
%exclude %{docdir}/MAINTAINERS
%{docdir}

%files devel
#BSD
%{incdir}/
%{sdkdir}/
%if %{with tools}
%exclude %{_bindir}/dpdk-*.py
%endif
%if %{with examples}
%exclude %{sdkdir}/examples/
%endif
%{_libdir}/*.so
%{pmddir}/*.so
%{_libdir}/pkgconfig/libdpdk.pc
%{_libdir}/pkgconfig/libdpdk-libs.pc
%{_datadir}/man
%if %{with examples}
%files examples
%{_bindir}/dpdk-*
%doc %{sdkdir}/examples/
%endif

%if %{with tools}
%files tools
%{_bindir}/dpdk-*.py
%endif

%changelog
* Tue Aug 19 2025 David Marchand <david.marchand@redhat.com> - 24.11.2-3
- Enable net/mlx5 driver for ARM (RHEL-109887)

* Thu Jun 26 2025 Maxime Coquelin <maxime.coquelin@redhat.com> - 24.11.2-2
- Avoid requiring NET_ADMIN with mlx5 (RHEL-93856)

* Mon Jun 23 2025 Kevin Traynor <ktraynor@redhat.com> - 24.11.2-1
- Rebase to 24.11.2 (RHEL-96849)

* Mon Jan 13 2025 David Marchand <david.marchand@redhat.com> - 24.11.1-2
- Enable net/ena and net/mana drivers (RHEL-73690)

* Wed Dec 18 2024 David Marchand <david.marchand@redhat.com> - 24.11.1-1
- Rebase to 24.11.1 (RHEL-71284)

* Tue Dec 17 2024 Kevin Traynor <ktraynor@redhat.com> - 23.11-2
- Backport fixes for CVE-2024-11614 (RHEL-68662)

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 2:23.11-1.2
- Bump release for October 2024 mass rebuild:
  Resolves: RHEL-64018

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 2:23.11-1.1
- Bump release for June 2024 mass rebuild

* Wed May 15 2024 Timothy Redaelli <tredaelli@redhat.com> - 23.11-1
- Aligned to cs9 (RHEL-33405)

* Wed Jan 24 2024 Fedora Release Engineering <releng@fedoraproject.org> - 2:22.11.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Fri Jan 19 2024 Fedora Release Engineering <releng@fedoraproject.org> - 2:22.11.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Wed Jul 19 2023 Fedora Release Engineering <releng@fedoraproject.org> - 2:22.11.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_39_Mass_Rebuild

* Fri Mar 03 2023 Timothy Redaelli <tredaelli@redhat.com> - 2:22.11.1-1
- Update to 22.11.1

* Thu Jan 19 2023 Fedora Release Engineering <releng@fedoraproject.org> - 2:21.11.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_38_Mass_Rebuild

* Sun Oct 23 2022 Jiri Olsa <jolsa@kernel.org> - 2:21.11.2-2
- Rebuild for libbpf 1.0.0

* Fri Sep 09 2022 Timothy Redaelli <tredaelli@redhat.com> - 2:21.11.2-1
- Update to 21.11.2 (CVE-2022-28199: bz2123550) (CVE-2022-2132: bz2122335)

* Thu Jul 21 2022 Fedora Release Engineering <releng@fedoraproject.org> - 2:21.11.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_37_Mass_Rebuild

* Wed Jul 06 2022 Timothy Redaelli <tredaelli@redhat.com> - 2:21.11.1-2
- Support compressed firmwares (bz2104418)

* Fri Apr 29 2022 Timothy Redaelli <tredaelli@redhat.com> - 2:21.11.1-1
- Update to 21.11.1

* Wed Mar 09 2022 Timothy Redaelli <tredaelli@redhat.com> - 2:21.11-1
- Update to 21.11 (bz1991248)
- Add other dependencies in order to build all the possible PMDs

* Thu Jan 20 2022 Fedora Release Engineering <releng@fedoraproject.org> - 2:20.11-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Wed Jul 21 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2:20.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Wed Feb 17 2021 Timothy Redaelli <tredaelli@redhat.com> - 2:20.11-1
- Update to 20.11

* Tue Jan 26 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2:19.11.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Tue Sep 01 2020 Jeff Law <law@redhat.com> - 2:19.11.3-2
- Re-enable LTO

* Tue Sep 01 2020 Timothy Redaelli <tredaelli@redhat.com> - 2:19.11.3-1
- Update to latest 19.11 LTS (bz1874499)

* Mon Jul 27 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2:19.11.1-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Wed Jul 01 2020 Jeff Law <law@redhat.com> - 2:19.11.1-6
- Disable LTO

* Tue Jun 23 2020 Timothy Redaelli <tredaelli@redhat.com> - 2:19.11.1-5
- Fix missing Requires for dpdk-devel (bz1843590)

* Thu Jun 04 2020 Neil Horman <nhorman@redhat.com> - 2:19.11.1-4
- Fix broken buildrequires (bz1843590)

* Thu Jun 04 2020 Neil Horman <nhorman@redhat.com> - 2:19.11.1-3
- Enable MLX5 PMD (bz 1843590)

* Thu May 07 2020 Neil Horman <nhorman@redhat.com> - 2:19.11.1-2
- Fix error in python interpreter fixup (bz 1832416)

* Mon Apr 06 2020 Timothy Redaelli <tredaelli@redhat.com> - 2:19.11-1
- Update to latest 19.11 LTS (bz1821213)

* Fri Feb 07 2020 Timothy Redaelli <tredaelli@redhat.com> - 2:18.11.6-1
- Update to latest 18.11 LTS (bz1800510)
- Add -fcommon to CFLAGS as workaround in order to make it build on GCC 10
  (bz1799289)

* Tue Jan 28 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2:18.11.2-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Mon Nov 04 2019 Timothy Redaelli <tredaelli@redhat.com> - 2:18.11.2-5
- Pass the correct LDFLAGS to host apps (dpdk-pmdinfogen) too (bz1768405)

* Wed Sep 11 2019 Than Ngo <than@redhat.com> - 2:18.11.2-4
- Fix multilib issue, different outputs on different arches

* Mon Aug 26 2019 Neil Horman <nhorman@redhat.com> - 2:18.11.2-3
- Fix csh syntax in dpdk-sdk-x86_64.csg (bz1742942)

* Wed Jul 24 2019 Fedora Release Engineering <releng@fedoraproject.org> - 2:18.11.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Tue Jun 25 2019 Timothy Redaelli <tredaelli@redhat.com> - 2:18.11.2-1
- Update to latest 18.11 LTS (bz1721056)

* Thu Feb 28 2019 Timothy Redaelli <tredaelli@redhat.com> - 2:18.11.0-1
- Update to latest LTS release (bz1684107)

* Wed Feb 13 2019 Neil Horman <nhorman@redhat.com> - 2:17.11.2-6
- Fix some FTBFS errors (1674825)

* Thu Jan 31 2019 Fedora Release Engineering <releng@fedoraproject.org> - 2:17.11.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Tue Nov 27 2018 Neil Horman <nhorman@redhat.com> - 2:17.11.2-4
- Add wdiff to BuildRequires

* Thu Sep 27 2018 Neil Horman <nhorman@tuxdriver.com> - 2:17.11.2-3
- quiet annocheck complaints (bz1548404)

* Thu Jul 12 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2:17.11.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Tue Apr 24 2018 Neil Horman <nhorman@redhat.com> 2:17.11.2-1
- Update to latest 17.11 LTS (fixes bz 1571361)

* Tue Apr 10 2018 Timothy Redaelli <tredaelli@redhat.com> - 2:17.11.1-3
- Fix Requires dpdk by adding epoch

* Fri Apr 06 2018 Neil Horman <nhorman@redhat.com> 2:17.11.1-2
- Fix aarch64 build issue

* Fri Apr 06 2018 Neil Horman <nhorman@redhat.com> 2:17.11.1-1
- Update to latest LTS release for OVS

* Fri Apr 06 2018 Timothy Redaelli <tredaelli@redhat.com> -  18.02 -6
- Replace "/usr/bin/env python" with "/usr/bin/python3" (bz 1564215)

* Thu Apr 05 2018 Neil Horman <nhorman@redhat.com> - 18.02-5
- Fix compiler flag error (bz 1548404)
- Update spec file to switch to python3

* Wed Mar 14 2018 Neil Horman <nhorman@redhat.com>< -18.02-4
- Fixing date in changelog below

* Thu Mar 08 2018 Neil Horman <nhorman@redhat.com> - 18.02-3
- Fixing missing c/ldflags for pmdinfogen (bz 1548404)

* Tue Feb 27 2018 Neil Horman <nhorman@redhat.com> - 18.02-2
- Fix rpm ldflags usage (bz 1548404)

* Mon Feb 19 2018 Neil Horman <nhorman@redhat.com> - 18.02-1
- update to latest upstream

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 17.11-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Wed Jan 03 2018 Iryna Shcherbina <ishcherb@redhat.com> - 17.11-3
- Update Python 2 dependency declarations to new packaging standards
  (See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3)

* Thu Nov 30 2017 Neil Horman <nhorman@redhat.com> - 17.11-2
- Fix dangling symlinks (bz 1519322)
- Fix devtools->usertools conversion (bz 1519332)
- Fix python-pyelftools requirement (bz 1519336)

* Thu Nov 16 2017 Neil Horman <nhorman@redhat.com> - 17.11-1
- Update to latest upstream

* Wed Aug 09 2017 Neil Horman <nhorman@redhat.com> - 17.08-1
- Update to latest upstream

* Mon Jul 31 2017 Neil Horman <nhorman@redhat.com> - 17.05-2
- backport rte_eth_tx_done_cleanup map fix (#1476341)

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 17.05-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon May 15 2017 Neil Horman <nhorman@redhat.com> - 17.05-1
- Update to latest upstream

* Fri Feb 24 2017 Neil Horman <nhorman@redhat.com> - 17-02-2
- Add python dependency (#1426561)

* Wed Feb 15 2017 Fedora Release Monitoring  <release-monitoring@fedoraproject.org> - 17.02-1
- Update to 17.02 (#1422285)

* Mon Feb 06 2017 Yaakov Selkowitz <yselkowi@redhat.com> - 16.11-2
- Enable aarch64, ppc64le (#1419731)

* Tue Nov 15 2016 Neil Horman <nhorman@redhat.com> - 16.11-1
- Update to 16.11

* Tue Aug 02 2016 Neil Horman <nhorman@redhat.com> - 16.07-1
* Update to 16.07

* Thu Apr 14 2016 Panu Matilainen <pmatilai@redhat.com> - 16.04-1
- Update to 16.04
- Drop all patches, they're not needed anymore
- Drop linker script generation, its upstream now
- Enable vhost numa support again

* Wed Mar 16 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-7
- vhost numa code causes crashes, disable until upstream fixes
- Generalize target/machine/etc macros to enable i686 builds

* Tue Mar 01 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-6
- Drop no longer needed bnx2x patch, the gcc false positive has been fixed
- Drop no longer needed -Wno-error=array-bounds from CFLAGS
- Eliminate the need for the enic patch by eliminating second -Wall from CFLAGS
- Disable unmaintained librte_power as per upstream recommendation

* Mon Feb 15 2016 Neil Horman <nhorman@redhat.com> 2.2.0-5
- Fix ftbfs isssue (1307431)

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.2.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Jan 26 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-3
- Use a different quoting method to avoid messing up vim syntax highlighting
- A string is expected as CONFIG_RTE_MACHINE value, quote it too

* Mon Jan 25 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-2
- Enable librte_vhost NUMA-awareness

* Wed Jan 20 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-1
- Update to 2.2.0
- Establish a driver directory for automatic driver loading
- Move the unversioned pmd symlinks from libdir -devel
- Make option matching stricter in spec setconf
- Spec cleanups
- Adopt upstream standard installation layout

* Thu Oct 22 2015 Aaron Conole <aconole@redhat.com> - 2.1.0-3
- Include examples binaries
- Enable the Broadcom NetXtreme II 10Gb PMD
- Fix up linkages for the dpdk-devel package

* Wed Sep 30 2015 Aaron Conole <aconole@redhat.com> - 2.1.0-2
- Re-enable the IGB, IXGBE, I40E PMDs
- Bring the Fedora and RHEL packages more in-line.

* Wed Aug 26 2015 Neil Horman <nhorman@redhat.com> - 2.1.0-1
- Update to latest version

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Mon Apr 06 2015 Neil Horman <nhorman@redhat.com> - 2.0.0-1
- Update to dpdk 2.0
- converted --with shared option to --without shared option

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-8
- Always build with -fPIC

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-7
- Policy compliance: move static libraries to -devel, provide dpdk-static
- Add a spec option to build as shared libraries

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-6
- Avoid variable expansion in the spec here-documents during build
- Drop now unnecessary debug flags patch
- Add a spec option to build a combined library

* Tue Jan 27 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-5
- Avoid unnecessary use of %%global, lazy expansion is normally better
- Drop unused destdir macro while at it
- Arrange for RTE_SDK environment + directory layout expected by DPDK apps
- Drop config from main package, it shouldn't be needed at runtime

* Tue Jan 27 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-4
- Copy the headers instead of broken symlinks into -devel package
- Force sane mode on the headers
- Avoid unnecessary %%exclude by not copying unpackaged content to buildroot
- Clean up summaries and descriptions
- Drop unnecessary kernel-devel BR, we are not building kernel modules

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.7.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jul 17 2014 - John W. Linville <linville@redhat.com> - 1.7.0-2
- Use EXTRA_CFLAGS to include standard Fedora compiler flags in build
- Set CONFIG_RTE_MACHINE=default to build for least-common-denominator machines
- Turn-off build of librte_acl, since it does not build on default machines
- Turn-off build of physical device PMDs that require kernel support
- Clean-up the install rules to match current packaging
- Correct changelog versions 1.0.7 -> 1.7.0
- Remove ix86 from ExclusiveArch -- it does not build with above changes

* Thu Jul 10 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-1.0
- Update source to official 1.7.0 release 

* Thu Jul 03 2014 - Neil Horman <nhorman@tuxdriver.com>
- Fixing up release numbering

* Tue Jul 01 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.9.1.20140603git5ebbb1728
- Fixed some build errors (empty debuginfo, bad 32 bit build)

* Wed Jun 11 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.9.20140603git5ebbb1728
- Fix another build dependency

* Mon Jun 09 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.8.20140603git5ebbb1728
- Fixed doc arch versioning issue

* Mon Jun 09 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.7.20140603git5ebbb1728
- Added verbose output to build

* Tue May 13 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.6.20140603git5ebbb1728
- Initial Build

