#!/bin/bash
set -euo pipefail
: "${KERNEL_RELEASE:?}" "${SOURCE_COMMIT:?}" "${SOURCE_BASE_COMMIT:?}"
mkdir -p /work/source /out
curl --fail --location --retry 3 "https://codeload.github.com/OpenGamingCollective/linux/tar.gz/${SOURCE_BASE_COMMIT}" -o /work/source.tar.gz
sha256sum /work/source.tar.gz > /out/source-archive.sha256
tar -xzf /work/source.tar.gz -C /work/source --strip-components=1 --wildcards \
  'linux-*/drivers/net/wireless/mediatek/mt76/*' 'linux-*/drivers/gpu/drm/*' 'linux-*/include/drm/*' 'linux-*/scripts/extract-vmlinux'
cd /work/source
for patch in /work/patches/*.patch; do
 git apply --check "$patch"
 git apply "$patch"
done
for patch in /work/wifi-patches/*.patch; do
 git apply --check "$patch"
 git apply "$patch"
done
(cd /work/wifi-patches && sha256sum *.patch) > /out/wifi-patches.sha256
(cd /work/patches && sha256sum *.patch) > /out/patches.sha256
printf '%s\n' "$SOURCE_BASE_COMMIT" > /out/source-base-commit
cp -a /work/source/drivers/gpu/drm/. /work/kernel/drivers/gpu/drm/
cp -a /work/source/include/drm/. /work/kernel/include/drm/
mkdir -p /work/kernel/drivers/net/wireless/mediatek/mt76
cp -a /work/source/drivers/net/wireless/mediatek/mt76/. /work/kernel/drivers/net/wireless/mediatek/mt76/
bash /work/source/scripts/extract-vmlinux /work/stock-vmlinuz > /work/kernel/vmlinux
cd /work/kernel
test "$(cat include/config/kernel.release)" = "$KERNEL_RELEASE"
make -j"${BUILD_JOBS:-4}" M=drivers/gpu/drm/display modules
make -j"${BUILD_JOBS:-4}" M=drivers/gpu/drm/xe KBUILD_EXTRA_SYMBOLS=/work/kernel/drivers/gpu/drm/display/Module.symvers modules
cp drivers/gpu/drm/xe/xe.ko drivers/gpu/drm/display/drm_display_helper.ko /out/
make -j"${BUILD_JOBS:-4}" M=drivers/net/wireless/mediatek/mt76/mt7921 modules
cp drivers/net/wireless/mediatek/mt76/mt7921/mt7921-common.ko /out/
strip --strip-debug /out/*.ko
for module in /out/*.ko; do
 test "$(modinfo -F vermagic "$module" | cut -d' ' -f1)" = "$KERNEL_RELEASE"
 readelf -S "$module" | grep -q '\.BTF'
done
cp .config /out/kernel.config
cp drivers/gpu/drm/xe/Module.symvers /out/xe.Module.symvers
cp drivers/gpu/drm/display/Module.symvers /out/display.Module.symvers
printf '%s\n' "$KERNEL_RELEASE" > /out/kernel-release
printf '%s\n' "$SOURCE_COMMIT" > /out/source-commit
gcc --version > /out/compiler.txt
(cd /out && sha256sum *.ko kernel.config > SHA256SUMS)
sha256sum /work/stock-vmlinuz > /out/stock-vmlinuz.sha256
