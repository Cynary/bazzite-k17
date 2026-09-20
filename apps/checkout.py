#!/usr/bin/python3
"""Fetch exact source revisions and apply the image's patch series."""
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
for name in ('moonlight', 'moondeck'):
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
    for patch in source['patches']:
        path = str(here / 'patches' / name / patch)
        git('apply', '--check', path)
        git('apply', path)

# Reuse only the pinned upstream bundle's Python dependencies, not its code.
with tempfile.TemporaryDirectory() as tmp:
    archive_path = Path(tmp) / 'moondeck.zip'
    source = sources['moondeck']
    subprocess.run(['curl', '-fL', '--retry', '3', '-o', str(archive_path), source['url']], check=True)
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != source['sha256']:
        raise RuntimeError('MoonDeck dependency bundle checksum mismatch')
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            path = Path(item.filename)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Unsafe archive path: {path}')
            prefix = 'moondeck/python/externals/'
            if item.filename.startswith(prefix) and not item.is_dir():
                target = root / 'moondeck/defaults/python/externals' / item.filename[len(prefix):]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(item))
