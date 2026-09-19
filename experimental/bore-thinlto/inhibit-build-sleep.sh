#!/bin/bash
# Run on the K17 after starting the build container. No persistent sleep-policy changes.
set -euo pipefail
container=${1:-k17-bore-build}
uid=$(id -u)
user=$(id -un)
[ "$(podman inspect "$container" --format '{{.State.Running}}')" = true ]
sudo systemd-run --unit=k17-build-awake --collect \
 /usr/bin/systemd-inhibit --what=idle:sleep --mode=block \
 --who='K17 kernel build' --why='Keep the K17 awake until kernel compilation finishes' \
 /usr/sbin/runuser -u "$user" -- /usr/bin/env "XDG_RUNTIME_DIR=/run/user/$uid" \
 /usr/bin/podman wait "$container"
