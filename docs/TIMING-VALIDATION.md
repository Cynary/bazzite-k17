# Moonlight queue and display timing

Tested on the K17 on 21 September 2026 with a 116 FPS Overcooked 2 stream,
4K HEVC 4:4:4 10-bit, HDR, VRR and V-sync enabled. Both captures used the same
patched Gamescope and per-frame tracing. The Moonlight executable was changed
between captures; no bandwidth or buffer-cap setting was lowered.

| After the first 60 seconds | Previous Moonlight | Corrected Moonlight |
| --- | ---: | ---: |
| Submitted frames per second | 115.24 | 115.98 |
| Mean queue wait | 8.99 ms | 1.62 ms |
| Median queue wait | 9.96 ms | 1.27 ms |
| 99th-percentile queue wait | 14.57 ms | 5.65 ms |
| Omitted frame numbers | 70 over 91 seconds | 0 over 143 seconds |
| Median client-added interval error | 334 us | 37 us |
| Mean client-added interval error | 601 us | 653 us |

Correlating decoder output with measured DRM display timestamps gave a mean
29.42 ms before and 24.01 ms after the change. This is not network-to-photon
latency: it excludes the host/network portion and panel response. It also shows
that the smaller queue statistic was not just a transfer of waiting elsewhere.

The application's whole-session statistic, including startup, reported **1.92 ms
average frame queue delay** with the fix. Occasional timing variation remains;
the mean interval error did not improve in this capture. This was an automated
launch/exit test, without a person evaluating motion or the TV overlay.

## What changed

Moonlight selected Gamescope WSI's FIFO presentation mode but reported that this
mode could not provide synchronized presentation. Its fallback software spacing
floor was about 8.67 ms at 120 Hz, limiting submissions below the 116 FPS source.
The resulting backlog caused regular skipped frames. Gamescope WSI already uses
a Mailbox driver swapchain and implements FIFO synchronization itself. Recognizing
that capability removes the redundant floor while retaining V-sync. Ordinary
FIFO, Immediate and relaxed FIFO keep their previous capability rules.

Two buffer-release problems were also corrected. Submission errors unrelated
to input readiness could keep old buffering indefinitely. A skipped frame also
reset the entire clean-history timer, so regular skips prevented the eight-second
release hold from ever completing. Revision 9 attributes protection to readiness
misses and counts observed clean intervals across gaps; it does not count the gaps
as clean time. The existing minimum, maximum, hold and release-rate settings remain.
Historical revisions remain available for replay.

The internal allowance still reached about 8.6 ms in this stream. That value is
not a constant queue wait: it locates the presentation target relative to the
mapped source timeline. Input arrival and GPU decoding consume much of it. The
corrected capture had about 4.3 ms of explicit decoder synchronization waiting in
its initial steady segment, separate from the displayed queue statistic. Genuine
readiness misses still justify retaining protection. Actual queue waiting was
measured separately in the table above.

## Gamescope timestamps

Gamescope previously sent predicted vblank times through its Vulkan WSI timing
interface as actual presentation times. In the baseline, 27,864 timestamps were
rejected for preceding submission, and only 53 usable samples were emitted.

The DRM backend now records the first page flip of the corresponding commit.
Early Wayland progress notifications are preserved; repeated scanout does not
replace the first timestamp. The final live capture emitted 23,198 usable timing
samples, with zero pre-submission rejections. Twenty-eight samples were rejected
as future-dated by Moonlight's clock checks; they were not treated as valid data.
Other Gamescope backends retain their existing behavior. Multi-output timing and
all overlay/composition combinations have not been hardware-validated.

## Checks and limits

Gamescope's 68-test suite passed. Moonlight's timing-controller, pacing-worker,
rate-policy, replay-configuration, Vulkan timing, presentation/swapchain,
Gamescope composition/repaint, Wayland feedback and incoming-frame tests passed.
New cases cover readiness-attributed release, skipped-frame recovery, intentional
preparation waits and the Gamescope FIFO capability distinction.

The recorded baseline reproduced controller decisions, but failed the replay
utility's full-fidelity gate. These results therefore use live A/B captures and
deterministic tests, not a claim of exact counterfactual replay. No new kernel
errors or unexpected reboot occurred during these captures.

## Packaged image check

The image built from `8492b41e3e665f9ea21088b8a997b81dd584fd24` booted with
manifest `sha256:e906b5cdf88232ea7dd85336c84e9c4c2ec17c3338b56e81e53ea86d393b3481`.
Gamescope and Moonlight hashes matched the build artifact; no temporary binary
mount was used. A further 134-second stream reported 1.67 ms whole-session queue
delay. After the first minute, it submitted 116.02 FPS with no omitted frame
numbers and 1.74 ms mean queue waiting. Exiting the stream closed Overcooked 2 on
the host. The display state remained 3840×2160 at 120 Hz with 30-bit RGB output.
Existing firmware ACPI warnings remain; no new graphics or storage errors were
observed. The historical Btrfs corruption counter remained unchanged.
