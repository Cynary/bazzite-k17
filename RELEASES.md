# Installing and maintaining the K17 image

This is a community experimental Bazzite Deck derivative, developed with Codex,
not an official Bazzite release or a general Intel hardware support claim.

## Current full-kernel release

[bore-20260919.1](https://github.com/Cynary/bazzite-k17/releases/tag/bore-20260919.1)
contains the exact hardware-tested BORE + ThinLTO OCI image and kernel RPMs.
The kernel source is [8cff674dac5e46b6452d4349ed3f3483d6cff1bc](https://github.com/Cynary/linux-k17-frl/commit/8cff674dac5e46b6452d4349ed3f3483d6cff1bc).

```
ghcr.io/cynary/bazzite-k17:bore-20260919.1
sha256:e12799860cc9ee12647ac9a6f5859238ef51417e9314d80f68e884b5cb631da6
```

The base is Bazzite Deck 44.20260916; kernel 7.2.4-k17bore1+ carries the
K17 FRL/VRR, MediaTek and Xbox adapter fixes, BORE 6.8 and Clang ThinLTO.
No AutoFDO. See [configuration, limitations and measured results](experimental/bore-thinlto/README.md).
Secure Boot is unsupported. Rust kernel modules and several optional third-party
specialty modules are absent. Existing firmware ACPI warnings remain.
TV-side validation of this full-kernel candidate is still required before stable promotion.

## Existing Bazzite installation

Back up important data, keep a known-good deployment pinned, and verify the
release's exact digest with `cosign` and this repository's `cosign.pub`.
Obtain the public key through a source you trust; downloading a key beside an
image is not independent verification of the publisher.

```sh
IMAGE=ghcr.io/cynary/bazzite-k17
DIGEST=sha256:e12799860cc9ee12647ac9a6f5859238ef51417e9314d80f68e884b5cb631da6
cosign verify --key cosign.pub --insecure-ignore-tlog=true "$IMAGE@$DIGEST"
sudo ostree admin status
# Pin the index of the currently working deployment shown above:
sudo ostree admin pin 0
sudo bootc switch "$IMAGE@$DIGEST"
sudo systemctl reboot
```

Check the actual index: index 0 is normally the current deployment only when
there is no staged deployment. Review or clear old local kernel overrides before
switching; do not mix this full kernel with replacement modules from another ABI.
The commands deliberately select a verified immutable digest. The default
container policy may not enforce our signature: verify each new digest before
switching. This key-based signature omits the transparency log, not the signature check.

After reboot, `uname -r`, `sudo bootc status` and
`sudo /usr/libexec/k17-verify-bore` should identify and verify the new kernel.
Then check actual TV HDR/10-bit/VRR, controllers, sound and suspend/resume.
If a candidate fails, select the pinned working deployment in the boot menu.
`sudo bootc rollback` schedules the available rollback deployment; inspect its
identity first because it may not be the particular pinned deployment you want.

## Fresh machine

Install official Bazzite's AMD/Intel HTPC/Steam Gaming Mode image first, selecting
Intel graphics for this K17. Complete first boot, then follow the switch above.
There is no separate installer ISO in this release. The OCI image is the complete
operating-system payload; an ISO would only add an installation environment.
Use [Bazzite's image selector](https://bazzite.gg/) for the initial installer.

For offline transfer, download every `image.oci.tar.part-*` asset and
`IMAGE-SHA256SUMS`, verify the checksums, and concatenate/extract into an empty
directory. The archive contains an OCI layout, not a disk image to write with dd.
Kernel RPM assets are image-build inputs, not a recommendation to layer RPMs onto
an existing Bazzite deployment.

## Updates

This first release is pinned. `bootc upgrade` cannot turn its immutable digest
into a newer kernel. Flatpak/Steam applications still update separately.

To publish an OS update:

1. Advance the pinned Bazzite base and inspect its kernel/driver changes.
2. Rebase the carried patches onto the matching OGC kernel; rebuild the full
   kernel and every out-of-tree module, including xone, for that ABI. If keeping
   an older kernel temporarily, explicitly verify its integration with the new base.
3. Build the OCI image; run lint, VM smoke, hardware boot and graphics/input/
   suspend tests. Pin the previous working deployment before testing.
4. Package the exact tested image and checksums as a new versioned prerelease.
   `Publish tested full-kernel image` verifies the archive and expected digest,
   copies it to GHCR without rebuilding, then signs it using repository secrets.
5. Users verify the newly published digest and run `bootc switch` to it.

No rolling full-kernel channel or unattended promotion is enabled yet. Once the
hardware qualification and update procedure are dependable, a signed rolling
channel can point at approved versions. Updating then becomes normal image
updates for clients, while the maintainer still carries/rebuilds the patch stack.
DKMS does not replace this work: BORE/LTO and these DRM changes require the kernel
build, not just an independently installable leaf driver.

## Personal setup is separate

Moonlight builds, Decky plugins, MoonDeck host settings and TV/AVR automation can
live under `/var/home`, `/var/lib` and `/etc`, surviving image updates. Their pairing
keys, account data, addresses and machine-specific network settings do not belong
in the public image. Python virtual environments may need rebuilding after a
Python minor-version upgrade. Retest plugins after Steam/Decky updates.
