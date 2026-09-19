# K17 tuning experiments, 2026-09-19

These are ad-hoc measurement tools for the installed K17, not production services or generic benchmarks. The Python scripts require root for RAPL, preemption and BPF control. Review paths, scheduler state, thermal limits and restore settings before reuse. compare.py assumes the verified initial state: lazy preemption and no active sched_ext scheduler; it restores that state and the original EPP settings. render-compare.py temporarily instruments the existing K17 VRRTest and restores main.lua in finally. It uses this machine's existing Steam shortcut ID. Do not run concurrently with other scheduler managers or tuning tools.

## Thermal load

stress-ng: eight matrixprod CPU workers, 180 seconds. CPU remained fully busy near 25 W. Peak 74 C; final-minute mean 72.3 C and 24.92 W. No thermal-throttling counter increases. Turbostat measured about 3.2 GHz average busy frequency during steady load. All eight stressors passed. This is a short CPU-only load test at current power limits, not a combined CPU/GPU soak or validation of hardware emergency shutdown. Fan RPM/acoustic response was unavailable. ACPI's 27.8 C fallback was not used; temperatures came from coretemp.

## CPU scheduling screen

latency.c runs as an ordinary non-realtime task: wake at 120 Hz, consume 1 ms of thread CPU time, record completion relative to the requested wake deadline. Eight background matrixprod workers compete for CPU. Each run has 1800 samples (15 s). Two passes use reversed configuration order. Gaming Mode/Steam remains running. This is synthetic deadline latency, not game FPS or input-to-photon latency. All configurations retain the 25 W power limit and security mitigations.

| Setting | Completion p99, run 1 / run 2 (ms) | Missed 8.33 ms deadlines, total |
|---|---:|---:|
| Default EEVDF, lazy, balance_performance | 3.873 / 3.515 | 0 |
| Full preemption only | 3.771 / 3.870 | 0 |
| LAVD default/autopilot | 5.434 / 4.811 | 1 |
| BPFLAND default | 2.761 / 2.828 | 1 |
| Performance EPP only | 3.853 / 2.742 | 0 |

BPFLAND improves p99 here but had a 10.486 ms maximum in its second run. Full preemption is not an improvement; performance EPP is inconsistent. No setting is qualified for default deployment on these short tests alone.

## Render check

render-compare.py launches VRRTest through its actual Steam shortcut at 90 FPS, with eight background CPU workers. After five seconds warmup it records 25 seconds of application loop intervals. Four runs use default, BPFLAND, BPFLAND, default order. These are application frame intervals, not measurements of panel refresh or scanout. No visual validation was available.

Results: default p99 13.723/13.824 ms; BPFLAND 12.936/12.634 ms. Maximum intervals default 15.812/15.298 ms; BPFLAND 14.053/13.146 ms. No intervals exceeded 16.667 ms in any render run. BPFLAND was selected as a reversible on-machine trial, not a release-qualified gaming improvement. Full preemption and performance EPP were restored to defaults. VRRTest instrumentation was removed and the app exited.

## Applied trial and rollback

Use the existing scx_loader with default_sched="scx_bpfland", default_mode="Auto" and empty BPFLAND auto_mode arguments. Service enabled at boot. Keep lazy preemption, balance_performance EPP, current 25 W limits and Btrfs zstd:1. Real-game/Moonlight, mixed CPU/GPU load, suspend/resume and reboot validation remain before release qualification.

Immediate return to EEVDF: `sudo scxctl stop`. Persistent return: `sudo systemctl disable --now scx_loader.service`, and restore /etc/scx_loader/config.toml.pre-k17-tuning. The kernel also falls back to its fair scheduler if the BPF scheduler fails. Do not enable another scheduler service concurrently.

A short Steam-menu idle check measured package power about 2.90 W with BPFLAND versus 2.85 W with EEVDF (three two-second samples each). This is only a sanity check, not an energy-efficiency benchmark. System returned to BPFLAND Auto afterward; temperature fell to 45 C and thermal-throttling counters remained zero. No new kernel warnings, display underruns or flip timeouts were observed during the tests. No failed systemd units.
