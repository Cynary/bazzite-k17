# Original Xbox adapter: firmware reset candidate

The original Microsoft Xbox Wireless Adapter (`045e:02e6`) can stop accepting controllers after a restart. We reproduced this on the K17 with both the older driver and the suspend candidate. Five successful restarts were not enough to establish reliability.

A captured startup produced a firmware assertion in `wifi/RAM/api/txm_dispatch.c`, line 908. Another failed boot produced malformed receive packets, then channel-command timeouts. A solid controller light was not sufficient evidence of a working connection; validation checks the Linux input device and controller packets.

## What the candidate changes

The existing warm path reloads the interrupt vector and waits for a ready bit that was already set before the reset. That check cannot demonstrate a fresh firmware startup.

For `02e6`, this candidate stops beacon transmission and the MAC, requests firmware-upload mode, checks the complete upload-state value, and reloads the firmware. Each retry establishes upload mode again. Other adapter revisions retain their existing initialization path. The existing suspend/resume and teardown patch is preserved.

It also selects the shared 2017 firmware (`xone_dongle_02fe.bin`) for this adapter, as the original xone driver did. Newer firmware by itself did not solve the failure. The firmware must be included in the initramfs as well as the installed filesystem.

The reset is included in [the complete xonedo fork](https://github.com/Cynary/xonedo/tree/b516bdd96f7d22f4e3de211cf1ca7177d0064357). Its module source version is `3DBD258ECD8E759A6E35105`. See [release validation](../../docs/XBOX-RELEASE-20260923.md).

## Validation so far

- A warm reboot using full reload recovered a captured failure without unplugging, pairing or shutting down the PC.
- Five further diagnostic-driver restarts all registered one controller and a real input device. Four were clean; one logged a transient busy result for a GIP status packet during driver setup.
- The clean candidate reconnected after boot. It logged early GIP status/serial-response errors and retried the connection, so this was not an error-free startup.
- Ten consecutive warm restarts of the clean candidate, loaded early from the initramfs, all restored exactly one controller and a Linux input device. Each capture contained controller traffic. Nine runs had no xone errors; one logged a single GIP status packet as busy during driver initialization, then registered the input device about 5 ms later. No firmware assertions, channel-command timeouts, firmware-upload errors or capture drops occurred. The test used normal USB power management and needed no unplugging, pairing or shutdown recovery.
- Timer wake and controller wake both restored a real input device with no new xone errors. Controller wake occurred about 15 seconds into sleep, before the 90-second fallback alarm.
- A subsequent batch of ten suspend/resume cycles also passed on the early-loaded clean candidate. The user pressed Xbox during some sleeps and after some timed wakes, so this was a mixed wake/reconnection test. All ten cycles resumed without rebooting, created a fresh controller input device, and retained exactly one client with no new xone errors. Suspend-entry to resume-exit intervals ranged from 6.5 to 31.8 seconds; these were short-cycle tests, not overnight standby tests.

The full-reload sequence is still a candidate. Earlier upload experiments failed, including a transition back to the older firmware. The exact firmware-side fault is unresolved. The ten-restart test passed, but the packaged image also passed boot and reconnection after a timer wake. These results cover this adapter on this K17; they do not establish reliability across other hardware.

An unrelated, confirmed bug is covered separately by `0004`: requests addressed to other access points must not allocate controller slots. A replay of the captured association requests preserved all three controller requests and rejected the unrelated request.
