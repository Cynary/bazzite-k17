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
