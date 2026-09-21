# Streaming patch validation

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

## September 21 assembled-image test

Tested OCI manifest `sha256:34107bfb403fcb58c80f10871cbc32fe35e04ac0e18fa47c8bf52687d69bccb0`
on the K17. The image booted with its own kernel modules and initramfs, without
local package overrides. The display driver reported 3840×2160 at 120 Hz,
RGB 30 bpp. Gamescope ran from the image with its scheduling capability intact.

The image's native Moonlight 6.1.0-vrr17.1-moonmachine.1 launched Overcooked 2
through upstream MoonDeck and Buddy protocol 9. Logs confirmed HEVC Main 4:4:4
10-bit VAAPI decoding, a Vulkan HDR10 swapchain, and active VRR pacing.
An 87-second session, including game startup, reported:

| Measurement | Result |
| --- | --- |
| Incoming and decoded frames | 114.24 FPS |
| Rendered frames | 113.23 FPS |
| Average decode time | 0.47 ms |
| Average render time, including V-sync | 3.44 ms |
| Network loss | 0.00% |
| Frames classified as jitter drops | 0.88% |
| Average frame queue delay | 8.94 ms |

Ending the local shortcut sent the upstream close-app request and removed the
host game process. This used the existing shortcut through Steam's API, not a
controller click through the MoonDeck interface. The Buddy used for this check
also carried optional launcher support; Overcooked was a regular Steam game.
No visual TV confirmation was available for this run.

The presentation-timestamp issue remains open: Gamescope returned 9,267
predicted timestamps earlier than the corresponding Moonlight submission.
These are rejected by Moonlight. The FIFO scheduling fix and packed 4:4:4
import fix do not fix that feedback or the remaining queue delay.

Build checks passed: Gamescope's 67 tests, 11 Moonlight test executables,
MoonDeck compilation/lint, three image-setup tests, runtime library checks,
and bootc container lint. Results apply to this machine and configuration.


### Sleep and storage checks

A blocked Steam sleep request left `suspending=false` and `show_resume_ui=false`.
After releasing the inhibitor, a normal Steam sleep request entered s2idle and
resumed with the same boot ID. The receiver wake produced a real FRL training
timeout; the driver retried and recovered automatically. The final display
state was 4K120 RGB 30 bpp, with no new underrun or flip timeout. Steam returned
without a suspend overlay. This check used an RTC alarm; a later WOL packet
was sent after the recorded resume, so it does not establish WOL reliability.
The controller was not powered on for this batch.

An unexplained reset occurred on the build machine before the successful build.
Damaged container intermediates were discarded, and readable portions of a
checksum-damaged audit log were preserved. Two subsequent full read-only Btrfs
scrubs passed, including one after the build. The SSD short self-test and a
120-second memory verification workload passed. No further unexpected reset or
checksum error occurred during these checks, but their cause remains unknown.
Existing firmware ACPI warnings and Intel Ethernet PTM timeout messages remain.

The subsequent [timing investigation](TIMING-VALIDATION.md) corrected the queue
backlog and Gamescope presentation feedback.
