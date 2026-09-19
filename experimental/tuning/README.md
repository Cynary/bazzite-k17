# K17 tuning experiments, 2026-09-19

These measurement tools compare CPU scheduling under load. They require root
for RAPL, preemption and BPF control. Review the scheduler state, thermal limits
and restoration logic before running them. `compare.py` expects lazy preemption
and no active sched_ext scheduler. Do not run another scheduler manager alongside it.

For the render scripts, set `TEST_USER` to the account running Steam and
`VRRTEST_APP_ID` to that account's VRRTest shortcut ID. They expect
`~/VRRTest/main.lua`, temporarily instrument it, and restore it in `finally`.
These older sched_ext comparisons are separate from the BORE measurements and
are not the current image's scheduler configuration.

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
