#!/usr/bin/python3
"""Install the source-built applications and checksum-pinned Decky loader."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
sources = json.loads((here / 'sources.json').read_text())
built = Path('/tmp/moonmachine-built')
share = Path('/usr/share/moonmachine')
share.mkdir(parents=True, exist_ok=True)
shutil.copy2(here / 'sources.json', share / 'sources.json')
shutil.copytree(here / 'licenses', share / 'licenses')
with tempfile.TemporaryDirectory() as tmp:
    dest = Path(tmp) / 'PluginLoader'
    source = sources['decky']
    subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--output', str(dest), source['url']], check=True)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != source['sha256']:
        raise RuntimeError('Decky checksum mismatch')
    shutil.copy2(dest, share / 'PluginLoader')
    (share / 'PluginLoader').chmod(0o755)
shutil.copytree(built / 'moonlight', '/usr/lib/moonmachine/moonlight')
shutil.copytree(built / 'moondeck', share / 'moondeck')
shutil.copytree(built / 'sources', share / 'sources')
sys.path.insert(0, str(share / 'moondeck/python/externals'))
sys.path.insert(0, str(share / 'moondeck/python'))
from lib.plugin.settings import UserSettingsManager
defaults = UserSettingsManager('/unused')._default_settings()
defaults['clientId'] = ''  # Unique identity is generated at first boot.
defaults['useMoonlightExec'] = True
defaults['moonlightExecPath'] = '/usr/bin/moonlight'
defaults['pauseUnfocusedSplash'] = True
(share / 'moondeck-defaults.json').write_text(json.dumps(defaults, indent=2) + '\n')
shutil.rmtree(built)
subprocess.run(['systemctl', 'enable', 'moonmachine-setup.service'], check=True)
