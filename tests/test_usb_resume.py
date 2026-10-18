import errno
import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import Mock, patch

source = Path(__file__).resolve().parents[1] / "files/usr/libexec/moonmachine-usb-resume.py"
if not source.exists():
    source = Path("/usr/libexec/moonmachine-usb-resume.py")
spec = importlib.util.spec_from_file_location("usb_resume", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RecoveryTests(unittest.TestCase):
    def run_case(self, replies, check=False):
        hub = Mock()
        hub.status.side_effect = replies
        result = module.recover(hub, check_only=check, delay=lambda _: None)
        return result, hub

    def test_healthy_does_not_reset(self):
        result, hub = self.run_case(["00000000"])
        self.assertEqual(result, "healthy")
        hub.reset.assert_not_called()

    def test_transient_stall_does_not_reset(self):
        result, hub = self.run_case([OSError(errno.EPIPE, "stall"), "00000000"])
        self.assertEqual(result, "healthy")
        hub.reset.assert_not_called()

    def test_persistent_stall_resets_once_and_verifies(self):
        result, hub = self.run_case([OSError(errno.EPIPE, "stall")] * 3 + ["00000000"])
        self.assertEqual(result, "recovered")
        hub.reset.assert_called_once()
        self.assertEqual(hub.status.call_count, 4)

    def test_check_only_never_resets(self):
        result, hub = self.run_case([OSError(errno.EPIPE, "stall")] * 3, True)
        self.assertEqual(result, "stalled")
        hub.reset.assert_not_called()

    def test_unrelated_errors_do_not_reset(self):
        for code in (errno.ETIMEDOUT, errno.ENODEV, errno.EPERM, errno.EPROTO):
            hub = Mock()
            hub.status.side_effect = OSError(code, "failure")
            with self.assertRaises(OSError):
                module.recover(hub, delay=lambda _: None)
            hub.reset.assert_not_called()

    def test_failed_verification_is_not_success_or_reset_loop(self):
        hub = Mock()
        hub.status.side_effect = OSError(errno.EPIPE, "stall")
        with self.assertRaises(OSError):
            module.recover(hub, delay=lambda _: None)
        hub.reset.assert_called_once()

    def test_identity_mismatch_does_not_open_device(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "idVendor").write_text("ffff")
            with patch.object(module.os, "open") as open_device:
                with self.assertRaises(ValueError):
                    module.Hub(path, {"idVendor": "05e3"})
                open_device.assert_not_called()

    def test_storage_descendant_prevents_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "child").mkdir()
            (path / "child/bInterfaceClass").write_text("08")
            hub = module.Hub.__new__(module.Hub)
            hub.path, hub.fd = path, 42
            with patch.object(module.fcntl, "ioctl") as ioctl:
                with self.assertRaises(ValueError):
                    hub.reset()
                ioctl.assert_not_called()

    def test_missing_host_context_recovers_even_when_control_works(self):
        hub = Mock()
        hub.status.return_value = '00000000'
        context = Mock(side_effect=[False, False, False, True])
        self.assertEqual(module.recover(hub, context_check=context,
                                       delay=lambda _: None), 'recovered')
        hub.reset.assert_called_once()

    def test_missing_context_check_only_does_not_reset(self):
        hub = Mock()
        self.assertEqual(module.recover(hub, check_only=True,
                                       context_check=lambda: False,
                                       delay=lambda _: None), 'stalled')
        hub.reset.assert_not_called()

    def test_context_still_missing_is_not_success(self):
        hub = Mock()
        with self.assertRaises(ValueError):
            module.recover(hub, context_check=lambda: False, delay=lambda _: None)
        hub.reset.assert_called_once()

    def test_port_reenabled_even_if_disable_write_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            port = path / 'port'
            port.mkdir()
            (port / 'disable').write_text('0')
            hub = module.Hub.__new__(module.Hub)
            hub.path, hub.fd = path, None
            writes = []
            def write(p, value):
                writes.append(value)
                if value == '1':
                    raise OSError(errno.EIO, 'failed disable')
            with patch.object(Path, 'write_text', write):
                with self.assertRaises(OSError):
                    hub.reset()
            self.assertEqual(writes, ['1', '0'])

    def test_reenumeration_reopens_new_device_and_closes_old_fd(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'port').mkdir()
            (path / 'port/disable').write_text('0')
            (path / 'bConfigurationValue').write_text('1')
            hub = module.Hub.__new__(module.Hub)
            hub.path, hub.fd = path, 42
            hub.open = Mock()
            with patch.object(module.os, 'close') as close, \
                    patch.object(module.time, 'sleep'):
                hub.reset()
            close.assert_called_once_with(42)
            hub.open.assert_called_once()
            self.assertEqual((path / 'port/disable').read_text(), '0')

    def test_unconfigured_children_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'bad').mkdir()
            (path / 'good').mkdir()
            (path / 'bConfigurationValue').write_text('1')
            (path / 'bad/bConfigurationValue').write_text('')
            (path / 'good/bConfigurationValue').write_text('1')
            hub = module.Hub.__new__(module.Hub)
            hub.path = path
            self.assertEqual(hub.unconfigured_children(), ['bad'])


if __name__ == "__main__":
    unittest.main()
