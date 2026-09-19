#!/usr/bin/python3
"""Fetch verified upstream application payloads inside the image build."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

here = Path(__file__).resolve().parent
sources = json.loads((here / 'sources.json').read_text())
share = Path('/usr/share/moonmachine')
share.mkdir(parents=True, exist_ok=True)
shutil.copy2(here / 'sources.json', share / 'sources.json')
shutil.copytree(here / 'licenses', share / 'licenses')
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for name, source in sources.items():
        dest = tmp / name
        subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--output', str(dest), source['url']], check=True)
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == source['sha256'], f'{name}: checksum mismatch'
    (tmp / 'moonlight').chmod(0o755)
    subprocess.run([str(tmp / 'moonlight'), '--appimage-extract'], cwd=tmp, stdout=subprocess.DEVNULL, check=True)
    target = Path('/usr/lib/moonmachine')
    target.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp / 'squashfs-root'), target / 'moonlight')
    shutil.copy2(tmp / 'decky', share / 'PluginLoader')
    (share / 'PluginLoader').chmod(0o755)
    with zipfile.ZipFile(tmp / 'moondeck') as archive:
        for item in archive.infolist():
            path = Path(item.filename)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'moondeck':
                raise ValueError(f'Unexpected archive path: {path}')
            if '.git' in path.parts:
                continue
            archive.extract(item, share)
            mode = (item.external_attr >> 16) & 0o777
            if mode:
                (share / path).chmod(mode)
    # Generate defaults using the pinned upstream schema, without modifying the plugin.
    import sys
    sys.path.insert(0, str(share / 'moondeck/python'))
    from lib.plugin.settings import UserSettingsManager
    defaults = UserSettingsManager('/unused')._default_settings()
    defaults['clientId'] = ''  # Unique identity is generated at first boot.
    defaults['useMoonlightExec'] = True
    defaults['moonlightExecPath'] = '/usr/bin/moonlight'
    (share / 'moondeck-defaults.json').write_text(json.dumps(defaults, indent=2) + '\n')
subprocess.run(['systemctl', 'enable', 'moonmachine-setup.service'], check=True)
