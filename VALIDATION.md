# Candidate validation — September 18, 2026

## Build completed

- Stock base: `bazzite-deck@sha256:f956a8f987e40b81990d673a9f5c777691944b45858f4267ea77f2e75c14d27b`.
- Kernel: `7.2.4-ogc3.1.fc44.x86_64`, unchanged.
- Patched source: `f37b49ee569bbf42bb8d1a675040f28c8b26cac6`.
- Stock kernel image SHA256: `886f4e5f0cad0ea02649101cadfa21afee95a2e0357c684318c06a9ddba5b705`; identical before/after image customization.
- Both replacement modules compiled against stock kernel-devel, with BTF. Modpost completed without unresolved-symbol errors. Headers differ from stock only in the two deliberately patched SCDC headers.
- Fedora's pahole is 1.30; stock kernel config records 1.31. Compilation warns about the difference. Both live module BTF files were present after boot, so the kernel accepted the result. The recorded kernel configuration was not altered to hide this warning.
- Module lookup selects `/usr/lib/modules/<release>/updates/k17/{xe,drm_display_helper}.ko`; initramfs inventory confirms both are included.
- `bootc container lint`: 13 checks passed, 1 skipped.
- Stock kernel package set and xone dongle module retained. `hid_xpadneo` was not present in the base image; this build does not add it or claim Bluetooth controller validation.
- Rootless local dracut emitted xattr-copy warnings; initramfs generation and image lint completed. The locally built image booted successfully; the final deployed artifact was independently built in CI.

## Published artifact

