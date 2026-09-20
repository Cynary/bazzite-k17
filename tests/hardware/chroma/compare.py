#!/usr/bin/env python3
"""Compare the probe's RGBA float16 output against a software-decoded reference."""
import argparse
import json
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('hardware')
parser.add_argument('reference')
parser.add_argument('--tolerance', type=float, default=0.001)
args = parser.parse_args()
a = np.fromfile(args.hardware, dtype=np.float16).astype(np.float32)
b = np.fromfile(args.reference, dtype=np.float16).astype(np.float32)
if not a.size or a.size != b.size or a.size % 4:
    raise SystemExit('Empty output or mismatched RGBA dimensions')
if not np.isfinite(a).all() or not np.isfinite(b).all():
    raise SystemExit('Non-finite output')
d = np.abs(a - b).reshape(-1, 4)
result = {'pixels': len(d), 'maximum_error': d.max(axis=0).tolist(),
          'mean_error': d.mean(axis=0).tolist(),
          'p99_error': np.percentile(d, 99, axis=0).tolist(),
          'tolerance': args.tolerance, 'passed': bool(d.max() <= args.tolerance)}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
