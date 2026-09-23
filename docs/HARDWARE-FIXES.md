# Wi-Fi and Xbox controllers

The included kernel fixes a bug when the K17's **MediaTek MT7922 Wi-Fi** driver
reads newer firmware. It checks the firmware records safely and skips entries
it doesn't recognise. Initialization and network scanning passed after the fix;
connecting to Wi-Fi and measuring throughput haven't been tested yet.
See the [Wi-Fi notes](../PLATFORM-FIRMWARE.md#mt7922-wi-fi) for details.

The **xone driver** handles Xbox Wireless Adapters. The image’s patch series:

- Answers repeated controller connection requests instead of silently ignoring them.
- Restores the startup USB reset for the original adapter (`045e:02e6`).
- Restores the radio before receiving packets after suspend, and stops queued requests during teardown.
- Ignores wireless connection requests addressed to other access points, which could otherwise consume controller slots.
- Reloads the original adapter’s firmware from a verified upload state and uses the shared 2017 firmware. The previous warm-reset check could accept a ready bit left over from the previous run.

The combined driver passed **ten consecutive early-loading restarts and ten
suspend/resume cycles** on the K17. A real controller input device returned every
time. One restart logged a transient GIP status warning during driver setup; the
suspend tests had no xone errors. No unplugging, pairing or recovery was needed.
The sleep tests mixed controller-triggered wakes and reconnection after timer
wakes, with short sleep intervals. Other adapters, multiple controllers and
long standby periods still need testing.

See the [firmware reset investigation](../experimental/xone/full-firmware-reset.md)
for the captured failures, changes and validation. Earlier five-restart tests
had missed an intermittent failure; the longer tests above cover the newer
combined driver. The signed `moonmachine-20260923.1` release includes these changes. See [packaged-image validation](XBOX-RELEASE-20260923.md) for its release status.
