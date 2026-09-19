#!/bin/bash
set -euo pipefail
: "${SOURCE_DIR:?}" "${BUILD_DIR:?}" "${XONE_DIR:?}" "${STAGE_DIR:?}"
kver=$(cat "$BUILD_DIR/include/config/kernel.release")
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 LD='ld.lld --threads=2' M="$XONE_DIR" -j4 modules
mkdir -p "$STAGE_DIR/usr/lib/modules/$kver" "$STAGE_DIR/usr/src/kernels/$kver"
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 LD='ld.lld --threads=2' INSTALL_MOD_PATH="$STAGE_DIR/usr" INSTALL_MOD_STRIP=1 DEPMOD=true modules_install
install -m644 "$BUILD_DIR/arch/x86/boot/bzImage" "$STAGE_DIR/usr/lib/modules/$kver/vmlinuz"
install -m644 "$BUILD_DIR/System.map" "$STAGE_DIR/usr/lib/modules/$kver/System.map"
install -m644 "$BUILD_DIR/.config" "$STAGE_DIR/usr/lib/modules/$kver/config"
gzip -c "$BUILD_DIR/Module.symvers" > "$STAGE_DIR/usr/lib/modules/$kver/symvers.gz"
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 run-command KBUILD_RUN_COMMAND="$SOURCE_DIR/scripts/package/install-extmod-build $STAGE_DIR/usr/src/kernels/$kver"
cp "$BUILD_DIR/.config" "$STAGE_DIR/usr/src/kernels/$kver/.config"
ln -sfn "/usr/src/kernels/$kver" "$STAGE_DIR/usr/lib/modules/$kver/build"
if test -L "$STAGE_DIR/usr/lib/modules/$kver/source"; then unlink "$STAGE_DIR/usr/lib/modules/$kver/source"; fi
mkdir -p "$STAGE_DIR/usr/lib/modules/$kver/extra/xone"
for module in "$XONE_DIR"/*.ko; do
 target="$STAGE_DIR/usr/lib/modules/$kver/extra/xone/$(basename "$module")"
 cp "$module" "$target"
 llvm-strip --strip-debug "$target"
 "$BUILD_DIR/scripts/sign-file" sha512 "$BUILD_DIR/certs/signing_key.pem" "$BUILD_DIR/certs/signing_key.x509" "$target"
 test "$(modinfo -F vermagic "$target" | cut -d' ' -f1)" = "$kver"
done
printf '%s\n' "$kver" > "$STAGE_DIR/kernel-release"
# Private signing keys must never enter an image or public artifact.
test -z "$(find "$STAGE_DIR" -name '*.pem' -print -quit)"
tar -czf "$STAGE_DIR/../kernel-bore-stage.tar.gz" -C "$STAGE_DIR" usr
