# Xbox driver release validation

`moonmachine-20260923.1` is built, signed and installed on the test K17.
It is published on the signed `moonmachine` update channel.

Image digest: `sha256:c960ed5c03c2fbd690b324e952b9eb548551c81da9c9b3469aef41b89f419edc`.
Build source: `7ca49a2`.

## What is included

All five patches in `xone-patches/` are applied to the pinned xonedo source.
The rebuilt source files match the tested candidate exactly. The module package
is `kernel-modules-7.2.4-k17bore1.frl6`; only `xone_dongle.ko` changed from the
previous module package. The existing graphics, Wi-Fi and other modules remain.

Both the installed driver and the copy extracted from the initramfs report
`3DBD258ECD8E759A6E35105` and match byte-for-byte. The image checks that version
and the shared 2017 firmware hash at build time. The boot health check verifies
both the installed and loaded driver identities.

The release also includes the streaming and VRR defaults prepared in the
previous unpublished candidate: initial Moonlight settings and the Steam VRR
settings service. See [streaming setup](STREAMING.md). Moonlight, Gamescope and
libplacebo binaries match that candidate; no rendering changes were made here.

## Tests

Before packaging, the driver passed ten early-loading restarts and ten short
suspend/resume cycles. All restored a real input device. One restart logged a
transient GIP status busy warning; the sleep cycles had no xone errors.
[The driver investigation](../experimental/xone/full-firmware-reset.md) explains
the changes and the limits of those tests.

The packaged image passed container checks and booted through its normal boot
entry, without a local module-loading service or test initramfs overlay. The
controller registered normally and remained present during the reboot test's
observation period. The kernel boot-health check passed.

The subsequent timer-driven suspend/resume completed without xone errors.
No controller was registered at the first observation; after the user confirmed reconnection,
a fresh input device registered with exactly one client and no new xone errors.

No new visual TV or streaming performance test was performed for this release.
The graphics and application binaries were checked against the previous build.

The signed registry channel was checked on the K17 and the identical digest was
staged as its update source. The currently running image is that same digest.
