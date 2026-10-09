#!/usr/bin/python3
"""Fetch the exact tested revisions of the application forks."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

here = Path(__file__).resolve().parent
sources = json.loads((here / 'sources.json').read_text())
root = Path(sys.argv[1])
names = sys.argv[2:] or ['moonlight', 'moondeck', 'gamescope', 'libplacebo', 'flydigi-control']
for name in names:
    source = sources[name]
    dest = root / name
    subprocess.run(['git', 'init', str(dest)], check=True)
    def git(*args):
        return subprocess.run(['git', '-C', str(dest), *args], check=True)
    git('fetch', '--depth=1', source['repository'], source['commit'])
    git('checkout', '--detach', 'FETCH_HEAD')
    actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != source['commit']:
        raise RuntimeError(f'{name}: wrong source revision')
    git('submodule', 'update', '--init', '--recursive', '--depth=1')

if 'moondeck' not in names:
    sys.exit(0)

# Preserve the tested CPython 3.13 wheel set used by Decky's plugin runtime.
# Each wheel has an immutable URL/hash; an upstream nightly replacement cannot
# silently replace dependencies or prevent rebuilding this source revision.
wheels = json.loads((here / 'moondeck-wheels.json').read_text())
requirements = {}
for line in (root / 'moondeck/defaults/python/requirements.txt').read_text().splitlines():
    line = line.split('#', 1)[0].strip()
    if line:
        name, version = line.split('==')
        requirements[name.strip()] = version.strip()
if {wheel['name']: wheel['version'] for wheel in wheels} != requirements:
    raise RuntimeError('MoonDeck requirements changed; update and validate the wheel lock')
with tempfile.TemporaryDirectory() as tmp:
    for wheel in wheels:
        archive_path = Path(tmp) / wheel['filename']
        subprocess.run(['curl', '-fL', '--retry', '3', '-o', str(archive_path), wheel['url']], check=True)
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != wheel['sha256']:
            raise RuntimeError(f"MoonDeck wheel checksum mismatch: {wheel['filename']}")
        with zipfile.ZipFile(archive_path) as archive:
            for item in archive.infolist():
                path = Path(item.filename)
                if path.is_absolute() or '..' in path.parts or any(p.endswith('.data') for p in path.parts):
                    raise ValueError(f'Unsupported wheel path: {path}')
                if not item.is_dir():
                    target = root / 'moondeck/defaults/python/externals' / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(item))
