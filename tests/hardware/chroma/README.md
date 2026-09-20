# Offline 4:4:4 renderer test

This test decodes a local HEVC file with VAAPI and imports it through the same
libplacebo FFmpeg helper used by Moonlight. It renders into an offscreen Vulkan
texture. No Windows host, stream, compositor, or connected display is needed.
It does require access to an Intel GPU render node. Run on an idle GPU for
performance measurements.

Build `probe.c` against the **same FFmpeg and libplacebo headers/libraries as the
candidate Moonlight build**. The importer lives in a header: replacing only a
shared libplacebo library will not update already-compiled Moonlight code.
For this test, FFmpeg also needs the Matroska demuxer and file protocol enabled
(`--enable-demuxer=matroska --enable-protocol=file`). The image's minimal FFmpeg
build normally omits those because streams arrive through Moonlight's transport.

```sh
export PKG_CONFIG_PATH=/path/to/prefix/lib/pkgconfig
export LD_LIBRARY_PATH=/path/to/prefix/lib
cc -O2 -Wall -pthread probe.c -o chroma-probe \
  $(pkg-config --cflags --libs libplacebo libavformat libavcodec libavutil libva) -lm
bash patterns.sh samples
./chroma-probe samples/hdr10-pattern.mkv 2 1 hardware.rgb16f
./chroma-probe samples/hdr10-pattern.mkv 3 1 reference.rgb16f
python3 compare.py hardware.rgb16f reference.rgb16f
```

`patterns.sh` requires FFmpeg with libx265. `compare.py` requires NumPy. The
lossless patterns include single-pixel chroma alternation and luma ramps, in
8-bit BT.709 and 10-bit BT.2020/PQ. Repeat the comparison with `sdr8-pattern.mkv`
and `420-pattern.mkv`. The latter guards the existing 10-bit 4:2:0 path.

Arguments are `FILE MODE FRAME_COUNT [FIRST_FRAME_RGBA16F_OUTPUT]`. Modes:

- `0`: hardware decode with an explicit completion wait.
- `1`: hardware decode and libplacebo import only.
- `2`: hardware decode, import, and offscreen render.
- `3`: software decode and offscreen render, as a colour reference.
- `4`: hardware decode with an early DRM PRIME mapping, followed by import and
  render. This covers Moonlight's retained-mapping path.
- `5`: the early-mapping renderer with a decoder thread and a three-frame queue,
  allowing decode and render to overlap.

Run baseline and candidate against identical files. Before the patch, both
4:4:4 formats must fail import; after it, modes 2 and 4 must succeed and match
mode 3. Do not accept a software fallback as a hardware-test pass. The probe
explicitly requests VAAPI and reports the actual surface format and modifier.

For a longer clip, pass its frame count and omit the output file. The probe
waits for GPU completion after every rendered frame. Its rate includes startup. Modes 0–4 are serial diagnostics; mode 5 overlaps
decode with rendering. Neither implements Moonlight's full pacing/presentation
loop, so these rates are not a substitute for a live streaming measurement. It does
not test swapchain presentation, VRR, HDMI output, or optical HDR correctness.
