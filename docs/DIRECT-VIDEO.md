# Direct video presentation

Moonlight's **Video presentation (Gamescope)** setting offers Auto, Direct YUV,
Direct RGB, and Vulkan. Reconnect the stream after changing it.

Direct YUV sends the decoded video surface to Gamescope. When the display
hardware accepts that format, it converts YUV to RGB while scanning out the
picture. Direct RGB first converts the surface with VAAPI video processing.
Vulkan uses Moonlight's existing libplacebo renderer.

The direct paths currently target native-resolution, limited-range BT.2020 PQ
HEVC 10-bit 4:4:4 decoded through VAAPI in Gamescope. Unsupported formats or a
failed direct renderer fall back to Vulkan. The validation below covers the
K17's Intel Arc 130V in Gaming Mode; it does not establish support on other GPUs
or desktop compositors.

## Measurements

At 3840×2160, 116 FPS, HDR and 4:4:4, measurements from complete frame reception
to the reported DRM display flip were:

| Path | Mean | 95th percentile |
| --- | ---: | ---: |
| Direct YUV | 6.86 ms | 11.05 ms |
| Direct RGB | 10.25 ms | 11.32 ms |
| Vulkan | 8.86 ms | 9.76 ms |

These were separate Overcooked 2 title-screen runs, excluding the first 30
seconds. They exclude host rendering/encoding, network transit, scanout position,
and the TV's internal processing. Timing records were matched to submission IDs;
no drops were recorded in these steady measurement windows. They are not a
motion-to-photon measurement or a guarantee that every frame takes less than
8.33 ms.

## Overlays

Statistics and Steam overlays can force Gamescope to compose the video and
interface together. In the sustained statistics test, Direct YUV rose to
19.16 ms on average, with 12 recorded drops in that measured window. Closing
statistics restored a 7.01 ms average. The overlay overhead remains unresolved.

The compositor skips unnecessary colour processing for fully transparent overlay
pixels. It also precompiles common packed-YUV HDR overlay and screenshot shaders
in its background compiler: compiling one of these on demand previously stalled
presentation for 266 ms.

Moonlight holds at most eight outstanding video buffers. If all remain in use,
it drops an incoming frame and services release events on subsequent frames.
It falls back to Vulkan if the pool remains full for 250 ms. This bounds memory
use and avoids abandoning direct rendering after a single congested frame.

## Validation limits

The builds pass Moonlight's existing timing suites and Gamescope's 68 tests.
Live checks cover selecting YUV/RGB/Vulkan, reconnecting streams, statistics,
screenshots, and returning from composition to direct scanout. Screenshots have
been visually inspected; quantitative HDR colour accuracy, other display modes,
and wider hardware compatibility still need validation.
