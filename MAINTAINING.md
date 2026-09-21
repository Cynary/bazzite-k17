# Maintaining Moonmachine

This is the build and release checklist for the project's maintainer. For
installation, see [RELEASES.md](RELEASES.md).

There is one image: the full custom kernel with BORE and ThinLTO. The root
`Containerfile` pins the Bazzite base. Kernel build tools and configuration are
in `experimental/bore-thinlto/`.

## Build the image

Build/package the kernel using the [kernel build notes](experimental/bore-thinlto/README.md).
Prepare an empty build directory with the matching kernel RPMs:

```sh
RPM_DIR=/path/to/kernel-rpms IMAGE_CONTEXT=/path/to/empty-context \
  ./experimental/bore-thinlto/prepare-image.sh
podman build -t localhost/moonmachine:test /path/to/empty-context
```

The context includes the kernel RPMs, boot defaults and application sources/patches.
The first build stage compiles patched Moonlight, MoonDeck and Gamescope. See
[the application patch notes](apps/README.md) for version pins, patch removal,
and how installed plugins receive updates. Decky and the Python dependency bundle
are checksum-verified downloads. MoonDeck's dependency archive is a moving
nightly asset; review and update its checksum if upstream replaces it.
Compilation uses all available CPU cores by default.

The image installs Moonlight under `/usr/lib/moonmachine` and bundles
Decky/MoonDeck under `/usr/share/moonmachine`. First-boot setup creates a unique
client identity. Later boots update image-managed MoonDeck code without replacing
settings or independently installed plugins. Setup needs no network access.

## Update the base or kernel

Check upstream Bazzite changes before advancing the base digest. Compare the
kernel, firmware, graphics stack and boot integration. Rebase the carried patches
and rebuild the kernel and out-of-tree modules when needed. Verify compatibility by building and booting the updated image.

The full kernel is necessary for BORE and ThinLTO. DKMS, which rebuilds additional
modules after a kernel update, cannot replace those changes. Rust kernel modules
are currently disabled because this kernel configuration combines ThinLTO and BTF.
Specialty out-of-tree drivers removed by `install-image.sh` need separate work if
support is added later.

## Test before publishing

Keep a working OS copy in the boot menu before a test. `ostree admin status` lists
these copies (called deployments); `ostree admin pin INDEX` keeps the selected
one from being removed automatically. Use the index of the running copy, not a
number copied from someone else's machine.

Build/lint the image, then boot the exact result on the K17. Check boot logs,
4K120/10-bit/HDR, actual TV VRR behaviour, return to fixed refresh, controllers,
networking, streaming, and suspend/resume. Test the application setup in a clean
home directory, repeat it, and check that an existing installation is unchanged.
Record what was actually tested and what still needs visual confirmation.

## Publish and update the channel

1. Export the tested image as an OCI directory with `podman save --format oci-dir`.
   Record its manifest digest with `skopeo inspect --raw oci:PATH | sha256sum`.
2. Archive the directory and split it below GitHub's 2 GiB per-file limit. Upload
   `image.oci.tar.part-*`, `IMAGE-SHA256SUMS` and `cosign.pub` to a numbered release
   such as `moonmachine-YYYYMMDD.1`. Include useful release notes and test limits.
3. Run **Publish tested full-kernel image** with the release name and digest. It
   publishes the exact archive, without rebuilding it, and signs it in both the
   native containers/image format used by bootc and the Cosign format.
4. Run **Promote tested Moonmachine release** with that release and digest. It
   verifies signatures before pointing `:moonmachine` at the image.
5. Check the signed channel on hardware and run `bootc upgrade --check` and
   `uupd update-check`. The latter returns 77 when no update is available.

`COSIGN_PRIVATE_KEY` and `COSIGN_PASSWORD` are repository secrets. Only the public
key belongs in the source tree and image. Enrollment installs a policy limited
to this image repository, preserving other repositories' policies.

To withdraw a bad release, promote a previous tested, signed release. Users then
receive it through the same update process. Leave numbered artifacts available
for diagnosis and recovery. Publishing here does not submit changes upstream.
