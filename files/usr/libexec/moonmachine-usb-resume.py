#!/usr/bin/python3
"""Recover explicitly configured USB hubs that stall control requests on resume."""
import argparse
import ctypes
import errno
import fcntl
import json
import logging
import os
from pathlib import Path
import re
import time

LOG = logging.getLogger("moonmachine-usb-resume")


class Control(ctypes.Structure):
    _fields_ = [("request_type", ctypes.c_uint8), ("request", ctypes.c_uint8),
                ("value", ctypes.c_uint16), ("index", ctypes.c_uint16),
                ("length", ctypes.c_uint16), ("timeout", ctypes.c_uint32),
                ("data", ctypes.c_void_p)]


class Hub:
    def __init__(self, path, config):
        self.path = path
        self.config = config
        self.fd = None
        self.open()

    def open(self):
        path, config = self.path, self.config
        for key in ("idVendor", "idProduct", "bcdDevice"):
            actual = (path / key).read_text().strip().lower()
            if actual != config[key].lower():
                raise ValueError(f"{path.name}: {key} changed: {actual}; refusing reset")
        if (path / "bDeviceClass").read_text().strip() != "09":
            raise ValueError(f"{path.name}: not a hub")
        bus = int((path / "busnum").read_text())
        dev = int((path / "devnum").read_text())
        self.fd = os.open(f"/dev/bus/usb/{bus:03}/{dev:03}", os.O_RDWR)
        if int((path / "devnum").read_text()) != dev:
            self.close()
            raise ValueError("USB device changed while opening it")

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def context_valid(self):
        # Optional xHCI diagnostic. A hub answering GET_STATUS does not prove
        # that the host still knows its port count and transaction translators.
        for name in Path('/sys/kernel/debug/usb/xhci').glob('*/devices/*/name'):
            try:
                if name.read_text().strip() == self.path.name:
                    context = name.with_name('slot-context').read_text()
                    LOG.info('%s host context: %s', self.path.name, context.strip())
                    return ' Hub ' in context
            except FileNotFoundError:
                continue
        return None

    def unconfigured_children(self):
        return [p.parent.name for p in self.path.resolve().rglob('bConfigurationValue')
                if p.parent != self.path.resolve() and not p.read_text().strip()]

    def status(self):
        # Hub-class GET_STATUS, USB 2.0 section 11.24.2.6; four-byte response.
        data = ctypes.create_string_buffer(4)
        request = Control(0xA0, 0, 0, 0, 4, 500, ctypes.addressof(data))
        ioctl = (3 << 30) | (ctypes.sizeof(Control) << 16) | (ord('U') << 8)
        result = fcntl.ioctl(self.fd, ioctl, request)
        if result != 4:
            raise OSError(errno.EPROTO, f"short hub status: {result}")
        return data.raw.hex()

    def reset(self):
        # Do not reset a hub carrying storage, even if other devices failed.
        for interface in self.path.resolve().rglob("bInterfaceClass"):
            if interface.read_text().strip() == "08":
                raise ValueError("hub has a storage interface; refusing automatic reset")
        # USBDEVFS_RESET left this xHCI's hub slot without Hub/MTT/port fields.
        # Disconnect/re-enumerate the branch instead: normal hub probing rebuilds
        # both the device and host state. This need not cut physical USB power.
        port = (self.path / 'port').resolve(strict=True) / 'disable'
        if port.read_text().strip() != '0':
            raise ValueError('upstream port already disabled; refusing recovery')
        self.close()
        try:
            port.write_text('1')
            time.sleep(0.2)
        finally:
            port.write_text('0')
        deadline = time.monotonic() + 8
        while True:
            try:
                self.open()
                if (self.path / 'bConfigurationValue').read_text().strip():
                    break
                self.close()
            except FileNotFoundError:
                self.close()
            if time.monotonic() >= deadline:
                raise TimeoutError('hub did not re-enumerate within eight seconds')
            time.sleep(0.1)


def recover(hub, check_only=False, delay=time.sleep, context_check=lambda: None):
    # Only persistent EPIPE matches the observed fault. Timeouts, disconnects,
    # permissions errors, and other failures must not trigger a speculative reset.
    reason = 'persistent control stall'
    for attempt in range(3):
        try:
            status = hub.status()
            if context_check() is False:
                reason = 'missing host hub context'
                LOG.error('host context no longer identifies this device as a hub')
                if attempt < 2:
                    delay(0.2)
                continue
            LOG.info("hub responds: %s; no reset", status)
            return "healthy"
        except OSError as error:
            if error.errno != errno.EPIPE:
                raise
            LOG.warning("hub GET_STATUS stalled (%d/3)", attempt + 1)
            if attempt < 2:
                delay(0.2)
    if check_only:
        LOG.error("%s; check-only mode, no recovery", reason)
        return "stalled"
    LOG.warning("%s; disconnecting and re-enumerating hub once", reason)
    hub.reset()
    # Reset completion is not proof of recovery. Require a working control reply.
    status = hub.status()
    if context_check() is False:
        raise ValueError('hub reappeared but its host context is still incomplete')
    LOG.info("hub recovered: %s", status)
    return "recovered"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/moonmachine-usb-resume.json")
    parser.add_argument("--check", action="store_true", help="read status without resetting")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    config_path = Path(args.config)
    if not config_path.exists():
        return 0
    lock = os.open("/run/moonmachine-usb-resume.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        configs = json.loads(config_path.read_text())["hubs"]
        result = 0
        for config in configs:
            hub = None
            try:
                name = config["path"]
                if not re.fullmatch(r"[0-9]+-[0-9]+(?:\.[0-9]+)*", name):
                    raise ValueError("invalid USB topology path")
                path = Path("/sys/bus/usb/devices") / name
                if not path.exists():
                    LOG.info("%s absent; skipping", name)
                    continue
                LOG.info("checking %s", name)
                hub = Hub(path, config)
                if recover(hub, args.check, context_check=hub.context_valid) == "stalled":
                    result = 1
                failed = hub.unconfigured_children()
                if failed:
                    LOG.error('USB children remain unconfigured: %s; no repeated reset',
                              ', '.join(failed))
                    result = 1
            except (OSError, ValueError, KeyError) as error:
                LOG.error("recovery failed: %s", error)
                result = 1
            finally:
                if hub is not None:
                    hub.close()
        return result
    finally:
        os.close(lock)


if __name__ == "__main__":
    raise SystemExit(main())
