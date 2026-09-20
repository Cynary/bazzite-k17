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
and continuing input traffic verified each time. Other adapter revisions,
multiple controllers and suspend/resume still need testing. See the
[Xbox adapter investigation](../experimental/xone/probe-reset-investigation.md)
for the findings and test results.
