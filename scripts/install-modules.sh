#!/bin/bash
set -euo pipefail
kver=$(cat /usr/share/k17-frl/build/kernel-release)
test "$kver" = "${KERNEL_RELEASE:?}"
test -s "/usr/lib/modules/$kver/vmlinuz"
# This image changes no kernel RPMs and removes no controller modules.
mkdir -p "/usr/lib/modules/$kver/updates/k17" /usr/lib/depmod.d /usr/lib/modprobe.d
install -m0644 /usr/share/k17-frl/build/{xe,drm_display_helper,xone_dongle,mt7921-common}.ko "/usr/lib/modules/$kver/updates/k17/"
printf 'override xe %s updates/k17\noverride drm_display_helper %s updates/k17\n' "$kver" "$kver" > /usr/lib/depmod.d/99-k17-frl.conf
printf 'override xone_dongle %s updates/k17\n' "$kver" >> /usr/lib/depmod.d/99-k17-frl.conf
printf 'override mt7921_common %s updates/k17\n' "$kver" >> /usr/lib/depmod.d/99-k17-frl.conf
printf 'options xe experimental_hdmi_vrr=1\n' > /usr/lib/modprobe.d/k17-frl.conf
depmod -a "$kver"
for mod in xe drm_display_helper xone_dongle mt7921-common; do
 selected=$(modinfo -k "$kver" -n "$mod")
 test "$selected" = "/lib/modules/$kver/updates/k17/$mod.ko" || test "$selected" = "/usr/lib/modules/$kver/updates/k17/$mod.ko"
done
# Follow Bazzite's generic image initramfs recipe, explicitly including our pair.
dracut --no-hostonly --kver "$kver" --reproducible --zstd --add ostree --add fido2 \
 --add-drivers 'xe drm_display_helper xone_dongle mt7921_common mei_me mei_gsc_proxy' -f "/usr/lib/modules/$kver/initramfs.img"
chmod 0600 "/usr/lib/modules/$kver/initramfs.img"
lsinitrd "/usr/lib/modules/$kver/initramfs.img" > /usr/share/k17-frl/build/initramfs-files.txt
for mod in xe drm_display_helper xone_dongle mt7921-common; do
 grep -q "updates/k17/$mod.ko" /usr/share/k17-frl/build/initramfs-files.txt
done
# Xe loads early; include its GSC proxy companion before the initramfs timeout.
for mod in mei_me mei_gsc_proxy; do
 # Module names may use underscores while their filenames use hyphens.
 module_file=$(basename "$(modinfo -k "$kver" -n "$mod")")
 grep -Fq "/$module_file" /usr/share/k17-frl/build/initramfs-files.txt
done
# Record that the stock kernel and third-party module package set are retained.
rpm -qa 'kernel*' '*xone*' '*xpadneo*' | sort > /usr/share/k17-frl/build/kernel-packages.txt
rm /usr/share/k17-frl/build/{xe,drm_display_helper,xone_dongle,mt7921-common}.ko
