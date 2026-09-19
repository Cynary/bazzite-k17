#!/bin/bash
# Run as root on the booted candidate. Read-only; no TV quality claims.
set -euo pipefail
meta=/usr/share/k17-frl/build
expected=$(cat "$meta/kernel-release")
test "$(uname -r)" = "$expected"
expected_kernel_hash=$(awk '{print $1}' "$meta/stock-vmlinuz.sha256")
actual_kernel_hash=$(sha256sum "/usr/lib/modules/$expected/vmlinuz" | cut -d' ' -f1)
test "$expected_kernel_hash" = "$actual_kernel_hash"
printf 'Stock kernel image hash: %s\n' "$actual_kernel_hash"
for mod in xe drm_display_helper; do
 test -d "/sys/module/$mod"
 test -s "/sys/kernel/btf/$mod"
 modinfo -n "$mod" | grep -F "/updates/k17/$mod.ko"
done
(cd "/usr/lib/modules/$expected/updates/k17" && sha256sum *.ko)
(cd "$meta" && sha256sum --check <(grep 'kernel.config$' SHA256SUMS))
for mod in xe drm_display_helper; do
 expected_hash=$(awk -v name="$mod.ko" '$2==name {print $1}' "$meta/SHA256SUMS")
 actual_hash=$(sha256sum "/usr/lib/modules/$expected/updates/k17/$mod.ko" | cut -d' ' -f1)
 test "$expected_hash" = "$actual_hash"
done
cat /sys/module/xe/parameters/experimental_hdmi_vrr
systemctl is-active sshd cardwired sddm
if journalctl -b -k --no-pager | grep -E 'BUG:|Oops:|Kernel panic|general protection fault|Unknown symbol|Invalid module format|BTF.*(invalid|Invalid)|CPU pipe.*FIFO underrun|state mismatch|mismatch in|flip_done timed out|Atomic update failure|vblank wait timed out|GSC proxy component not bound'; then
 echo 'Kernel diagnostic failure; inspect journal before promoting.' >&2
 exit 1
fi
printf 'Stock-kernel candidate health checks passed; physical TV validation is still required.\n'
