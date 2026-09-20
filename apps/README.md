# Streaming application patches

The image builds Moonlight and MoonDeck from the commits in `sources.json`.
`checkout.py` applies the listed patches before compilation. A patch that no
longer applies stops the build.

* **Moonlight:** reuse the DRM PRIME mapping created when waiting for a VAAPI
  frame. This avoids synchronizing the same Intel decoder surface again after
  later frames have started reading it. The change is carried against Nonary's
  VRR fork, version 6.1.0-vrr17.1.
* **MoonDeck:** add “Pause splash rendering when unfocused” under Runner
  Settings. This stops the background splash from driving extra Gamescope
  refreshes during a stream. Moonmachine enables it for new installations;
  the patch's upstream default is off. See
  [MoonDeck PR #183](https://github.com/FrogTheFrog/moondeck/pull/183).

Moonlight is a native build, with Wayland, Gamescope WSI, Vulkan and VAAPI
support. Its private FFmpeg and libplacebo libraries live beside the executable;
Qt and SDL come from Bazzite. The build runs Moonlight's VRR timing tests and
builds and tests MoonDeck's frontend and Python setting migration. Decky and
MoonDeck's Python dependencies use checksum-verified upstream downloads.

The corresponding patched source and build inputs are included at
`/usr/share/moonmachine/sources`. No application configuration, pairing keys,
or host addresses are included.

## Updating or removing a patch

1. Review the upstream changes and update the source commit in `sources.json`.
2. If upstream includes the fix, remove its patch file and its entry in
   `patches`. Otherwise rebase the patch against the new commit.
3. Build the image and check streaming on hardware, including actual display
   refresh, return to Steam, and the MoonDeck toggle. Passing compilation alone
   does not cover these behaviors.

Moonlight updates with the OS image. MoonDeck installations created by the image
also update at boot, keeping settings and a backup under
`~/homebrew/moonmachine-backups/moondeck-previous`. If the
installed plugin files have been changed or replaced through Decky, image setup
leaves that installation alone. Existing independently installed plugins are
not adopted automatically.

## Gamescope default

`30-moonmachine-vrr.conf` sets `gamescope_adaptive_sync_uncapped=false` for
Gaming Mode. This keeps VRR and V-sync available while avoiding the scheduling
regression observed with paced Moonlight frames. Native games that render above
the display's refresh rate may lose the uncapped behavior that setting provides.

This is a workaround, separate from any proposed Gamescope code fix. Keep it
until that fix has been tested across presentation modes and incorporated into
the Gamescope package used by Bazzite.

The proposed FIFO fix is [Gamescope PR #24](https://github.com/OpenGamingCollective/gamescope/pull/24).
It restores full-rate Moonlight presentation in the K17 test with uncapped
scheduling enabled. The image continues to use the convar default above;
it does not replace Gamescope with the diagnostic test binary.

## Intel 4:4:4 import

`patches/libplacebo/0001-import-packed-vaapi-444.patch` adds import mappings for
Intel's packed Y410 (10-bit) and XYUV8888 (8-bit) decoder surfaces. The GPU samples
these through compatible RGB texture layouts; the component mapping restores
Y, Cb and Cr before colour conversion. Frames remain on the GPU.

The patch is applied before installing libplacebo's headers and compiling
Moonlight, because the FFmpeg import helper is header-defined. Its pinned
libplacebo revision and application order are in `build.sh`.
See [the offline test](../tests/hardware/chroma/README.md) and
[validation results](../docs/CHROMA-VALIDATION.md).
