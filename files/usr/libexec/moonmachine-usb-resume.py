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
        os.close(self.fd)

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
        fcntl.ioctl(self.fd, 0x5514, 0)  # USBDEVFS_RESET


def recover(hub, check_only=False, delay=time.sleep):
    # Only persistent EPIPE matches the observed fault. Timeouts, disconnects,
    # permissions errors, and other failures must not trigger a speculative reset.
    for attempt in range(3):
        try:
            status = hub.status()
            LOG.info("hub responds: %s; no reset", status)
            return "healthy"
        except OSError as error:
            if error.errno != errno.EPIPE:
                raise
            LOG.warning("hub GET_STATUS stalled (%d/3)", attempt + 1)
            if attempt < 2:
                delay(0.2)
    if check_only:
        LOG.error("persistent control stall; check-only mode, no reset")
        return "stalled"
    LOG.warning("persistent control stall; resetting hub once")
    hub.reset()
    # Reset completion is not proof of recovery. Require a working control reply.
    status = hub.status()
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
                if recover(hub, args.check) == "stalled":
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
