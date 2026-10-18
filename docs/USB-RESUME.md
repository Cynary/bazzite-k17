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
resume. If three consecutive hub-status requests stall, it disconnects and
re-enumerates that USB branch once. On xHCI hosts with debugfs available, it also
checks that the host still identifies the device as a hub. Three checks showing
missing hub metadata trigger the same recovery.

This uses the upstream port's `disable` attribute, then re-enables it. It rebuilds
the host's device records; it does not necessarily cut electrical power. We
stopped using `USBDEVFS_RESET` after observing that it left the hub's xHCI record
without its hub flag, port count and transaction-translator information. A
working hub-status reply alone did not catch that problem.

The hook verifies the response after recovery and reports any children still
missing a USB configuration. It does not repeatedly reset devices that report
bandwidth errors. It refuses to recover a hub with a USB storage interface
beneath it. Other USB errors are logged without a reset.

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
configuration file to disable recovery. Recovery briefly disconnects everything
beneath that hub, including audio receivers. This is recovery for a demonstrated
failure, not a guarantee that the hub will resume correctly. Automated tests
cover the reset policy; repeated physical suspend/resume validation is pending.

In a later failure, the Vader receiver remained powered but failed USB
configuration with `-ENOSPC`. The xHCI event ring identified a **Secondary
Bandwidth Error**, which concerns scheduling USB transfers behind a hub.
Recovering the branch restored the Vader and Steam input without restarting
Steam. The Steam Controller puck still failed configuration, including after
re-enumerating the branch with correct hub metadata. That remaining failure is
under investigation; these recovery checks do not resolve every bandwidth error.

Linux documents the distinction between normal resume and reset-resume in its
[USB power-management documentation](https://cdn.kernel.org/doc/html/latest/driver-api/usb/power-management.html).
