#!/bin/bash
set -euo pipefail
# This script runs only in the disposable image build, never on the live host.
# Follow Bazzite's image-build kernel-install shims; restore on exit.
for hook in 05-rpmostree.install 50-dracut.install; do
 cp -a "/usr/lib/kernel/install.d/$hook" "/tmp/$hook.k17-backup"
 printf '#!/bin/sh\nexit 0\n' > "/usr/lib/kernel/install.d/$hook"
done
restore_hooks() {
 for hook in 05-rpmostree.install 50-dracut.install; do
  cp -a "/tmp/$hook.k17-backup" "/usr/lib/kernel/install.d/$hook"
  rm "/tmp/$hook.k17-backup"
 done
}
trap restore_hooks EXIT
old=$(rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}' kernel-core)
mapfile -t old_kmods < <(rpm -qa --qf '%{NAME}\n' | grep '^kmod-' | grep -v '^kmod-libs$')
rpm -e --nodeps "${old_kmods[@]}" kernel kernel-core kernel-modules kernel-devel kernel-devel-matched
# The new modules package provides usbip and rebuilt xone capabilities.
# Unmatched specialty add-ons are not supported by this K17-only experiment.
dnf5 versionlock delete kernel kernel-core kernel-modules kernel-devel kernel-devel-matched
dnf5 --disable-repo='*' -y --setopt=protect_running_kernel=False --setopt=disable_excludes=all install --allowerasing /tmp/k17-bore-rpms/*.rpm
dnf5 versionlock add kernel kernel-core kernel-modules kernel-devel kernel-devel-matched
# Remove companion packages whose optional out-of-tree modules were removed.
# Keep xone-kmod-common: our rebuilt modules satisfy its capability.
dnf5 --disable-repo='*' -y --setopt=clean_requirements_on_remove=False remove \
 displaylink gcadapter_oc hid-fanatecff hid-fanatecff-akmod-modules \
 hid-tmff2 hid-tmff2-akmod-modules kvmfr nct6687d new-lg4ff \
 new-lg4ff-akmod-modules openrazer ryzen_smu ryzen_smu-akmod-modules \
 sc0710 system76-driver system76-io t150-driver v4l2loopback \
 zenergy zenergy-akmod-modules
dnf5 --disable-repo='*' check
rm -rf "/usr/lib/modules/$old"
kver=$(rpm -q --qf '%{VERSION}-%{RELEASE}' kernel-core)+
test -s "/usr/lib/modules/$kver/vmlinuz"
mkdir -p /usr/share/k17-bore/build
cp "/usr/lib/modules/$kver/config" /usr/share/k17-bore/build/kernel.config
printf '%s\n' "$kver" > /usr/share/k17-bore/build/kernel-release
sha256sum "/usr/lib/modules/$kver/vmlinuz" > /usr/share/k17-bore/build/vmlinuz.sha256
for setting in SCHED_BORE LTO_CLANG_THIN; do grep -qx "CONFIG_${setting}=y" /usr/share/k17-bore/build/kernel.config; done
! grep -qx 'CONFIG_AUTOFDO_CLANG=y' /usr/share/k17-bore/build/kernel.config
mkdir -p /usr/lib/systemd/system/scx_loader.service.d
printf '[Unit]\nConditionPathExists=!/proc/sys/kernel/sched_bore\n' > /usr/lib/systemd/system/scx_loader.service.d/50-k17-bore.conf
depmod -a "$kver"
for mod in xe drm_display_helper mt7921_common xone_dongle xone_gip xone_gip_gamepad; do
 test "$(modinfo -k "$kver" -F vermagic "$mod" | cut -d' ' -f1)" = "$kver"
done
# Kernel RPMs are supplied separately from the source tree. Reject stale artifacts.
xe_module=$(modinfo -k "$kver" -n xe)
python3 /usr/libexec/k17-verify-frl-module "$xe_module"
sha256sum "$xe_module" > /usr/share/k17-bore/build/xe.sha256
# Refuse older module RPMs that omit the tested firmware reset and suspend fixes.
# Refresh this identity when rebuilding xone from changed sources/toolchains.
xone_srcversion=$(modinfo -k "$kver" -F srcversion xone_dongle)
test "$xone_srcversion" = 3DBD258ECD8E759A6E35105
sha256sum "$(modinfo -k "$kver" -n xone_dongle)" > /usr/share/k17-bore/build/xone.sha256
printf '%s\n' "$xone_srcversion" > /usr/share/k17-bore/build/xone-srcversion
# The original adapter now uses the shared 2017 firmware, including during early boot.
xz -dc /usr/lib/firmware/xone_dongle_02fe.bin.xz | sha256sum | grep -q '^48084d9fa53b9bb04358f3bb127b7495dc8f7bb0b3ca1437bd24ef2b6eabdf66 '
# Xone requests firmware dynamically, so dracut cannot infer these names from modinfo.
xone_firmware=$(printf '%s ' /usr/lib/firmware/xone_dongle_*.bin.xz)
dracut --install "$xone_firmware" --no-hostonly --kver "$kver" --reproducible --zstd --add ostree --add fido2 --add-drivers 'xe drm_display_helper xone_dongle mei_me mei_gsc_proxy' -f "/usr/lib/modules/$kver/initramfs.img"
chmod 0600 "/usr/lib/modules/$kver/initramfs.img"
lsinitrd "/usr/lib/modules/$kver/initramfs.img" > /usr/share/k17-bore/build/initramfs-files.txt
dnf5 --disable-repo='*' check
rpm -qa | sort > /usr/share/k17-bore/build/packages.txt
