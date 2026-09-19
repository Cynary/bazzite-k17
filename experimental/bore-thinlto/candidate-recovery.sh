#!/bin/bash
set -euo pipefail
state=/var/lib/k17-candidate-check
[ -e "$state/armed" ] || exit 0
rm "$state/armed"
if [ -x /usr/libexec/k17-verify-bore ]; then
 verifier=/usr/libexec/k17-verify-bore
elif [ -d /usr/share/k17-frl/build ]; then
 verifier=/usr/local/sbin/k17-verify-candidate
else
 exit 0
fi
if "$verifier" > "$state/result.log" 2>&1; then exit 0; fi
fallback=$(cat "$state/fallback")
index=$(rpm-ostree status --json | python3 -c 'import json,sys; target=sys.argv[1]; ds=json.load(sys.stdin)["deployments"]; print(next(i for i,d in enumerate(ds) if d["checksum"]==target))' "$fallback")
ostree admin set-default "$index"
echo 'Candidate health check failed; rebooting to pinned known-good deployment.' >> "$state/result.log"
systemctl reboot
