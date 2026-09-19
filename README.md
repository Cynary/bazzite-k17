# Bazzite K17 — stock-kernel FRL/VRR candidate

Custom Bazzite Deck image retaining the **stock OGC kernel and all its packaged
modules**, with matched `xe.ko` and `drm_display_helper.ko` replacements.
The complete carried patch stack is in `kernel-patches/`; provenance and hardware notes are in `kernel-notes/`. A release also preserves the original kernel Git history.

This is an experimental Lunar Lake / GMKtec K17 image, developed with Codex.
TV-level HDR/VRR validation is required before treating a new candidate as stable.
Secure Boot is not supported by this initial build: replacement modules are not
signed with an enrolled key. This does not change the machine's firmware settings.

## Build

`podman build -t localhost/bazzite-k17:candidate .`

The Containerfile pins the Bazzite base by digest, the stock kernel release and
the original OGC source commit and carried patch stack. Both modules are built against that base's exact
kernel-devel tree and BTF extracted from its stock kernel image. No forced module
loading or vermagic rewriting is used. Module selection and initramfs contents
are checked during the build. Build metadata is under `/usr/share/k17-frl/build`.

The workflow builds and publishes **candidate** and immutable commit tags only.
It does not promote stable or automatically update the K17. Rebuilding with the
same base is not an upstream OS upgrade; updates require an explicit base/kernel
change, rebuild, and hardware qualification. The compiler packages are resolved
from Fedora repositories and recorded; this is not a bit-reproducible toolchain.

## Deployment and recovery

Keep the existing working and stock deployments pinned before switching. Clear
prototype local kernel overrides in the new deployment, otherwise they defeat the
purpose of the stock-kernel image. Do not blindly reset/reboot into a half-prepared
state. See [the validation record](VALIDATION.md) for the exact published digest,
boot results, and remaining hardware checks.

Images use the public `ghcr.io/cynary/bazzite-k17` package, with public visibility
checked by CI. The temporary `bazzite-k17-private` package is also public, but
future builds use the original name. Builds sign with a repository-specific key,
without a transparency-log upload. The verification key is `cosign.pub`; the
signing key/password remain repository secrets.
Verify each new image digest with:

```sh
cosign verify --key cosign.pub --insecure-ignore-tlog=true "$IMAGE@$DIGEST"
```

The transparency-log check is deliberately omitted for these key-based signatures;
verification still requires the pinned public key. Initial historical candidates
used GitHub OIDC keyless signing; see `VALIDATION.md` for their identity and digest.
The installed `ostree-unverified-*` transport does not enforce Cosign verification
itself, so verify each selected digest before staging. No unattended promotion is
enabled. Public images can be pulled anonymously; local OCI deployment is
also available for offline testing.

Pinning preserves recovery deployments; it is not an update lock. Do not infer
visual stability from a clean kernel log. Confirm actual refresh behavior, HDR,
10-bit output, transitions, audio, suspend/resume and intended controllers.

## Maintenance

Changes to kernel/base digests require a complete rebuild of the pair. Source API
conflicts or module validation errors fail the build. See the
[maintenance plan](kernel-notes/MAINTENANCE.md).

Source, releases, and images are public. No patches or reports will be submitted
to upstream kernel maintainers without an explicit user request.
