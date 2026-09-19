#!/bin/bash
# Run as root on the installed K17; image kargs.d supplies defaults for new installs.
set -euo pipefail
[[ $EUID == 0 ]]
[[ $(cat /sys/class/dmi/id/product_name) == 'NucBox K17' ]]
backup=/var/lib/k17-boot-backup
mkdir -p "$backup"
if [[ -e /boot/grub2/custom.cfg ]] && ! grep -q '^# K17 graphical boot' /boot/grub2/custom.cfg; then
 echo 'Existing custom GRUB configuration requires merging; refusing to overwrite.' >&2
 exit 1
fi
if [[ ! -e "$backup/cmdline" ]]; then
 cp /proc/cmdline "$backup/cmdline"
 cp /boot/grub2/grub.cfg "$backup/grub.cfg"
fi
cat > /boot/grub2/custom.cfg <<'GRUB'
# K17 graphical boot. Keep explicit recovery/menu requests visible.
if [ "${timeout}" = "1" -a "${boot_counter}" != "-1" ]; then
  set timeout_style=hidden
  set timeout=1
fi
set gfxpayload=keep
GRUB
rpm-ostree kargs \
 --delete-if-present=drm.debug=0x6 --delete-if-present=log_buf_len=8M \
 --append-if-missing=quiet --append-if-missing=rhgb \
 --append-if-missing=loglevel=0 --append-if-missing=systemd.show_status=false \
 --append-if-missing=rd.systemd.show_status=false \
 --append-if-missing=rd.udev.log_level=3 --append-if-missing=udev.log_level=3 \
 --append-if-missing=vt.global_cursor_default=0
