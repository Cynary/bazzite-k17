# Moonmachine releases and updates

Moonmachine is this repository's experimental K17 Bazzite Deck derivative,
with the custom FRL/VRR kernel, BORE and ThinLTO. It is not an official Bazzite
release or a general Intel hardware support guarantee. Secure Boot is unsupported.

## Follow the release stream

The moving channel is:

```
ghcr.io/cynary/bazzite-k17:moonmachine
```

Machines following this tag receive approved images through normal Bazzite system
updates, or `sudo bootc upgrade`, followed by a reboot. The tag advances only when
we explicitly promote a tested release; it does not blindly follow upstream
Bazzite or automatically compile new kernels. A check that finds no newer digest
correctly reports no OS update. Flatpak and Steam applications update separately.

A machine installed using `@sha256:...` or a numbered release tag remains pinned
to that version. It needs a **one-time switch** to `:moonmachine` to follow updates.
Pinning an OSTree recovery deployment is different: it preserves that deployment
without preventing the active channel from updating.

From a trusted checkout of this repository on Bazzite:

```sh
sudo ostree admin status
# Pin the working deployment's actual index; it is normally 0 if none is staged.
sudo ostree admin pin 0
sudo ./scripts/join-moonmachine-channel.sh
sudo systemctl reboot
```

Review/trust `cosign.pub` before this initial enrollment. The helper verifies the
channel's resolved digest, installs the repository key and a narrowly scoped
container signature policy, and uses `bootc switch --enforce-container-sigpolicy`.
It preserves policies for other repositories. Subsequent OS updates require a
signature from this key; a mere mutable tag is not the trust boundary.

Existing enrolled machines can switch with:

```sh
sudo bootc switch --enforce-container-sigpolicy ghcr.io/cynary/bazzite-k17:moonmachine
```

No additional automatic reboot timer is enabled by this project. Bazzite's own
update UI, update scheduling and reboot behavior remain in control.

## Installation and rollback

For a fresh computer, install official Bazzite's Intel HTPC/Steam Gaming Mode
image first, complete first boot, then enroll above. Use the
[Bazzite selector](https://bazzite.gg/). Our release is a complete bootable OCI OS
payload, not a custom installer ISO or a disk image to write using dd.

After reboot, inspect `sudo bootc status`, `uname -r` and
`sudo /usr/libexec/k17-verify-bore`. Verify actual TV HDR/10-bit/VRR, controllers,
sound and suspend/resume. Keep known-good deployments pinned. If boot fails,
select a pinned working deployment in the boot menu. `sudo bootc rollback`
schedules the available rollback deployment; check its identity first.

Numbered tags and explicit digests remain available for reproducible installs,
comparison and recovery. Switching to one stops following the moving stream until
you switch back. A channel can also be moved back to a previous signed release
if a regression is discovered; clients still need to perform an update/reboot.

## Releases

- `bore-20260919.1`: Bazzite 44.20260916, kernel 7.2.4-k17bore1+.
  Digest `sha256:e12799860cc9ee12647ac9a6f5859238ef51417e9314d80f68e884b5cb631da6`.
- `bore-20260919.2` (**current `:moonmachine`**): Bazzite 44.20260919, the same
  tested full-kernel RPMs (upstream's kernel version is unchanged), updated
  Gamescope 3.16.29, and native signature-policy enforcement.
  Digest `sha256:01921691cf33b54dd97b9ea3f9239a591a74a595b79efebd8e4e2320d65f4916`.
  Hardware boot/health and MoonDeck launch/host-exit checks passed.
  See [release notes](https://github.com/Cynary/bazzite-k17/releases/tag/bore-20260919.2)
  for validation limits and [boot measurements](experimental/bore-thinlto/results/release-20260919.2/boot-check.txt).

See [GitHub releases](https://github.com/Cynary/bazzite-k17/releases) for exact
artifacts/digests and [kernel configuration and limitations](experimental/bore-thinlto/README.md).
Rust kernel modules and several optional out-of-tree specialty modules are absent.
Existing firmware ACPI warnings remain. No general gaming performance gain is claimed.

## Maintainer procedure

1. Advance the pinned Bazzite base. Compare kernel version/configuration and OS
   integration changes. Rebase/rebuild the full kernel and every out-of-tree
   module when needed. Reuse existing RPMs only after an explicit compatibility
   review; matching the version alone is not a general ABI guarantee.
2. Prepare the full-kernel build context with `experimental/bore-thinlto/prepare-image.sh`,
   setting `RPM_DIR` and `IMAGE_CONTEXT`. It includes graphical boot defaults and
   channel trust policy from this repository; it does not copy the live host.
3. Build and lint the image, boot-test with pinned recovery, and test graphics,
   input, networking, applications and suspend/resume as applicable.
4. Upload the exact tested OCI archive/checksums as a numbered release and run
   `Publish tested full-kernel image`. It verifies the archive/digest and publishes
   it without rebuilding. It provides both native containers/image signatures
   for OS updates and Cosign signatures for independent verification.
5. Run `Promote tested Moonmachine release` with the numbered release and expected
   digest. It verifies signatures using the OS signature-policy implementation
   before moving `:moonmachine` to that same digest. No kernel patches are sent
   upstream by this workflow.

The maintainer still needs to carry patches and qualify new images. Consumers no
longer need to manually switch to each numbered release once enrolled. DKMS does
not replace the full-kernel work needed for BORE/LTO and the carried DRM changes.

## Personal configuration

TV/AVR automation, pairings, account data and host addresses stay outside the
shared image. Files in `/var/home`, `/var/lib` and `/etc` survive OS updates.
Recreate Python virtual environments if the Python minor version changes.
See [image scope](IMAGE-SCOPE.md) for planned clean upstream MoonDeck preinstallation;
that feature is separate from this OS/channel update and is not yet packaged.
Existing personal MoonDeck forks are preserved.
