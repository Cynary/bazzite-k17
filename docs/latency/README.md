# Latency figure data

`data/*.csv` contains anonymized intervals extracted from per-frame traces. There
are no addresses, host names, game account identifiers or absolute timestamps.
`extract.py` records the extraction rules. It joins submission IDs to measured
DRM feedback (`latch_time_kind=2`), deduplicates feedback and excludes the first
30 seconds by pacer arrival. Unmatched submissions are not counted as displayed
frames. Zero drops refers to the trace's dropped-frame counter in those windows.

Sources:

- `before-clock-fix.csv`: `tail-ab-baseline.csv`, previous Direct YUV build.
- `release-yuv444.csv`: `release-ready-true.csv`.
- `release-rgb444.csv`: `release-mode-2.csv`.
- `release-vulkan444.csv`: `release-mode-3.csv`.
- `release-yuv420.csv`: `release-overlay-1.csv`, short pre-overlay window.

The four release traces come from image `moonmachine-20260922.2`, digest
`sha256:78a8822139dcdf80abd7fafe1282bef3cb6b38928228bbf8c6a87b4225d93282`.
The historical-checkpoint chart uses the individually described experiments in
[TIMING-VALIDATION.md](../TIMING-VALIDATION.md); it has a different start boundary
and must not be combined into a single cumulative speedup calculation.

Rebuild PNG and SVG figures and numerical summaries:

```sh
python3 -m venv .venv
.venv/bin/pip install matplotlib numpy
.venv/bin/python docs/latency/plot.py
```

`other_ms` is total minus the three explicitly measured stages. It includes
receipt/dispatch and pacing; it is not a measurement of intentional buffering
alone. GPU decode wait is observed synchronization time, not a GPU timer query.
The p99 summary uses sorted sample index `floor(0.99*n)`, matching the release
report. The curves show all samples rather than synthesizing a distribution
from percentiles. Publication figures are snapshots of separate live runs.
