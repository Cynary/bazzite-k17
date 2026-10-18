#!/usr/bin/python3
"""Check configured USB hubs at boot, after resume, and while the system is awake."""
import fcntl
import importlib.util
import json
import logging
import os
from pathlib import Path
import signal
import time

spec = importlib.util.spec_from_file_location("usb_recovery", Path(__file__).with_name("moonmachine-usb-resume.py"))
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
LOG = logging.getLogger("moonmachine-usb-health")
STATE = Path("/run/moonmachine-usb-health/state.json")


def plan(state, faults, now):
    """One attempt per persistent fault; re-arm after three healthy observations."""
    records = state.setdefault("faults", {})
    current = set(faults)
    for name in list(records):
        if name in current:
            records[name]["healthy"] = 0
        else:
            record = records[name]
            if not record['attempted']:
                record['samples'] = 0
            # Enumeration after recovery is asynchronous. Absence immediately
            # after a reset is not evidence that a failed receiver recovered.
            if now - state.get("last_attempt", -1000) >= 30:
                record["healthy"] = record.get("healthy", 0) + 1
                if record["healthy"] >= 3:
                    del records[name]
    for name in current:
        record = records.setdefault(name, {"since": now, "samples": 0, "attempted": False})
        if not record['samples']:
            record['since'] = now
        record["samples"] += 1
    due = [name for name in sorted(current)
           if not records[name]["attempted"] and records[name]["samples"] >= 2
           and now - records[name]["since"] >= 15]
    if due and now - state.get("last_attempt", -1000) >= 60:
        # Record before touching USB, including other faults already present.
        # A failure or service interruption must not result in repeated resets.
        for name in current:
            records[name]["attempted"] = True
        state["last_attempt"] = now
        return due
    return []


def inspect(hub):
    faults = []
    try:
        hub.status()
    except OSError as error:
        if error.errno != recovery.errno.EPIPE:
            raise
        faults.append("hub-control-stall")
    if hub.context_valid() is False:
        faults.append("hub-context-missing")
    for name in hub.unconfigured_children():
        # Children may be several hubs deep; use their sysfs bus entry.
        path = Path('/sys/bus/usb/devices') / name
        if (path / 'authorized').read_text().strip() == '1':
            faults.append('unconfigured:' + name)
    return sorted(faults)


def save(state):
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state))
    tmp.chmod(0o600)
    tmp.replace(STATE)


def terminate(signum, frame):
    # Raise so reset()'s finally clause re-enables a disabled port on shutdown.
    raise SystemExit(128 + signum)


def main():
    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    recovery.LOG.setLevel(logging.WARNING)
    signal.signal(signal.SIGTERM, terminate)
    config = Path('/etc/moonmachine-usb-resume.json')
    if not config.exists():
        return 0
    lock = os.open('/run/moonmachine-usb-resume.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        for item in json.loads(config.read_text())['hubs']:
            name = item['path']
            if not recovery.re.fullmatch(r'[0-9]+-[0-9]+(?:\.[0-9]+)*', name):
                raise ValueError('invalid USB topology path')
            path = Path('/sys/bus/usb/devices') / name
            if not path.exists():
                # No matching device identity: do not touch that port.
                continue
            hub = None
            key = ':'.join(item[k] for k in ('path', 'idVendor', 'idProduct', 'bcdDevice'))
            record = state.setdefault(key, {})
            try:
                hub = recovery.Hub(path, item)
                faults = inspect(hub)
                if record.get('observed') != faults:
                    LOG.info('%s: %s', name, ', '.join(faults) or 'healthy')
                    record['observed'] = faults
                due = plan(record, faults, time.monotonic())
                save(state)
                if due:
                    LOG.warning('%s: recovering persistent fault: %s', name, ', '.join(due))
                    hub.reset()
                    hub.status()
                    if hub.context_valid() is False:
                        raise ValueError('host hub context still missing after recovery')
                    LOG.info('%s: hub re-enumerated; subsequent checks will verify its receivers', name)
            except (OSError, ValueError, KeyError) as error:
                message = str(error)
                if record.get('error') != message:
                    LOG.error('%s: %s', name, message)
                    record['error'] = message
                save(state)
            else:
                if record.pop('error', None) is not None:
                    save(state)
            finally:
                if hub is not None:
                    hub.close()
        return 0
    finally:
        os.close(lock)


if __name__ == '__main__':
    raise SystemExit(main())
