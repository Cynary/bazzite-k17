# Xbox adapter diagnostic candidate, 2026-09-18

Not included in the image or qualified for persistent deployment.

Base: OpenGamingCollective/xonedo 982cbcb019ae4d2bee5ae69385223409ee555c88.
An unmodified rebuild matches installed xone_dongle srcversion
228407C6EB982C5BA099BF0 on 7.2.4-ogc3.1.fc44.x86_64.
The 045e:02e6 adapter firmware matches upstream SHA-256
080ce4091e53a4ef3e5fe29939f51fd91f46d6a88be6d67eb6e99a5723b3a223.

Observed: spurious association requests with invalid destination/BSSID values
consume all 16 client slots without a registered controller input device.
USB autosuspend is disabled. Driver rebind, USB reset and deauthorize/authorize
do not resolve the issue. Diagnostic logging shows payload-like bytes being
interpreted as MAC addresses; the underlying receive/firmware cause is not yet
proven.

The candidate rejects association requests until the adapter has a valid MAC,
and requires their destination to match that MAC. This stopped phantom client
accumulation in the live test. Malformed-packet -EINVAL reports still occur.
Real controller pairing, reconnect, reboot and resume remain unvalidated.
Do not claim the overall controller failure is fixed.

The candidate module was built against the stock kernel headers in the existing
Fedora builder, then loaded from ~/k17-option1/xonedo-test/xone_dongle.ko.
The installed immutable module remains unchanged. Reboot restores stock xone;
manual rollback is modprobe -r xone_dongle followed by modprobe xone_dongle.
No upstream submission is authorized.

## Restart investigation

Physical unplug/replug restored controller input. A subsequent reload of the
packaged driver and two warm reboots with the controller on also reconnected
successfully. With the controller explicitly powered off (sysfs slot 0) before
the next reboot, idle initialization again produced malformed packets and two
phantom clients. This implicates idle/startup behavior, but does not yet prove
which driver change causes it. Logs are in ~/k17-option1/xone-restart on K17.

The association-address filter did not restore connection. Removing the recent
WoW-routing initialization also did not eliminate errors. Neither experiment
is currently loaded. An older v0.5.5 module could not recover the failed state.
Forcing a full firmware upload on the warm path timed out; that change was
reverted.

Current temporary candidate changes only pairing_scan: skip channel hopping
for USB product 02e6, retaining its selected initial channel. This is a
diagnostic comparison, not a validated fix. A physical replug with controller
off, delayed reconnection, and reboot remain required. No persistent module
override has been installed.

The no-scan candidate passed a cold replug, idle for >60 seconds, and delayed
controller connection. It FAILED a warm reboot with the controller off: ten
phantom clients and packet errors returned. It must not be shipped as a fix.
Temporary modprobe override was removed. Firmware re-upload experiments also
failed, including the xow reset-command variant; the last variant produced USB
control errors and requires physical disconnect to finish unloading. No
experimental override remains configured for boot. Root cause unresolved.

The reboot verified Btrfs compress=zstd:1 is now active.

Final recovery: physical disconnect allowed the experimental module to unload.
The packaged driver (srcversion 228407C6EB982C5BA099BF0) was restored.
User confirmed connection; one real controller input device and one client
were verified, with no xone errors since the final replug. Temporary modprobe
configuration, loader script, module copy and SELinux file-context rule were
removed. Restart reliability remains unresolved.
