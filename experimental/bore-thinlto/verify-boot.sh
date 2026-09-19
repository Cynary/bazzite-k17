#!/bin/bash
set -euo pipefail
expected=$(cat /usr/share/k17-bore/build/kernel-release)
test "$(uname -r)" = "$expected"
sha256sum -c /usr/share/k17-bore/build/vmlinuz.sha256
for setting in SCHED_BORE LTO_CLANG_THIN DEBUG_INFO_BTF; do
 zgrep -qx "CONFIG_${setting}=y" /proc/config.gz
done
test "$(cat /proc/sys/kernel/sched_bore)" = 1
test "$(cat /sys/kernel/sched_ext/state)" = disabled
systemctl is-active sshd sddm NetworkManager
ip -4 addr show enp86s0 | grep 'inet '
grep -q '^xe ' /proc/modules
grep -q '^xone_dongle ' /proc/modules
for mod in xe drm_display_helper mt7921_common xone_dongle xone_gip xone_gip_gamepad; do
 test "$(modinfo -F vermagic "$mod" | cut -d' ' -f1)" = "$expected"
done
if journalctl -b -k --no-pager | grep -Ei 'BUG:|Oops:|kernel panic|GPU HANG|flip_done timed out|CPU pipe.*underrun|Unable to handle kernel'; then
 echo 'Critical kernel diagnostic found'; exit 1
fi
printf 'K17 BORE boot health check passed. Visual and performance tests remain separate.\n'
