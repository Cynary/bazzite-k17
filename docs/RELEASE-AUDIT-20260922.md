# Release contents audit: 22 September 2026

Audited `moonmachine-20260922.2`, published to `ghcr.io/cynary/bazzite-k17:moonmachine`:

`sha256:78a8822139dcdf80abd7fafe1282bef3cb6b38928228bbf8c6a87b4225d93282`

The streaming and graphics changes below are present. **The later Xbox
suspend/resume candidate is missing from this release.** Earlier reconnection
fixes are included; they must not be described as including that candidate.

## Included

| Component | What is packaged | Evidence |
|---|---|---|
| Intel display driver | Native HDMI FRL, 4K120 10-bit HDR/VRR work; corrected clocks and VRR transitions; lost-link recovery | `kernel-modules-7.2.4-k17bore1.frl4`; installed Xe hash matches build record; boot health checks passed |
| Kernel | BORE and ThinLTO | Installed configuration has `CONFIG_SCHED_BORE=y` and `CONFIG_LTO_CLANG_THIN=y` |
| Gamescope | FIFO scheduling fix; measured DRM presentation timestamps; native HDR scanout; wake for already-ready frames; direct packed-YUV and P010 handling, composition and overlay support | Pinned source plus all six patches in `apps/sources.json`; binary hash below |
| Moonlight | Reused VAAPI mapping; readiness-attributed buffer release; Gamescope FIFO recognition; direct YUV/RGB options; P010; retained-decoder overlay handoff; early export and separate clock/readiness policy | Pinned Nonary source plus all seven patches; Linux policy enabled by default; binary hash below |
| libplacebo | Packed Y410/XYUV8888 import and channel mappings, compiled into the private renderer and Moonlight's header-based import helper | Build applies `0001-import-packed-vaapi-444.patch` before building both; patched build inputs preserved in installed image |
| MoonDeck / Decky | Pinned upstream MoonDeck including host close request and unfocused splash behaviour; Decky 3.2.9 | Installed build manifest matches repository; no MoonDeck patch remains |
| Wi-Fi | MT7922 firmware-record parsing fix | Included custom kernel; firmware loading/scanning validated, throughput not validated |
| Xbox | Answer repeated association requests; restore original adapter probe reset | Two files in `xone-patches/`; packaged and loaded dongle `srcversion 79D993360F2FB22DB547715` |
| Sleep UI | Steam inhibitor guard | Image-owned script and `default.target.wants` symlink; service running during audit |
| Boot / updates | Quiet graphical boot, signature policy, signed GHCR release stream | Signature-verified switch and both update checks passed |

`systemctl --user is-enabled` reports the guard as disabled, but the image's
vendor `default.target.wants` symlink starts it; it was active. This is not a
missing guard. No temporary Moonlight, Gamescope or Xe file mounts were found.
Installed application build inputs matched the tested build context recursively.
The runtime Moonlight and Gamescope hashes match the validated build.

## Omission: Xbox suspend candidate

Follow-up: the [23 September candidate](XBOX-RELEASE-20260923.md) packages this
fix together with the later firmware-reset and association-address fixes.

The September 19 candidate restored the radio before restarting USB receive
requests and added a teardown guard for queued events. Five short candidate
sleep cycles registered an input device without phantom clients or packet errors:
two controller wakes and three RTC wakes. The control was already unstable before
its first sleep, so those tests did not isolate resume ordering as the root cause.

That code remained in an experimental local driver, rather than in
`xone-patches/` or the release's kernel RPM. A leftover kernel-specific modprobe
override points at the candidate, but the audit found the packaged older module
actually loaded. The initramfs also includes xone, so a later root-filesystem
override cannot be treated as proof of which driver booted.

Follow-up: recover a clean source diff, retain the limited validation claim,
package it in the matching kernel module RPM and initramfs, then test reboot,
controller wake and RTC resume using the image-owned module with no local loader.
Do not mark this complete based only on a successful local reload. This audit
made no live driver changes.

## Separate from the client image

- MoonDeck Buddy runs on the Windows host. The client image contains the protocol
  support, not the host service or optional launcher-specific host changes.
- The test machine's CPU performance preference, elevated GPU minimum clocks and
  35 W sustained package limit are outside the shared image. The streaming
  measurements used that machine's tuning; a fresh installation may differ.
- TV/receiver addresses, pairing credentials and network automation remain
  setup-specific. The repository provides examples, not preconfigured devices.
- Failed experiments, temporary tracing, arbitrary buffer caps and experimental
  asynchronous handoff are not required by the published streaming path.

## Artifact identity

Image source: `e648001` (later publishing/documentation commits do not change
its binaries). Moonlight `6.1.0-vrr17.1-moonmachine.5`; Gamescope
`ogc-0ef725a-moonmachine.5`. FFmpeg and libplacebo are private libraries beside
Moonlight. Corresponding patched sources and build inputs are shipped under
`/usr/share/moonmachine/sources`.

| Installed artifact | SHA-256 |
|---|---|
| Moonlight | `f0e34114d8bc0f94e41547014df381ec903fff93b23ab976a1564e83d9e3d0cf` |
| Gamescope | `360a865eacecaf306690230164030bcdc50a8d6d962d568fabfa8ce755964aa8` |
| libplacebo.so.365 | `efd9eb400ca05e32dedf2aab0ddd13e05ed8472bad68ab9e6fd17c9570e6b643` |
| Xe module | `8e6f2f82afa7c277e9b4f310894580262f72cf4d57d1aeae84b9ba326e6b2a03` |

The K17 was running this digest from the tested local OCI source. The signed
registry deployment of the identical digest was staged for its next normal boot.
The GHCR publisher verified the digest and signed it; channel promotion checked
signatures. `bootc upgrade --check` found no change, and `uupd update-check`
reported `update_available: false` (exit 77).

This audit verifies packaging and selected runtime identities. It does not
repeat the full hardware test suite. See [streaming validation](STREAMING-VALIDATION.md)
and [display recovery](DISPLAY-RECOVERY.md) for what was exercised.