- Public image: `ghcr.io/cynary/bazzite-k17`.
- Tested digest: `sha256:0f70ebca5af3e11740485060094b3c3ed90cf18f41e3845eabfa8e28b4b183d9`.
- Recipe revision: `4d5fde50afc610d90ecd3bed295a4f9283f593cc`.
- [Build/push run](https://github.com/Cynary/bazzite-k17/actions/runs/35402374436): build and upload passed; signing initially failed because Cosign did not share Podman's credential path.
- [Signing/publishing retry](https://github.com/Cynary/bazzite-k17/actions/runs/35403125108): succeeded for the **same digest**, without rebuilding. Future builds share a credential file between Podman and Cosign.
- Anonymous pull passed. Cosign 3.1.3 verified the certificate issuer, workflow identity, claims, and transparency-log inclusion before deployment.
- Certificate identity: `https://github.com/Cynary/bazzite-k17/.github/workflows/publish-existing.yml@refs/heads/main`.
- Issuer: `https://token.actions.githubusercontent.com`.
- Local and CI-built Xe/helper module hashes are identical.

## Deployment and boot

The first locally built candidate was imported from a local OCI directory, after
`rpm-ostree reset --overrides` cleared the prototype's five kernel replacements
and 37 removals in the *new* deployment. No reboot occurred between reset and
candidate rebase. The candidate has no local package overrides.

The machine was then rebased to the published digest with:

```sh
sudo rpm-ostree rebase ostree-unverified-registry:ghcr.io/cynary/bazzite-k17@sha256:0f70ebca5af3e11740485060094b3c3ed90cf18f41e3845eabfa8e28b4b183d9
sudo systemctl reboot
```

Signature verification was performed separately; this transport does not enforce
Cosign signatures itself. The origin is an immutable digest, not a moving tag.

Booted deployment: `d5e1f7b0db51d130c2d0e8bf86c53eaf98e55e0d14b6f7cd3e1f5e6138321d35`.
The running release is the stock `7.2.4-ogc3.1.fc44.x86_64`; the kernel binary hash
matches the original base. Both replacement modules loaded normally with BTF
present under `/sys/kernel/btf/`. No force-load or symbol-version bypass was used.
The unsigned external modules produce the expected module-signature/taint notices;
Secure Boot was disabled. SSH, SDDM and cardwired are active; no failed system units.

### Display tests on the published image

With the TV powered on, HDMI2 selected and Denon on AUX2:

- Gaming Mode selected 3840×2160 at 120 Hz, RGB, 30 bpp, no dithering;
  adjusted pixel clock 1,188,000 kHz, FRL four lanes at 10 Gbit/s.
- Gamescope HDR output and VRR feedback were both 1.
- Fullscreen VRRTest at a 70–100 FPS target sweep produced nonconstant hardware
  vblank intervals; one 179-interval sample ranged 8.336–13.797 ms.
- A 90 FPS target run also produced variable scanout. Its sampled median was
  12.356 ms, so this is **not** a claim of exact 90 FPS frame pacing.
- Disabling VRR during the test produced a fixed 8.333 ms median, with all 179
  intervals rounding to 8.3 ms. Re-enabling restored variable intervals and VRR feedback.
- Two fullscreen launch/exit cycles and the VRR off/on transition produced no
  FRL-training failures, underruns, state mismatches, flip timeouts, Oops or panic.
- The early boot `GSC proxy component not bound` message remains present; this
  is a pre-existing firmware/proxy startup diagnostic, not a claim of an entirely
  error-free kernel journal.
- The published image passed two reboots with the TV/AVR awake; the second returned to 4K120/30-bpp HDR and VRR without manual display commands.
- The one-shot boot health check passed without invoking fallback. Its temporary timer was disabled afterward; test windows and the sleep inhibitor were removed.
- Measured second startup: 78.302 s firmware + 8.276 s loader + 0.716 s kernel + 44.084 s initrd + 8.223 s userspace. Boot-speed optimization was not part of this validation.

The test content is SDR rendered through HDR output. This confirms output mode
and varying scanout, not HDR luminance accuracy or an end-to-end Moonlight decoder test.
Physical TV inspection was unavailable for this session.

### Initial failure and recovery

The first local-image boot happened while the receiver was in standby and the TV
was off. FRL training timed out, followed by state mismatches and flip timeouts.
The kernel remained remotely accessible. The original health-check pattern missed
these messages; it was corrected to reject them. No failed boot was classified as
passing display validation after inspecting the full log.

Broadcast wake packets did not wake the TV. A unicast packet to its Wi-Fi MAC/IP
with a temporary neighbor entry did; the neighbor entry was removed afterward.
After waking the chain and rebooting into the published image, link training and
VRR tests passed. This does **not** certify recovery after receiver/TV standby:
off/on, cable hotplug, and suspend/resume remain separate tests.

A subsequent [failure-path audit](https://github.com/Cynary/linux-k17-frl/blob/k17-frl-vrr-test/k17/FRL-RECOVERY.md) reproduced the TV-off failure, traced the relevant early return to the original Intel FRL series, and recovered 4K120/30-bpp HDR/VRR by restarting Gaming Mode without rebooting the OS. Power-on alone did not recover that run; robust automatic recovery remains unresolved. The audit intentionally generated kernel warnings on that boot; it made no driver changes.

## Recovery and remaining qualification

Pinned recovery deployments remain:

- Previous visually tested full kernel `7.2.4-k17vrr4+`:
  `f8bb6194a23c916ad7e5774672c1870917c199458ebf36405950e395986a29e4`.
- Original stock Bazzite:
  `641e67e8d5d894677d75b7a9a6091afb6b96a66b9551e3ceefa5848ab3d9f58b`.

Use `rpm-ostree status` / `ostree admin status` to identify the current index of a
recovery deployment, then `sudo ostree admin set-default INDEX` and reboot, or
select it in the boot menu. Indices change; do not hardcode an old index.

Pending before stable promotion: visual HDR/VRR/flicker/dropout checks, HDMI audio,
controllers, Moonlight decoding/streaming, cold boot, suspend/resume and display
power/input/hotplug recovery. The stock xone module is retained but controller
operation was not exercised. No stable tag or unattended updates were enabled.
