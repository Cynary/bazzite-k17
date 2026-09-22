# Intel 4:4:4 import validation

These are the original offline test notes. The patch is now packaged and live
4:4:4 streaming has been validated in the [September 22 release](STREAMING-VALIDATION.md#2026-09-22-permanent-clockreadiness-policy).
Historical candidate status below describes the time of each test.

Tested on the K17 / Arc 130V on September 20, 2026 with Intel media-driver
26.3.3, libva 2.24.1 and the image's libplacebo revision
`2d0979fb54e025e904c7372666fffbf5dae40f66`. Tests used the GPU directly through
an offscreen Vulkan renderer; no streaming host or TV observation was needed.

The baseline decoded HEVC successfully but failed `pl_map_avframe_ex` for both
Y410 and XYUV8888 DMA-BUF surfaces. The reported modifier was
`0x0100000000000009`. The missing format lookup also exists in libplacebo's
upstream head checked for this work, `e2972fdd09adacd383656738d7d280f0cd84a761`.

The candidate imports Y410 as `rgb10a2` with sampled channels mapped to Cb, Y,
Cr; XYUV8888 uses `rgba8` mapped to Cr, Cb, Y. The unused channel is ignored.
There is no CPU readback or conversion in that import path. Test readback occurs
only when comparing rendered pixels.

| Test | Result |
| --- | --- |
| Baseline 8-bit and 10-bit 4:4:4 import | Both fail as expected |
| Patched 8-bit 4:4:4 single-pixel chroma/ramp pattern | Exact match to software-decoded reference |
| Patched 10-bit BT.2020/PQ 4:4:4 pattern | Maximum RGB error 0.00001526 in float16 output |
| Early DRM PRIME mapping versus VAAPI-derived import | Identical output |
| Existing 10-bit 4:2:0 pattern | Exact match to software-decoded reference |
| 600-frame 3840×2160 HEVC 4:4:4 10-bit clip | All frames imported and rendered |

The longer clip measured about 100 FPS with serialized decode/render completion
waits while a separate Moonlight stream was running. This is not an idle-GPU
throughput result and does not establish 4K120 streaming performance. Startup
shader compilation is included. The colour comparisons use the same libplacebo
renderer with software-decoded planar frames as reference; they check packed
import correctness, not independent calibration of libplacebo's colour science.

The development container had an older libva than its media driver required.
These tests used the running system's libva 2.24.1. The final OS image was checked
separately: it already has the compatible version and initializes VAAPI normally.

Live Moonlight 4:4:4 throughput, HDR/VRR presentation, suspend/resume and other
GPUs remain unverified. The running Moonlight installation was not replaced.
Implementation and automated validation were performed with OpenAI Codex.

During the rebuild, upstream replaced MoonDeck's moving nightly archive. The
new archive checksum is
`99c28c22149201b9c92313416f076f6f60bc0fe7ed266db4404020962e5144d1`.
All 577 extracted Python dependency files were compared by SHA-256 against the
previous verified bundle and are identical. The MoonDeck source pin and patches
were not changed.

The full candidate image built successfully, with application tests, setup tests,
library checks and bootc lint (13 passed, one skipped). Image ID:
`b0920ff3c59de716b05870767e8ead837f02f536a5805077c328f429444298aa`.
It has not been booted or promoted to the release channel.

After closing the stream and finishing compilation, the three-frame queued
probe ran inside that image using its VAAPI, Vulkan, libplacebo and decoder
libraries. It rendered 600 4K 10-bit 4:4:4 frames in 3.956 seconds (151.66 FPS).
Only the test's libavformat was supplied separately to enable local Matroska
input; the shipped minimal libavformat does not include a file demuxer. The
probe's import helper is compiled from the patched header. This validates the
image's GPU libraries and the import patch, not the complete Moonlight program.

A longer run looped the same five-second test clip twelve times: all 7,200 frames
rendered in 45.776 seconds (157.29 FPS), including startup. Mean mapping time was
4.059 ms and mean GPU-completed rendering time was 2.219 ms. The final image's
HDR pattern output was identical to the earlier patched-container output.
These throughput tests had no active stream or compiler load. They are
unpaced, offscreen tests and do not measure display deadlines or dropped frames
in Moonlight.
