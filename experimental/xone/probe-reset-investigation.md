# Xbox adapter startup reset regression — 2026-09-19

Status: the combined fix passed five consecutive settled warm restarts
with the Xbox Wireless Adapter `045e:02e6` on the K17.

## Controlled version comparison

Hardware: GMKtec K17, Xbox Wireless Adapter `045e:02e6`, wired network,
stock adapter firmware, Bazzite kernel `7.2.4-ogc3.1.fc44.x86_64`.
Only the dongle transport module was replaced; the GIP module remains stock.

| Driver source | Settled warm-restart result |
|---|---|
| v0.5.5 | Five passed; user confirmed Steam navigation afterward |
| `725a46c` | Five passed |
| `51720a2` | Control restart passed |
| `7ee0ce1`, immediate successor | First two passed, third failed |
| `8398e16` | First restart failed, including receive overflows |
| `112e883` | First two passed, third failed with 16 phantom clients |

The only functional difference between `51720a2` and `7ee0ce1` is removing
`usb_reset_device()` from probe. On the failed third boot, no real controller
input device registered. The capture includes incoming packets containing the
controller's address, but no continuing controller data stream. Thus that
failure cannot be explained just by the controller being switched off.

Other failed runs produced malformed association-shaped frames addressed
elsewhere, exhausting the client table. Destination/header validation remains
a separate hardening issue; it did not fix the earlier low-level failure.

The results implicate removal of the startup reset on this setup. They do not
establish the internal firmware/DMA mechanism. Some failures survive a module
reload and USB re-enumeration. Full shutdown followed by Wake-on-LAN restored
operation without unplugging; this does not prove that USB VBUS was removed.

## Candidate

The current pinned source plus the separately demonstrated association-retry
fix is built with a probe reset restored only for product `02e6`. Reset runs
before allocating the workqueue, and a reset error aborts probe safely. Other
adapter product IDs keep the existing initialization sequence.

No controller power-off on restart, added delay, firmware replacement, or USB
power-management override is part of the candidate. Earlier reset-only tests
could still encounter the separate lost-association-reply defect; this build
combines both corrections.

Candidate dongle srcversion: `79D993360F2FB22DB547715`.
Stock GIP srcversion: `202AABE021C636443A21D63`.

## Validation limits

The controller connected after shutdown/WOL, confirmed by the user and by its
actual Linux input device. All five consecutive warm restarts of this exact candidate passed: the real
controller input registered each time, exactly one client slot was occupied,
no unexpected USB completion errors or Xbox-driver error messages were found,
and controller traffic continued through every capture. Each run is observed until at least 105 seconds uptime, with a
bounded 90-second USB capture. Registration, client count, transport errors,
and continued controller traffic are checked remotely. Per the user's request,
Steam navigation is not manually checked after every restart.

Suspend/resume, multiple controllers, other adapter revisions, and long-term
reliability are not validated by this test. No upstream submission has been
made. Raw captures stay private because they contain unrelated radio traffic.

The investigation, code change, and automated checks were performed with Codex;
the user performed the physical controller checks reported above.

| Restart | Observation uptime | USB completions | Unexpected USB errors |
|---|---:|---:|---:|
| 1 | 107 s | 956 | 0 |
| 2 | 110 s | 10541 | 0 |
| 3 | 109 s | 10711 | 0 |
| 4 | 108 s | 996 | 0 |
| 5 | 109 s | 917 | 0 |

The patch is included in the source recipe. The live machine currently loads
the tested module through the temporary kernel-version-guarded loader. An
OCI image containing this change has not yet been rebuilt or deployed.
