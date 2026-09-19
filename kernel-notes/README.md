# Tested baseline — September 17, 2026

## Source provenance

- OGC base: `43d13ad09df8a544c032f75dc84fddd2aefe8f76` on `ogc-7.2.y`.
- Intel public FRL series: [171757, revision 1](https://patchwork.freedesktop.org/api/1.0/series/171757/revisions/1/mbox_with_cover/), 44 patches dated August 7, 2026. Original authors and sign-offs are preserved in the commits. This is an adapted application of the series, not an assertion that it is byte-identical to its mbox.
- Compatibility adaptation: `1b5b88468`.
- Local VRR/fix series: `7c1d5b4fe`, `ae2736138`, `d2431137f`, `e349116e5`, `35b11469e`, `f37b49ee5`.
- Exact tested source: tag `k17-vrr4-tested` → `f37b49ee5`.
- Base operating system: Bazzite Deck KDE `44.20260916`.
- Compiler: GCC 16.2.1 20260810; GNU binutils 2.47. Full build retained DWARF5/BTF and module BTF. Secure Boot was disabled; this is not a Secure Boot validation.

The additional local changes were written with OpenAI Codex. Hardware observations combine TV checks and instrumented driver/vblank measurements. These experiments require review before upstream submission, particularly the blanking calculation and VTEM/GMP transport.

## What changed

1. Prefer FRL over TMDS chroma fallback for modes above 600 MHz.
2. Correct FRL DFM integer overflows/unsigned saturation and experimental blanking control-character accounting, allowing RGB10 at FRL40.
3. Preserve the actual FRL pixel clock instead of using a TMDS deep-color calculation. The wrong 800 MHz value caused static/FIFO underruns; the tested mode needs 1188 MHz.
4. Add opt-in Lunar Lake HDMI VRR timing using the sink's HDMI VRR range. No HDMI VRR on TMDS or joined pipes in this prototype.
5. Send VTEM through the GMP packet slot and update it on fastsets. Permit the corresponding enable-mask change during fastset validation.
6. Remove the +0.5% clock budgeting tolerance from video M/N while retaining it for bandwidth budgeting. Fixed refresh changed from approximately 120.6 Hz to 120.00 Hz.

Enable the experiment at boot with `xe.experimental_hdmi_vrr=1`; it is disabled by default. This gate is for the VRR experiment, not every FRL change. FRL patches also affect shared i915 display code. Do not infer that all other platforms are tested.

## Evidence and limits

| Test | Observation |
|---|---|
| Stock Linux | 4K60; no HDMI VRR exposed on this machine |
| Patched KDE fullscreen test | User confirmed varying refresh with 4K120 RGB10/HDR output, no fullscreen flicker |
| KDE automatic VRR | Variable fullscreen, fixed desktop, no flicker when returning to desktop |
| KDE forced-always VRR | Idle brightness flicker with rapid 40–120 Hz changes; use automatic policy |
| Gaming Mode before nominal-clock fix | VRR active, intermittent brief blackouts reported |
| Gaming Mode after nominal-clock fix | User confirmed steady-target 90 FPS test stable |
| 70–100 FPS Gaming Mode sweep after fix | About ten minutes without new driver errors; separate visual confirmation was not recorded |
| Reboot into installed vrr4 | Xe autoloaded; cardwired and Gaming Mode active; 4K120, pipe bpp30/no dithering, HDR and VRR feedback enabled; native Steam preference restored VRR |
| Fixed vblank after correction | Approximately 8.333 ms, 120.00 Hz |
| Variable vblank | Nonconstant hardware intervals corroborate variable scanout; not just a TV “VRR enabled” badge |

The moving-bar test supplies SDR content in an HDR output session. This confirms simultaneous HDR signaling and VRR, not HDR luminance/color accuracy. The nominal FPS target did not produce perfectly constant presentation intervals under Gamescope; these tests do not certify frame pacing or latency.

Full kernel build passed its x86 checks (8,212,978 decoded instructions and 1,000,000 random instructions). The extracted DFM test covers RGB 8/10/12 bpc at FRL24/32/40/48. It checks arithmetic and expected acceptance boundaries; it does not prove the experimental accounting conforms to the HDMI specification.

HDMI audio, suspend/resume, hotplug/retraining, long-term stability, Moonlight end-to-end HDR/4:4:4/VRR streaming, DSC, other receivers/TVs, and other GPUs still need validation. Successful display output is separate from video decoding support. Kernel warning-free runs alone cannot prove absence of a visible link dropout.

## Building the current kernel

These are the original graphics experiments. For the current complete build,
see [kernel build notes](../experimental/bore-thinlto/README.md) and
[image maintenance](../MAINTAINING.md).
