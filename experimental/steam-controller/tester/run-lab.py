#!/usr/bin/env python3
"""Run the experimental native HID relay over SSH; Ctrl+C removes the virtual device."""
import argparse
import selectors
import signal
import re
import shlex
import subprocess
import time
from pathlib import Path
from imu_clock import ImuClock

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--client', required=True, help='Linux SSH alias')
parser.add_argument('--host', required=True, help='Windows SSH alias')
parser.add_argument('--broker', required=True, help='Absolute Windows broker.exe path (forward slashes)')
parser.add_argument('--device', default='/dev/hidraw5', help='Puck interface 2; verify its sysfs identity first')
parser.add_argument('--minutes', type=int, default=30)
args = parser.parse_args()
if not 1 <= args.minutes <= 120:
    parser.error('--minutes must be between 1 and 120')
# Gateway source and all control traffic use authenticated SSH. No listening port.
gateway = Path(__file__).resolve().parent.parent / 'windows-native' / 'gateway.py'
remote = '/tmp/moonmachine-controller-lab-gateway.py'
subprocess.run(['scp', '-q', str(gateway), args.client + ':' + remote], check=True)
command = shlex.join(['sudo', '-n', 'systemd-inhibit', '--what=sleep', '--mode=block',
                     '--why=Steam Controller Lab', 'timeout', str(args.minutes * 60 + 10),
                     'python3', remote, args.device])
linux = subprocess.Popen(['ssh', '-o', 'ConnectTimeout=10', args.client, command],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
windows = None
def stop(signum, frame):
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM, stop)
try:
    if linux.stdout.readline() != b'READY\n':
        raise RuntimeError('Physical endpoint unavailable; check device and passwordless sudo')
    if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+', args.broker):
        raise ValueError('Invalid broker path')
    windows = subprocess.Popen(['ssh', '-o', 'ConnectTimeout=10', args.host, args.broker],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(linux.stdout, selectors.EVENT_READ, windows)
    selector.register(windows.stdout, selectors.EVENT_READ, linux)
    buffers = {linux.stdout: b'', windows.stdout: b''}
    end = time.monotonic() + args.minutes * 60
    count = 0
    imu_clock = ImuClock()
    print('Native relay running. Open Steam Controller Lab in Moonlight. Ctrl+C ends it.', flush=True)
    while time.monotonic() < end:
        for key, _ in selector.select(max(0, end - time.monotonic())):
            data = key.fileobj.read(65536)
            if not data:
                raise RuntimeError('Relay endpoint disconnected')
            buffers[key.fileobj] += data
            if len(buffers[key.fileobj]) > 131072:
                raise RuntimeError('Oversized relay message')
            while b'\n' in buffers[key.fileobj]:
                line, buffers[key.fileobj] = buffers[key.fileobj].split(b'\n', 1)
                count += line.startswith(b'I ')
                if key.fileobj is linux.stdout and line.startswith(b'I '):
                    report = imu_clock.normalize(bytes.fromhex(line[2:].decode('ascii')))
                    line = b'I ' + report.hex().encode('ascii')
                key.data.stdin.write(line + b'\n')
    print('Time limit reached. Reports forwarded:', count)
except KeyboardInterrupt:
    print('Stopping relay.')
finally:
    for process in (windows, linux):
        if process is None:
            continue
        try:
            process.stdin.write(b'X\n')
            process.stdin.close()
            process.wait(timeout=10)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()
