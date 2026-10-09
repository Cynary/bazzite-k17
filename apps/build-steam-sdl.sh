#!/bin/bash
set -euo pipefail
export PKG_CONFIG_LIBDIR=/usr/lib/pkgconfig:/usr/share/pkgconfig
unset PKG_CONFIG_PATH LD_LIBRARY_PATH
cmake -S /build/steam-sdl -B /build/steam-sdl/build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS=-m32 -DCMAKE_CXX_FLAGS=-m32 \
    -DSDL_KMSDRM=OFF -DSDL_STATIC=OFF -DSDL_TEST_LIBRARY=OFF
cmake --build /build/steam-sdl/build --parallel "${JOBS:-$(nproc)}"
cd /build/flydigi-control
cc -m32 -shared -fPIC -Wall -Wextra -Werror experimental/steam-sdl/preload.c \
    -ldl -pthread -o /build/preload.so
cc -m32 -Wall -Wextra -Werror experimental/steam-sdl/test-loader.c \
    -ldl -o /build/test-loader
library=$(readlink -f /build/steam-sdl/build/libSDL3.so.0)
# A real ELF test checks dlopen and dlmopen and verifies child environment cleanup.
mkdir -p /build/steam-original
cp "$library" /build/steam-original/libSDL3.so.0
FLYDIGI_SDL_LIBRARY="$library" FLYDIGI_SAVED_PRELOAD= \
    LD_PRELOAD="/build/preload.so:$library" \
    /build/test-loader /build/steam-original/libSDL3.so.0 "$library"
(cd /build/steam-sdl && python3 validation/replay-flydigi.py && python3 validation/replay-linux-handoff.py)
python3 -m unittest discover -s tests -p test_steam_launcher.py -v
python3 packaging/steam-sdl/install.py /out/steam-sdl "$library" /build/preload.so
mkdir -p /out/steam-sdl/usr/share/licenses/moonmachine-steam-sdl
cp /build/steam-sdl/LICENSE.txt /out/steam-sdl/usr/share/licenses/moonmachine-steam-sdl/SDL.txt
cp LICENSE /out/steam-sdl/usr/share/licenses/moonmachine-steam-sdl/flydigi-control.txt
mkdir -p /out/steam-sdl/usr/share/moonmachine/sources
# Preserve the fork and matching integration sources with the image.
tar --exclude=.git --exclude=build --exclude=__pycache__ -C /build -cJf \
    /out/steam-sdl/usr/share/moonmachine/sources/steam-sdl.tar.xz steam-sdl flydigi-control
