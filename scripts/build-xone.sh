#!/bin/bash
set -euo pipefail
: "${KERNEL_RELEASE:?}" "${XONE_SOURCE_COMMIT:?}"
mkdir -p /work/xone
curl --fail --location --retry 3 "https://codeload.github.com/OpenGamingCollective/xonedo/tar.gz/${XONE_SOURCE_COMMIT}" -o /work/xone.tar.gz
sha256sum /work/xone.tar.gz > /out/xone-source-archive.sha256
tar -xzf /work/xone.tar.gz -C /work/xone --strip-components=1
cd /work/xone
for patch in /work/xone-patches/*.patch; do
 git apply --check "$patch"
 git apply "$patch"
done
make -C /work/kernel M=/work/xone -j"${BUILD_JOBS:-4}" modules
test "$(modinfo -F srcversion xone_gip.ko)" = "$(modinfo -F srcversion /work/stock-xone-gip.ko.xz)"
# Only transport changes; retain the packaged GIP/controller modules.
cp xone_dongle.ko /out/
strip --strip-debug /out/xone_dongle.ko
test "$(modinfo -F vermagic /out/xone_dongle.ko | cut -d' ' -f1)" = "$KERNEL_RELEASE"
readelf -S /out/xone_dongle.ko | grep -q '\.BTF'
printf '%s\n' "$XONE_SOURCE_COMMIT" > /out/xone-source-commit
(cd /work/xone-patches && sha256sum *.patch) > /out/xone-patches.sha256
(cd /out && sha256sum *.ko kernel.config > SHA256SUMS)
