#!/usr/bin/python3
"""Require the K17 repository key while preserving other registry policies."""
import json
from pathlib import Path

policy = Path('/etc/containers/policy.json')
data = json.loads(policy.read_text())
data.setdefault('transports', {}).setdefault('docker', {})['ghcr.io/cynary/bazzite-k17'] = [{
    'type': 'sigstoreSigned',
    'keyPath': '/etc/pki/containers/cynary-k17.pub',
    'signedIdentity': {'type': 'matchRepository'},
}]
policy.write_text(json.dumps(data, indent=4) + '\n')
