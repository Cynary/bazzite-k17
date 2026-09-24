# Streaming application sources

The image builds the exact commits in `sources.json`. Moonlight, Gamescope and
libplacebo come from the Moonmachine branches of our forks; MoonDeck comes from
upstream. The build does not apply a second set of application patches.

* **Moonlight:** reuse the DRM PRIME mapping created when waiting for a VAAPI
  frame. This avoids synchronizing the same Intel decoder surface again after
  later frames have started reading it. The change is carried against Nonary's
  VRR fork, version 6.1.0-vrr17.1. Buffer release now uses attributable
  readiness misses and preserves clean evidence across skipped frames.
  Gamescope WSI FIFO is recognized as protected presentation, removing the
  extra software spacing floor that capped a 116 FPS stream near 115.4 FPS.
* **MoonDeck:** the pinned upstream commit includes host-game closing and
  pausing the splash while it is unfocused. Both changes are now upstream, so
  the image no longer carries a MoonDeck patch. The upstream splash behavior
  is automatic.
* **Gamescope:** carry the small FIFO scheduling fix from
  [PR #24](https://github.com/OpenGamingCollective/gamescope/pull/24).
  Build the compositor and its Vulkan WSI layer together from the pinned OGC
  revision, rather than relying on a locally compiled binary.
  Native HDR10 streams can scan out directly when no real overlay is visible:
  the transparent Steam overlay placeholder and the SDR conversion option no
  longer force an extra rendering pass. Frames whose GPU work has already
  finished also wake the compositor immediately, as asynchronously completed
  frames already do. Real Steam overlays still use composition when needed.

Moonlight is a native build, with Wayland, Gamescope WSI, Vulkan and VAAPI
support. Its private FFmpeg and libplacebo libraries live beside the executable;
Qt and SDL come from Bazzite. The build runs Moonlight's VRR timing tests and
builds and lints MoonDeck's frontend and checks Python syntax. Decky and
MoonDeck's Python dependencies use checksum-verified upstream downloads.

The corresponding patched source and build inputs are included at
`/usr/share/moonmachine/sources`. No application configuration, pairing keys,
or host addresses are included.

## Updating a component

1. Merge or rebase upstream changes in the component fork. Remove our corresponding
   commits when upstream has incorporated them.
2. Test the component and pin its full commit ID in `sources.json`.
3. Build the image and check streaming on hardware, including display refresh,
   return to Steam and overlays. Compilation alone does not cover these behaviors.

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

The image includes the FIFO code fix as well as this conservative default.
The default remains until uncapped scheduling has broader presentation-mode
validation. The diagnostic Gamescope binary and local tracing settings are not
part of the image.

Gamescope WSI now reports the first measured DRM page flip for each displayed
commit. Early Wayland application-progress notifications remain unchanged.
Repeated scanout does not overwrite a frame's timestamp, and discarded commits
do not receive an invented display time. The change currently covers the DRM
backend; other backends retain their existing behavior.

See [the timing validation](../docs/TIMING-VALIDATION.md) for measurements and
remaining test limits.

## Intel 4:4:4 import

The pinned libplacebo fork adds import mappings for
Intel's packed Y410 (10-bit) and XYUV8888 (8-bit) decoder surfaces. The GPU samples
these through compatible RGB texture layouts; the component mapping restores
Y, Cb and Cr before colour conversion. Frames remain on the GPU.

The fork is built before Moonlight because the FFmpeg import helper is
header-defined. Its exact revision is recorded in `sources.json`.
See [the offline test](../tests/hardware/chroma/README.md) and
[validation results](../docs/CHROMA-VALIDATION.md).

The libplacebo patch has not yet been submitted upstream.

## Direct video presentation

The direct-presentation patches add selectable YUV and RGB paths to Moonlight
and packed-YUV import to Gamescope. YUV can avoid Moonlight's colour-conversion
render pass when the display supports direct scanout. The settings retain Vulkan
as an explicit choice and as the fallback for unsupported direct presentation.
See [Direct video presentation](../docs/DIRECT-VIDEO.md) for requirements,
measurements, and the automatic Vulkan handoff while overlays are visible.

### Linux source-clock and GPU readiness

The Moonlight fork exports Direct YUV surfaces before the next decoder job
can add a reference-read dependency. It also estimates the source clock from
CPU decoder output, keeping GPU readiness as a separate presentation constraint.
This is enabled by default on Linux and uses a new calibration key; older trace
parameters retain the previous behavior for replay. See
[direct video measurements](../docs/DIRECT-VIDEO.md#frame-timing-and-early-export).


## Optional predictive frame dropping

Moonlight's VRR settings include **Predictive frame dropping (experimental)**.
It is off by default. Reconnect after changing it. When enabled, it may skip a
late frame rather than let that frame delay its successor. It can also make
motion less smooth: one Stellar Blade capture dropped 5.1% of frames, without
a convincing enough reduction in the latency tail to make this the default.
Normal overload handling remains active with this option off.

The image includes cached VA surface export and explicit buffer synchronization
for Direct YUV/RGB. On a single-GPU system, the launcher selects its render node
for the Wayland explicit-sync protocol. Multi-GPU systems need an explicit
`MOONLIGHT_DIRECT_SYNCOBJ_DEVICE` selection. Unsupported direct initialization
falls back to Vulkan. RGB and multi-GPU behavior still need broader validation.
The measured acquire-wait reduction does not establish a general latency gain;
one early comparison accidentally compared Vulkan with direct presentation.

Native Steam Controller forwarding includes the Linux helper. It requires the
matching Vibepollo fork and virtual HID driver on Windows; the image alone does
not install the Windows driver. See the [controller transport notes](https://github.com/Cynary/moonlight-qt/blob/experimental/native-steam-controller/docs/native-steam-controller.md).

The host's event-driven WGC capture is a separate change in the
[Vibepollo fork](https://github.com/Cynary/Vibepollo/blob/experimental/native-steam-controller/docs/moonmachine-capture.md).
It works with predictive dropping off. Vibepollo runs on the host and is not
bundled in this client OS image.
