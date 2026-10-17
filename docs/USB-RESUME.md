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

## Optional recovery after resume

Moonmachine includes an opt-in recovery hook. It checks the configured hub after
resume and resets it once only if three consecutive hub-status requests stall.
Healthy hubs and other errors do not trigger resets. The hook verifies the
response after a reset and logs the outcome. It refuses to reset a hub with a
USB storage interface beneath it.

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

Look for `moonmachine-usb-resume` in `journalctl -b` after waking. Remove the
configuration file to disable recovery. A reset briefly disconnects everything
beneath that hub, including audio receivers. This is recovery for a demonstrated
failure, not a guarantee that the hub will resume correctly. Automated tests
cover the reset policy; repeated physical suspend/resume validation is pending.

Linux documents the distinction between normal resume and reset-resume in its
[USB power-management documentation](https://cdn.kernel.org/doc/html/latest/driver-api/usb/power-management.html).
