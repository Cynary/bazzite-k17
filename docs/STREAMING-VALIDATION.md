# Streaming patch validation — 20 September 2026

## Gamescope

Tested on the K17 with Intel Arc 130V, a 4K120 HDR VRR display, and Moonlight's
Gamescope WSI FIFO swapchain. The stream used HEVC 4:2:0.

The original uncapped VRR path could reduce rendering to about 63 FPS while
Moonlight received and decoded 116 FPS. Disabling `adaptive_sync_uncapped`
restored full-rate presentation.

[Gamescope PR #24](https://github.com/OpenGamingCollective/gamescope/pull/24)
excludes FIFO clients from that scheduling gate. The tested base was the `ogc`
branch at `0ef725a8754b3480fb52d2493c4b3af3b845659b`. With the candidate and
uncapped scheduling enabled, a 3,499-frame capture measured 115.98 submissions
per second. Repaint counters reported 116–117 new base frames per second and
zero repeated base frames. Presentation calls had a median of 0.607 ms, p99 of
1.275 ms, and maximum of 1.797 ms.

The runtime test binary included diagnostic counters, which are excluded from
the PR. Other GPUs, multiple outputs, and uncapped mailbox/immediate games were
not tested. The image retains the convar workaround as its default. The September 21
recipe also builds the FIFO patch without the diagnostic counters. Hardware
validation of that assembled image is recorded with its release.

## Application packaging

Moonlight's VAAPI mapping patch was ported from the hardware-tested vrr14 build
to Nonary's vrr17.1 source. The image builds the patched source with Vulkan,
VAAPI, Wayland and Gamescope WSI support. The following checks passed:

- VRR timing-controller, rate-policy, pacing-worker and replay-configuration suites.
- MoonDeck frontend compilation and lint, splash focus behavior, and settings migration.
- Image setup in a fresh home, repeated setup, unique client identities, preservation
  of independently modified plugins/settings, and updating an image-managed plugin.
- Runtime library resolution and Moonlight's command-line startup in the assembled image.
- Bootc container lint: 13 checks passed, one skipped.

The vrr17.1 image build has not yet had a boot-and-stream hardware test. The live
Gamescope measurements above used the vrr14 VAAPI-patched client. This record
does not establish 4:4:4 decoding support or extend validation to other machines.
