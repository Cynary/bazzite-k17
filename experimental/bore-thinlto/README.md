# Kernel build notes

Moonmachine builds the full kernel with BORE 6.8 and Clang ThinLTO. AutoFDO and
Propeller are not enabled. Image publishing is described in [MAINTAINING.md](../../MAINTAINING.md).

## Inputs

- Kernel source: https://github.com/Cynary/linux-k17-frl/tree/k17-bore-thinlto
- Exact source commit: `b6a571d6677f23a2893d95a30d102cc44abc888a`.
- OGC base: `43d13ad09df8a544c032f75dc84fddd2aefe8f76`.
- BORE source: `firelzrd/bore-scheduler`, commit `076b60f7b147827e89da77601662751a36c57831`.
- Xone: `982cbcb019ae4d2bee5ae69385223409ee555c88` plus the two patches in `xone-patches/`.
- Compiler used: Clang/LLD 22.1.8; bindgen 0.72.1. See `Containerfile.builder`.
- Resolved configuration: `candidate.config`; reference OGC configuration: `stock.config`.

The BORE patch targets the flattened EEVDF code also present in OGC's tree.
Adaptations place bore_ctx before task_struct without the newer task_ipi_mask
context and use the existing update_curr helper in yield_task_fair.

## Compile and package

Use a clean source checkout and a separate output directory:

```sh
cp candidate.config "$BUILD_DIR/.config"
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 olddefconfig
make -C "$SOURCE_DIR" O="$BUILD_DIR" LLVM=1 LD='ld.lld --threads=2' -j8 bzImage modules
```

Run `stage.sh` with SOURCE_DIR, BUILD_DIR, XONE_DIR and STAGE_DIR set. It gathers
the kernel, all in-tree modules, rebuilt xone and matching headers. Package its
`kernel-bore-stage.tar.gz` using `kernel-k17-bore.spec` in a Fedora rpmbuild
container. Pass the resulting RPM directory to `prepare-image.sh`.

The image checks module version compatibility, includes dynamically requested
Xbox firmware in the early boot image, and prevents scx_loader from replacing
BORE. BTF and UBSAN remain enabled. Rust modules are disabled because this tree
cannot combine Rust with both LTO and BTF. Optional third-party drivers listed in
`install-image.sh` are removed unless rebuilt for this kernel.

## Checks and measurements

The build completed all 5,026 in-tree modules. A KVM smoke test exercised mixed
CPU and sleeping tasks with BORE both enabled and disabled. Hardware boots passed
with 4K120/30 bpp reported by Xe. ACPI firmware warnings and xone's deprecated
workqueue warning remain. Secure Boot is not supported.

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
