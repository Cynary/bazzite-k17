#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
export JOBS=${JOBS:-$(nproc)}
export PREFIX=/usr/lib/moonmachine/moonlight/usr
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib64/pkgconfig"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib64"
export HOME=/tmp/moonmachine-build-home
mkdir -p "$HOME"
mkdir -p /build "$PREFIX"
python3 "$here/checkout.py" /build

# Build the compositor and its matching WSI layer from the same pinned revision.
cd /build/gamescope
meson setup build --prefix=/usr --libdir=lib64 --buildtype=release \
    -Denable_openvr_support=false -Davif_screenshots=disabled -Dsdl2_backend=disabled
ninja -C build -j"$JOBS"
meson test -C build --print-errorlogs
DESTDIR=/out/gamescope meson install -C build

# Match the codecs and libplacebo revision used by Nonary's AppImage build.
# Qt, SDL and graphics-loader libraries come from the same Bazzite base as the OS.
fetch() {
    git init "/build/$1"
    git -C "/build/$1" fetch --depth=1 "$2" "$3"
    git -C "/build/$1" checkout --detach FETCH_HEAD
    test "$(git -C "/build/$1" rev-parse HEAD)" = "$3"
    git -C "/build/$1" submodule update --init --recursive --depth=1
}
fetch ffmpeg https://github.com/FFmpeg/FFmpeg.git 239f2c733de417201d7ad3b3b8b0d9b63285b2b1
cd /build/ffmpeg
./configure --prefix="$PREFIX" --enable-pic --disable-static --enable-shared \
    --disable-all --disable-autodetect --enable-avcodec --enable-avformat --enable-swscale \
    --enable-decoder=h264 --enable-decoder=hevc --enable-decoder=av1 \
    --enable-vaapi --enable-hwaccel=h264_vaapi --enable-hwaccel=hevc_vaapi --enable-hwaccel=av1_vaapi \
    --enable-vdpau --enable-hwaccel=h264_vdpau --enable-hwaccel=hevc_vdpau --enable-hwaccel=av1_vdpau \
    --enable-libdrm --enable-vulkan --enable-hwaccel=h264_vulkan --enable-hwaccel=hevc_vulkan --enable-hwaccel=av1_vulkan \
    --enable-libdav1d --enable-decoder=libdav1d
make -j"$JOBS"
make install
fetch libplacebo https://github.com/haasn/libplacebo.git 2d0979fb54e025e904c7372666fffbf5dae40f66
cd /build/libplacebo
git apply /build/moonlight/app/deploy/linux/appimage/*.patch
git apply --check "$here/patches/libplacebo/0001-import-packed-vaapi-444.patch"
git apply "$here/patches/libplacebo/0001-import-packed-vaapi-444.patch"
meson setup build --prefix="$PREFIX" --libdir=lib -Dbuildtype=release -Dvulkan=enabled -Dopengl=disabled -Ddemos=false
ninja -C build -j"$JOBS"
ninja -C build install

cd /build/moonlight
export CI_VERSION
CI_VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["moonlight"]["version"])' "$here/sources.json")
mkdir build-native
cd build-native
qmake6 ../moonlight-qt.pro CONFIG+=release PREFIX="$PREFIX"
make -j"$JOBS"
make install
# Fail the build if dependencies accidentally disabled the patched renderer.
grep -q -- '-DHAVE_LIBPLACEBO_VULKAN' app/Makefile*
grep -q -- '-DHAVE_LIBVA' app/Makefile*
grep -q -- '-DHAS_WAYLAND' app/Makefile*
mkdir /build/moonlight/test-native
cd /build/moonlight/test-native
export CPATH="$PREFIX/include"
CPATH="$PREFIX/include" qmake6 ../tests/tests.pro CONFIG+=tests
make -j"$JOBS"
export QT_QPA_PLATFORM=offscreen
for test in tst_vrrtimingcontroller tst_vrrratepolicy tst_vrrpacingworker tst_vrrreplayconfig; do
    binary=$(find . -type f -executable -name "$test" -print -quit)
    test -n "$binary"
    "$binary"
done

cd /build/moondeck
pnpm install --frozen-lockfile
pnpm run build
pnpm run test
python3 -m compileall -q defaults/python
# checkout.py supplies the checksum-pinned upstream Python dependency bundle;
# the frontend and backend themselves both come from the patched checkout.
mkdir -p /out/moondeck
cp -a dist defaults/python main.py package.json plugin.json LICENSE /out/moondeck/
mkdir -p /out/moonlight
cp -a "$PREFIX" /out/moonlight/usr
cat > /out/moonlight/AppRun <<'EOF'
#!/bin/bash
appdir=$(cd -- "$(dirname -- "$0")" && pwd)
export LD_LIBRARY_PATH="$appdir/usr/lib:$appdir/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$appdir/usr/bin/moonlight" "$@"
EOF
chmod +x /out/moonlight/AppRun
# Preserve corresponding patched sources and build inputs with the artifact.
mkdir -p /out/sources
tar --exclude=.git --exclude=node_modules --exclude=build --exclude=build-native --exclude=test-native \
    -C /build -cJf /out/sources/applications.tar.xz moonlight moondeck ffmpeg libplacebo gamescope
cp -a "$here" /out/sources/build
