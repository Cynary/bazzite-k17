# K17 BORE + ThinLTO experiment

Requested explicitly by the user. No AutoFDO or Propeller. Not a stable release.

## Inputs

- Source: https://github.com/Cynary/linux-k17-frl/tree/k17-bore-thinlto
- Exact source commit: 8cff674dac5e46b6452d4349ed3f3483d6cff1bc.
- Existing FRL/VRR and recovery base: a5a7dbdf33954095909d0ad53d953a993c31b09c.
- BORE 6.8.0 from firelzrd/bore-scheduler commit 076b60f7b147827e89da77601662751a36c57831, stable linux7.3-rc2 patch, author Masahito S.
- OGC's 7.2.4 tree has the flattened EEVDF changes expected by the 7.3 patch. The older 7.2-rc1 patch was not used. Two adaptations: locate bore_ctx before task_struct without the newer task_ipi_mask context; use the existing update_curr helper in yield_task_fair. Formatting-only Kconfig whitespace cleanup.
- The Wi-Fi CLC fixes match the tested module replacement.
- Xone: 982cbcb019ae4d2bee5ae69385223409ee555c88 plus this repository's two xone-patches, rebuilding every GIP/gamepad/transport module for the new ABI.
- Compiler: Clang/LLD 22.1.8; rustc 1.98.1; bindgen 0.72.1 in the Fedora 44 K17 build container. The abandoned laptop build used bindgen 0.73.2. Tool versions must be checked when reproducing; they are not downloaded automatically by these scripts.
- Config: actual running stock config in stock.config; resolved candidate config in candidate.config. Retains BTF and UBSAN (Clang's array-bounds implementation); Rust kernel modules are disabled because this tree forbids RUST with LTO and DEBUG_INFO_BTF together, security mitigations and existing drivers. No localmodconfig pruning or CPU-native flags.

## Build and package

On a matching LLVM/Rust toolchain, place candidate.config into an empty out-of-tree build directory as .config, then:

```
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 olddefconfig
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 LD='ld.lld --threads=2' -j8 bzImage modules
```

Run stage.sh with SOURCE_DIR, BUILD_DIR, XONE_DIR and STAGE_DIR exported; XONE_DIR must contain the pinned patched xone source. It stages the complete in-tree module set plus rebuilt xone, matched build headers and kernel image. It never includes the private module-signing key. Use kernel-k17-bore.spec to package the resulting kernel-bore-stage.tar.gz in a Fedora rpmbuild container. Place only those RPMs in rpms/ for the Containerfile build.

The local Containerfile base is the already-tested recovery2 image. Its immutable OCI digest is c0009d371c13b4a8fc7eb3a9ff4ae453aa9d5acc42fe6cedb7911bbfc59a689a. This local experiment is separate from the main stock-kernel Containerfile and public candidate tag.

## Limits and recovery

The full rebuild cannot reuse old-ABI third-party modules. This K17-only test rebuilds xone; optional specialty add-ons such as DisplayLink, vendor racing-wheel drivers and other out-of-tree extras are not qualified here. The original image remains pinned for full compatibility/rollback. In-tree USB, networking, graphics and input drivers remain configured.

An image-local service condition prevents scx_loader from replacing BORE when /proc/sys/kernel/sched_bore exists. The original deployment retains its BPFLAND setup. Toggle kernel.sched_bore between 0 and 1 to isolate BORE within the same ThinLTO kernel; this does not turn off compile-time changes to task layout or default slice settings.

Secure Boot was already disabled on the test machine; no firmware security setting is changed. Generated kernel/module keys are local build secrets, not enrolled Secure Boot keys.

## Validation

Build, VM smoke test, hardware boot and benchmark outcomes will be recorded as completed. boot-smoke.c is a minimal VM init that tests both BORE runtime modes with mixed CPU/sleeping child tasks. It is not a full correctness or hardware qualification suite.

## Build host

The laptop build was stopped at the user’s request. The active build runs on the K17 in localhost/k17-bore-builder:44, built with Containerfile.builder. Source is a clean git archive of the pinned commit; build-k17.sh makes the kernel suffix explicit and uses eight compiler jobs, with LLD limited to two threads. No partial laptop objects are reused. Build log: ~/k17-option1/bore-build/build.log on K17.

## Build validation — 2026-09-19

Full K17 build completed with exit 0 after 48m06s for the successful attempt. There were three warnings: an unused DSP lock in aw87xxx audio and two existing DEVICE_ATTR macro redefinitions in ayn-ec. All 5,026 in-tree modules completed. The initial Fedora builder was missing Perl and the openssl executable; Containerfile.builder now installs both, and the incremental retry succeeded.

The kernel booted under KVM with four vCPUs and 2 GiB RAM. boot-smoke.c completed mixed CPU/sleeping task tests with kernel.sched_bore=0 and =1, printed K17_SMOKE_PASS, and shut down cleanly. This is not hardware or visual validation.

The K17 sleep inhibitor follows the active build container and releases on exit; use inhibit-build-sleep.sh with the appropriate container name for subsequent build/packaging stages.

## First hardware boot and comparisons

The K17 booted 7.2.4-k17bore1+, with sched_bore=1 and sched_ext disabled. SSH, SDDM and NetworkManager passed; no failed systemd services. Xe reported active 3840x2160 at 120 Hz, bpp=30, with BT2020_RGB. An initial FRL timeout recovered; visual confirmation remains separate. No Oops, BUG, graphics underrun or flip timeout was observed during the tests. Existing firmware ACPI warnings remain. Rust being disabled also makes the configured panic QR screen fall back to the normal user screen; this is a warning, not a panic. Xone emits a deprecated-workqueue warning.

The first image omitted dynamically requested Xbox firmware from the initramfs, causing early load warnings before the root filesystem became available. The recipe now explicitly includes all shipped xone_dongle_*.bin.xz files.

Same-kernel runtime comparison (BORE off/on/on/off), eight matrixprod background workers:

| Metric | BORE off, two runs | BORE on, two runs |
| --- | --- | --- |
| Wake latency p99, ms | 1.677 / 1.648 | 0.114 / 0.063 |
| Task completion p99, ms | 2.938 / 3.032 | 3.110 / 3.083 |
| Task completion maximum, ms | 6.249 / 5.348 | 3.519 / 3.143 |
| 8.33 ms deadline misses | 0 / 0 | 0 / 0 |
| 90 FPS test frame interval p99, ms | 13.162 / 13.247 | 13.066 / 13.081 |
| Frame interval maximum, ms | 14.558 / 14.790 | 13.463 / 14.101 |
| Frame intervals above 16.667 ms | 0 / 0 | 0 / 0 |

Interpretation: substantially lower wake latency and lower worst observed task-completion latency; no p99 task-completion improvement. The small frame-interval difference is not strong evidence of a meaningful gaming performance gain. Frame intervals come from the application's update loop, not panel scanout. Maximum observed CPU temperature in the latency tests was 69 C. BORE was restored to enabled and the test closed/restored its source afterward. These comparisons do not isolate ThinLTO against GCC, and runtime BORE disable does not remove compile-time layout/default changes. Raw results are in results/.

## Final local candidate deployed

Local OCI image `/var/lib/k17-images/bore2`, manifest digest `sha256:e12799860cc9ee12647ac9a6f5859238ef51417e9314d80f68e884b5cb631da6`, image configuration `48912802d2250e0d14877f71731df7562b8defeffa8fbd424f4684c4036c8709`. Kernel image SHA256 `af17aab87f9536e4fdf6674f44b4267605148c3e6849f05b218a1188fd1779e2`.

Final image lint: 13 passed, 1 skipped, zero warnings. All four dynamically requested Xbox firmware files were verified in the initramfs. Second hardware boot passed health checks with BORE=1 and sched_ext disabled, zero failed services, 4K120 and bpp=30 reported by Xe, and no early xone firmware-load failure. No BUG/Oops, underrun or flip timeout appeared in the checks. Startup to graphical target was 29.294 seconds (firmware 10.348, loader 4.144, kernel 0.662, initrd 4.740, userspace 9.397). The new deployment and original known-good stock-kernel deployment are pinned; the one-shot recovery timer was disarmed after success.

The final image is a local hardware-test deployment, not a promoted public stable release. TV-side visual HDR/VRR and controller-button confirmation remain outstanding. No additional kernel rebuild occurred between the measured candidate and the final firmware-packaging correction.

## Public experimental release

The identical tested OCI digest is now published as `bore-20260919.1` at
`ghcr.io/cynary/bazzite-k17`, signed with the repository key and anonymously
downloadable. The K17 verified the signature, switched to the public digest, and
rebooted successfully in 29.951 seconds. Boot verifier passed, zero failed services,
no observed BUG/Oops, underrun or flip timeout. The public deployment is pinned.
See [installation and update instructions](../../RELEASES.md). This is an
experimental prerelease; it does not promote the stock `candidate` tag or create
the moving channel by itself. The subsequently added `:moonmachine` stream
provides signed updates after explicit maintainer promotion; see RELEASES.md.
