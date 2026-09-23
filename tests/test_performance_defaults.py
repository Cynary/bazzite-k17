"""Test hardware selection and preservation of later user choices."""
from pathlib import Path
import os
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

helper = runpy.run_path(os.environ.get('MOONMACHINE_DEFAULT_HELPER', '/usr/libexec/moonmachine-performance-default'))

class PerformanceDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sysfs = self.root / 'sys'
        self.stamp = self.root / 'var/applied'
        self.opt_out = self.root / 'disabled'
        self.run = Mock()

    def k17(self, maximum=1850):
        dmi = self.sysfs / 'class/dmi/id'
        dmi.mkdir(parents=True)
        (dmi / 'sys_vendor').write_text('GMKtec\n')
        (dmi / 'product_name').write_text('NucBox K17\n')
        gpu = self.sysfs / 'bus/pci/devices/0000:00:02.0'
        gpu.mkdir(parents=True)
        (gpu / 'vendor').write_text('0x8086\n')
        for gt, max_freq in ((0, maximum), (1, 1200)):
            freq = gpu / f'tile0/gt{gt}/freq0'
            freq.mkdir(parents=True)
            (freq / 'min_freq').write_text('400\n')
            (freq / 'rp0_freq').write_text(str(max_freq))

    def apply(self):
        helper['apply_default'](self.stamp, self.opt_out, self.sysfs, self.run)

    def test_k17_defaults_are_applied_once(self):
        self.k17()
        self.apply()
        self.run.assert_called_once_with(['tuned-adm', 'profile', 'moonmachine-k17-streaming'], check=True)
        self.run.reset_mock()
        self.apply()
        self.run.assert_not_called()

    def test_other_hardware_gets_no_k17_gpu_settings(self):
        self.apply()
        self.run.assert_called_once_with(['tuned-adm', 'profile', 'moonmachine-streaming'], check=True)

    def test_failed_selection_is_not_marked_complete(self):
        self.run.side_effect = subprocess.CalledProcessError(1, 'tuned-adm')
        with self.assertRaises(subprocess.CalledProcessError):
            self.apply()
        self.assertFalse(self.stamp.exists())

    def test_incompatible_gpu_is_not_programmed(self):
        self.k17(maximum=1500)
        with self.assertRaises(RuntimeError):
            self.apply()
        self.run.assert_not_called()
        self.assertFalse(self.stamp.exists())

    def test_opt_out_is_preserved(self):
        self.opt_out.touch()
        self.apply()
        self.run.assert_not_called()
        self.assertFalse(self.stamp.exists())

if __name__ == '__main__':
    unittest.main()
