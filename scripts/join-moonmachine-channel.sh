#!/bin/bash
set -euo pipefail
# Run from a trusted checkout of this repository on an existing Bazzite system.
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
test -e /run/ostree-booted
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
image=ghcr.io/cynary/bazzite-k17
# Keep the current OS as a recovery option before switching.
status=$(bootc status --json)
if python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["status"]["staged"] else 1)' <<< "$status"; then
 echo 'A system update is already waiting. Reboot to finish it, then run this again.' >&2
 exit 1
fi
index=$(rpm-ostree status --json | python3 -c 'import json,sys; d=json.load(sys.stdin)["deployments"]; print(next(i for i,x in enumerate(d) if x.get("booted")))')
ostree admin pin "$index"
# Verify before installing the repository's trust policy. Review/trust cosign.pub first.
digest=$(skopeo inspect --format '{{.Digest}}' "docker://$image:moonmachine")
cosign verify --key "$repo/cosign.pub" --insecure-ignore-tlog=true "$image@$digest" >/dev/null
install -d -m 755 /etc/pki/containers /etc/containers/registries.d
install -D -m 644 "$repo/cosign.pub" /etc/pki/containers/cynary-k17.pub
install -D -m 644 "$repo/channel/cynary-k17.yaml" /etc/containers/registries.d/cynary-k17.yaml
if [[ ! -e /etc/containers/policy.json.before-k17 ]]; then
 cp -a /etc/containers/policy.json /etc/containers/policy.json.before-k17
fi
python3 "$repo/scripts/configure-signature-policy.py"
bootc switch --enforce-container-sigpolicy "$image:moonmachine"
echo 'Moonmachine is ready. Reboot to start it.'
