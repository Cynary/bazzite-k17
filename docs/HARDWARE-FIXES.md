# Wi-Fi and Xbox controllers

The included kernel fixes a bug when the K17's **MediaTek MT7922 Wi-Fi** driver
reads newer firmware. It checks the firmware records safely and skips entries
it doesn't recognise. Initialization and network scanning passed after the fix;
connecting to Wi-Fi and measuring throughput haven't been tested yet.
See the [Wi-Fi notes](../PLATFORM-FIRMWARE.md#mt7922-wi-fi) for details.

The **xone driver**, which handles Xbox Wireless Adapters, includes two fixes:
it answers repeated controller connection requests and restores a startup reset
for adapter model `045e:02e6`. These address cases where the controller keeps
flashing or appears connected but never becomes usable after a restart. The
combined fix passed five consecutive restarts with a controller input device
and continuing input traffic verified each time. Longer testing subsequently
reproduced intermittent failures on both this driver and the suspend candidate.
Restart reliability is still under investigation; the five successful runs did
not establish a complete fix. Other adapter revisions and multiple controllers
also need testing. See the
[Xbox adapter investigation](../experimental/xone/probe-reset-investigation.md)
for the findings and test results.

The later radio-before-receive suspend candidate is **not included in
`moonmachine-20260922.2`**. Its five short sleep tests used a local module. See
the [release audit](RELEASE-AUDIT-20260922.md#omission-xbox-suspend-candidate) for
the packaging gap and required follow-up.

The next image build also carries
`0003-restore-radio-before-receive-and-bound-teardown.patch`: restore the radio
before accepting receive traffic after sleep, and stop processing queued requests
during teardown. This preserves the previously tested candidate without its
informational diagnostic messages. Packaging and new-image reboot/resume
validation must finish before this is described as released.

A further source patch,
`0004-reject-association-requests-for-other-access-points.patch`, ignores wireless
connection requests addressed to another access point. A captured request of
that kind had consumed a controller slot. The patch keeps requests addressed
to the adapter and has been tested in the diagnostic driver; it is not yet in a
published image. It addresses false controller entries, not the separate radio
initialization failures.

The [full firmware reset investigation](../experimental/xone/full-firmware-reset.md)
describes the latest candidate and its validation limits.
