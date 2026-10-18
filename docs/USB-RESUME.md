# Controllers disappear after waking

A USB hub can fail to resume even while its receivers still have power. The
controllers may show a connected light, but Linux cannot communicate with them.
With no controller input, the Steam library can appear frozen.

We observed this with a Genesys `05e3:0610` hub, revision `9406`. After resume,
its control requests returned `EPIPE`, several ports failed to reset, and a
downstream hub containing a Vader receiver and Steam Controller puck disappeared.
Resetting the Genesys hub restored both controllers without restarting Steam or
Gamescope. This identifies the failed part of the USB path; it does not establish
whether the original trigger was hub firmware, power, or the host USB driver.

## Automatic health checks

An opt-in monitor checks the configured hub 20 seconds after boot, every 15
seconds while the machine is awake, and after resume. It does not prevent sleep
or wake the computer for a check.

It detects stalled hub control requests, missing xHCI hub metadata, and receivers
that are present and authorized but failed USB configuration. A fault must still
be present on a later check, at least 15 seconds after it was first seen, before
recovery starts. Normal startup and reconnects get time to finish.

Recovery disconnects and re-enumerates that USB branch. This briefly interrupts
all devices on it, including controllers and headsets. The monitor checks the
result on subsequent passes. It attempts each persistent fault once, waits at
least a minute between recoveries, and re-arms after three healthy checks. An
unrecoverable receiver therefore cannot cause an endless reset loop; a new
failure on another receiver can still trigger recovery.

This uses the upstream port's `disable` attribute, then re-enables it. It rebuilds
the host's device records; it does not necessarily cut electrical power. We
stopped using `USBDEVFS_RESET` after observing that it left the hub's xHCI record
without its hub flag, port count and transaction-translator information. A
working hub-status reply alone did not catch that problem.

Recovery requires the configured hub identity to match and refuses to disconnect
a hub carrying USB storage. A missing hub or unrelated USB errors are logged or
skipped rather than resetting an unidentified device. Checks remain inactive
until a configuration file exists.

Find the affected hub's path with `lsusb -t` and its identity in
`/sys/bus/usb/devices/<path>/`. Create `/etc/moonmachine-usb-resume.json` as root,
using the actual values for your hub:

```json
{
  "hubs": [
    {
      "path": "3-5",
      "idVendor": "05e3",
      "idProduct": "0610",
      "bcdDevice": "9406"
    }
  ]
}
```

The path above is an example. All identity fields must match before recovery is
allowed. Moving a hub to another port may require updating the path.

Check the configuration without resetting anything:

```sh
sudo python3 /usr/libexec/moonmachine-usb-resume.py --check
```

Check the monitor with:

```sh
systemctl status moonmachine-usb-health.timer
journalctl -b -u moonmachine-usb-health.service
```

The timer is enabled in the image. On a manual installation, enable it with
`sudo systemctl enable --now moonmachine-usb-health.timer`. Remove the configuration
file to disable automatic recovery. Recovery briefly disconnects everything
beneath that hub, including audio receivers. This is recovery for a demonstrated
failure, not a guarantee that the hub will resume correctly. Automated tests
cover fault detection policy, recovery limits and re-arming. Repeated physical
suspend/resume validation is pending.

In a later failure, the Vader receiver remained powered but failed USB
configuration with `-ENOSPC`. The xHCI event ring identified a **Secondary
Bandwidth Error**, which concerns scheduling USB transfers behind a hub.
Recovering the branch restored the Vader and Steam input without restarting
Steam. The Steam Controller puck still failed configuration, including after
re-enumerating the branch with correct hub metadata. That remaining failure is
under investigation; these recovery checks do not resolve every bandwidth error.

Linux documents the distinction between normal resume and reset-resume in its
[USB power-management documentation](https://cdn.kernel.org/doc/html/latest/driver-api/usb/power-management.html).
