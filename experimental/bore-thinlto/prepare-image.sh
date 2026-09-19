#!/bin/bash
set -euo pipefail
# Copy a clean image context, keeping RPM artifacts outside the source repository.
: "${RPM_DIR:?Set RPM_DIR to the matching built kernel RPM directory}"
: "${IMAGE_CONTEXT:?Set IMAGE_CONTEXT to an empty staging directory}"
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(cd "$source_dir/../.." && pwd)
mkdir -p "$IMAGE_CONTEXT"
test -z "$(ls -A "$IMAGE_CONTEXT")"
cp "$repo/Containerfile" "$source_dir/install-image.sh" "$source_dir/verify-boot.sh" "$IMAGE_CONTEXT/"
cp -a "$repo/apps" "$IMAGE_CONTEXT/"
cp -a "$repo/files" "$repo/channel" "$IMAGE_CONTEXT/"
cp "$repo/scripts/configure-signature-policy.py" "$IMAGE_CONTEXT/"
mkdir "$IMAGE_CONTEXT/rpms"
cp "$RPM_DIR"/*.rpm "$IMAGE_CONTEXT/rpms/"
