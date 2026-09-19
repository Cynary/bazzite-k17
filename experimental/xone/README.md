# Xbox adapter diagnostic candidate, 2026-09-18

**Restart fault remains unresolved. The receive-parser candidate FAILED the
controller-on reboot test. Do not promote it as a controller reliability fix.**

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

## Receive parser investigation (next candidate)

Code comparison with medusalix/xow identified missing packet-type validation.
xow checks the WLAN-port header is80211 bit (bit 19) before parsing RXWI and
802.11, and checks the destination address before dispatch. xone did neither
(the first failed experiment checked only association destinations). xone also
checked command sequence bits before distinguishing the port, even though
WLAN packets use those bits for other fields. Captured failing header
22 20 04 00 has port 0 and is80211 clear.

receive-header-validation-test.patch adds the native-802.11 check, restricts
command-response handling to CPU_RX, and validates the destination before all
frame dispatch. Firmware initialization is pristine upstream.
Module srcversion: 70B2B8BF8270C75A1BE533E.

The candidate booted with controller off and stayed at zero clients with no
packet errors for more than a minute, including expiration of pairing mode.
Delayed controller connection is awaiting user validation. Not release-qualified.

A temporary kernel-version-guarded modprobe override loads the root-owned
module /var/lib/k17-xone-test/xone_dongle.ko, labelled modules_object_t.
The loader is /usr/local/sbin/k17-xone-test-load. A temporary service
k17-xone-test.service retries after local-fs because /var is not available at
the initial udev probe. This is test scaffolding, not final image packaging.
Rollback: disable/remove k17-xone-test.service, remove
/etc/modprobe.d/99-k17-xone-test.conf, unload/reload xone_dongle or reboot;
remove the loader, module directory and its semanage fcontext rule afterward.
Do not disable SELinux.

User confirmed delayed connection after that warm reboot without unplugging;
one real controller and one client verified. A single GIP "already initialized
(in)" warning was logged, but input device registration succeeded. Do not claim
a completely warning-free log or validated suspend/resume. The patch is now
being packaged under xone-patches; image deployment validation remains pending.

## A/B retest: causal claim remains unproven

The user requested reproducing on the old driver and switching live into the
patched driver before reboot. Packaged srcversion 228407C6EB982C5BA099BF0
was booted with the same delayed loader and reconnected after idle. Then the
loader override was disabled and two normal early-loading stock-driver boots
with controller off stayed at zero clients and no packet errors for >60 s.
Thus the failure could not be reproduced in this round. Delayed load timing
was a potential confound, but normal loading also did not reproduce.

The parser differences are supported by code and a captured non-802.11 header;
the claim that this fixes the intermittent restart failure is NOT established.
Recovery by live swap from the failed state remains untested. Do not label
this candidate a confirmed restart fix, or infer a firmware fault. Logs in
~/k17-option1/xone-restart/ab. Restore patched candidate after comparison;
keep image on candidate track pending stronger validation.

## Controller-on reboot with parser candidate: FAILED

The controller remained flashing; dongle LED solid; host had zero clients.
USB monitoring revealed a continuous command-endpoint-5 stream completing
with -EOVERFLOW (-75), 1536 bytes against a 1620-byte buffer. xone silently
resubmits failed URBs, so clean dmesg was insufficient evidence of health.
Rounding input buffers to the endpoint packet size removed overflow but
left a continuous invalid-data stream (2048-byte successful completions),
with no controller connection. This did not recover by live module replacement.
Firmware reset/upload experiments and reinitializing USB DMA configuration
did not recover it either. Original DMA config already read 0xc00000.
Do not conclude firmware fault solely from these observations.

Next single-variable diagnostic restores upstream parsing/firmware code and
removes the SYSTEM_RESTART early return in xone_dongle_shutdown, allowing
normal controller power-off on reboot. Module srcversion
042B49711030E5168B50CEB. User power cycle/reconnection and reboot test pending.
Temporary boot loader now selects this shutdown-only candidate.

## Shutdown-only candidate reboot tests

After physical recovery, shutdown-only srcversion 042B49711030E5168B50CEB
was booted with the controller connected. User confirmed the restart powered
off the controller and that pressing Xbox reconnected it without unplugging.
A second connected-controller restart again had no packet errors, phantom
clients or continuous endpoint-5 USB stream, and a real controller input
registered after the user powered it back on. Steam input confirmation pending.

Image packaging now selects ONLY the restart-cleanup patch. The failed parser
candidate remains archived under experimental, not included in the next image.
No firmware replacement, DMA-register experiments, packet-filter changes or
receive-buffer changes are included. This is a promising restart workaround;
the precise cause of the adapter's invalid USB stream and suspend/resume
behavior remain unproven. Tests should not be described as comprehensive.
