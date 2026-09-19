"""Run inside the built image: python3 /tmp/test_app_setup.py."""
import asyncio
import json
from pathlib import Path
import pwd
import runpy
import sys
import tempfile
import unittest

share = Path('/usr/share/moonmachine')
seed = runpy.run_path('/usr/libexec/moonmachine-setup')['seed']
sys.path.insert(0, str(share / 'moondeck/python'))
from lib.plugin.settings import UserSettingsManager

class SetupTests(unittest.TestCase):
    def test_clean_setup_repeat_upgrade_and_unique_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            identities = []
            for name in ['alice', 'bob']:
                home = base / name
                home.mkdir()
                account = pwd.struct_passwd((name, 'x', 1000, 1000, '', str(home), '/bin/bash'))
                units = base / (name + '-units')
                self.assertTrue(seed(account, share, units))
                settings = home / '.config/moondeck/settings.json'
                data, migrated = asyncio.run(UserSettingsManager(settings).read())
                self.assertFalse(migrated)
                self.assertTrue(data['useMoonlightExec'])
                self.assertEqual(data['moonlightExecPath'], '/usr/bin/moonlight')
                identities.append(data['clientId'])
                self.assertTrue((home / '.local/share/Steam/.cef-enable-remote-debugging').exists())
                self.assertTrue((home / 'homebrew/services/PluginLoader').stat().st_mode & 0o111)
                self.assertEqual(json.loads((home / 'homebrew/plugins/moondeck/package.json').read_text())['version'], '1.12.2')
                # Updates must preserve changed settings and installed plugin bytes.
                settings.write_text('{"user-setting":"preserve me"}')
                marker = home / 'homebrew/plugins/moondeck/package.json'
                marker.write_text('installed plugin: preserve me')
                unit_before = (units / 'plugin_loader.service').read_bytes()
                self.assertFalse(seed(account, share, units))
                self.assertEqual(settings.read_text(), '{"user-setting":"preserve me"}')
                self.assertEqual(marker.read_text(), 'installed plugin: preserve me')
                self.assertEqual((units / 'plugin_loader.service').read_bytes(), unit_before)
            self.assertNotEqual(*identities)

    def test_unmanaged_homebrew_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'homebrew').mkdir()
            account = pwd.struct_passwd(('alice', 'x', 1000, 1000, '', str(home), '/bin/bash'))
            self.assertFalse(seed(account, share, home / 'units'))
            self.assertEqual(list((home / 'homebrew').iterdir()), [])

if __name__ == '__main__':
    unittest.main()
