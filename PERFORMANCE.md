# K17 release tuning and validation (2026-09-18)

## Measured boot improvement

The K17 (Core Ultra 5 226V / Arc 130V) booted with our stock-kernel replacement
modules before and after disabling JetKVM's unused virtual USB mass-storage
function and restoring graphical boot arguments:

| Stage | Before | After |
|---|---:|---:|
| Firmware | 71.651 s | 10.313 s |
| Bootloader | 4.596 s | 4.120 s |
| Kernel | 0.766 s | 0.703 s |
| Initramfs | 44.565 s | 4.533 s |
| Userspace to graphical target | 8.068 s | 8.368 s |
| Total | 129.649 s | 28.038 s |

User confirmed substantially faster startup with no text. This measures
systemd's graphical target, not the time until Steam finishes loading.
JetKVM remains usable for keyboard, mouse and audio. Its mass-storage function
must be re-enabled deliberately for future virtual-media installs.

Quiet boot uses quiet/rhgb, suppressed console status and cursor, and removes
drm.debug=0x6/log_buf_len=8M. Logs remain in the journal. Plymouth's existing
BGRT theme retains the firmware logo. The host's /boot/grub2/custom.cfg hides
the normal one-second menu, preserving explicit recovery/menu requests.
Firmware-generated error screens cannot be controlled by Linux.

## Display validation

FRL failure recovery is now patch 0052. User confirmed smooth 90 FPS VRR with
4K120 RGB10 HDR output when VRRTest was launched as an actual Steam shortcut.
A manually injected test over Steam's animated welcome UI was an invalid
baseline: pausing Steam's web UI removed extra refreshes, and launching from
Steam after login reproduced the smooth desktop result without overrides.
No Gamescope patch or persistent scheduler/overlay override was needed.
The test was closed after validation.

## Errors are not all eliminated

No new display underruns, flip timeouts or display state mismatch was found.
The early GSC proxy timeout coincided with delayed boot and missing mei_me /
mei_gsc_proxy in the initramfs; these are included in the next image build.
The faster reboot bound the proxy before the timeout even before that build.
There are separate firmware ACPI lookup errors, a MediaTek mt7921 firmware-init
UBSAN array-bounds report, and xone Xbox-dongle errors. These are not evidence
of an FRL regression, but prevent claiming a completely clean kernel log or
fully qualified release. They require separate triage; do not hide them by
disabling sanitizers or removing controller drivers.

## Performance decisions

Keep the stock OGC kernel and exact-ABI Xe/display-helper pair for this release.
Current kernel already provides HZ=1000, PREEMPT_DYNAMIC (lazy active),
SCHED_CLASS_EXT, Intel HWP/intel_pstate, and MGLRU enabled (0x7).
Bazzite uses balanced-bazzite / balance_performance EPP and zstd zram.
The NVMe uses kyber. Intel_pstate's powersave name does not mean a fixed low
clock; active HWP dynamically selects frequency.

CachyOS reference: https://wiki.cachyos.org/features/kernel/
- It offers ThinLTO/AutoFDO, optimized builds, BORE and other scheduler variants.
- BORE, ThinLTO and kernel-wide build flags require replacing/rebuilding the
  entire kernel and its compatible external modules; cannot be applied just
  to our Xe module. That would give up much of option 1's maintenance benefit.
- CPU-native kernel compilation does not accelerate fixed-function video
  decoding directly. Workload profiles are needed to justify AutoFDO.
- This Lunar Lake processor is an x86-64-v3 target, not AVX-512/v4. Avoid
  -march=native on unrelated CI hosts. Keep the existing distro ABI for now.

Next benchmark candidates, all reversible and one at a time:
1. Default EEVDF versus scx_lavd and scx_bpfland, already installed and supported
   by the running kernel. Test foreground game/stream during background load.
2. Dynamic full versus lazy preemption, and balanced versus performance EPP.
   Measure tail frame times, power/temperature and fan noise; P/E-core affinity
   only if traces show migration-related delays. Do not disable E cores blindly.
3. kyber versus none/mq-deadline only with real install/shader-cache I/O loads.
4. Evaluate a separate full-kernel BORE candidate for interactive responsiveness
   under contention, preserving the stock-based release as fallback. Average
   FPS alone is not a sufficient acceptance test; include input-to-frame latency,
   UI stalls and frame-time tails during downloads, shader compilation and I/O.

Benchmarks must use a real Steam-launched game/stream, 4K120 HDR+VRR, warmed
shader caches, repeat runs, dropped-frame counts and p95/p99 frame-time tails.
A moving-bar test is display validation, not a general performance benchmark.
Do not disable security mitigations, thermal management or idle states for an
unmeasured gain. Keep E cores available for background work and power headroom
for the shared-package GPU.

Scheduler reference: https://wiki.cachyos.org/configuration/sched-ext/
Intel HWP: https://docs.kernel.org/admin-guide/pm/intel_pstate.html

## Filesystem

Keep Btrfs on the existing NVMe. The OS also uses composefs over OSTree;
filesystem replacement is not an image-only change and would require data
migration/reinstall. Btrfs gives checksums, CoW/reflinks and compression; XFS
or ext4 may win some particular I/O workloads but are not a demonstrated win
for this streaming client. CachyOS supports these alternatives rather than
establishing a universally fastest filesystem.

Observed SSD optimizations, async discard and free-space-tree are enabled.
The fstab requests zstd:1 but live mount options do not show compression:
first mount occurs in initramfs with rootflags=subvol=root. Ensure the intended
compression option is included at first mount before claiming it is active.
Compression affects new writes, not existing data retroactively. Do not run a
whole-disk recompression/defragmentation or disable CoW globally.

Filesystem references:
- https://wiki.cachyos.org/installation/filesystem/
- https://btrfs.readthedocs.io/en/stable/Administration.html

## Publication policy

Our source and images are public. No upstream kernel patch/report submission
is authorized. Candidate publishing does not imply stable promotion or an
automatic deployment to the K17.

## Full-kernel maintenance scope

BORE is a reasonable experimental track, not a promise of a universal speedup.
Use the same OGC base and configuration initially, add only a matching BORE
patch, and rebuild the entire kernel plus its external controller modules.
CI should produce versioned images, retain a known-good deployment and prevent
automatic candidate promotion. Routine stable updates can be automated, but
boot, suspend/resume, controllers and FRL/HDR/VRR still need hardware validation.
Major rebases can need manual scheduler/graphics patch conflict resolution.
The existing experimental HDMI stack is itself a substantial maintenance
commitment; BORE adds scheduler coverage and full-kernel packaging, rather than
requiring every update to be rebuilt by hand. Do not bundle LTO, new compiler
flags and scheduler changes into the first comparison.

BORE upstream: https://github.com/firelzrd/bore-scheduler

Compression correction was staged on the K17 with:
`rpm-ostree kargs --delete=rootflags --append=rootflags=subvol=root,compress=zstd:1`
(the previous rootflags contained only subvol=root). It requires a reboot and
verification of the live mount options; no existing files were recompressed.
