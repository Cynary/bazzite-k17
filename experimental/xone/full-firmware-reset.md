# Original Xbox adapter: firmware reset candidate

The original Microsoft Xbox Wireless Adapter (`045e:02e6`) can stop accepting controllers after a restart. We reproduced this on the K17 with both the older driver and the suspend candidate. Five successful restarts were not enough to establish reliability.

A captured startup produced a firmware assertion in `wifi/RAM/api/txm_dispatch.c`, line 908. Another failed boot produced malformed receive packets, then channel-command timeouts. A solid controller light was not sufficient evidence of a working connection; validation checks the Linux input device and controller packets.

## What the candidate changes

The existing warm path reloads the interrupt vector and waits for a ready bit that was already set before the reset. That check cannot demonstrate a fresh firmware startup.

For `02e6`, this candidate stops beacon transmission and the MAC, requests firmware-upload mode, checks the complete upload-state value, and reloads the firmware. Each retry establishes upload mode again. Other adapter revisions retain their existing initialization path. The existing suspend/resume and teardown patch is preserved.

It also selects the shared 2017 firmware (`xone_dongle_02fe.bin`) for this adapter, as the original xone driver did. Newer firmware by itself did not solve the failure. The firmware must be included in the initramfs as well as the installed filesystem.

Apply [the candidate patch](full-firmware-reset.patch) after `xone-patches/0001` through `0004`. It compiled as module source version `3DBD258ECD8E759A6E35105` with the current kernel build. This patch is not yet part of a published image.

## Validation so far

- A warm reboot using full reload recovered a captured failure without unplugging, pairing or shutting down the PC.
- Five further diagnostic-driver restarts all registered one controller and a real input device. Four were clean; one logged a transient busy result for a GIP status packet during driver setup.
- The clean candidate reconnected after boot. It logged early GIP status/serial-response errors and retried the connection, so this was not an error-free startup.
- Timer wake and controller wake both restored a real input device with no new xone errors. Controller wake occurred about 15 seconds into sleep, before the 90-second fallback alarm.

The full-reload sequence is still a candidate. Earlier upload experiments failed, including a transition back to the older firmware. The exact firmware-side fault is unresolved. Extended tests of the clean build and validation of a rebuilt image remain necessary before release.

An unrelated, confirmed bug is covered separately by `0004`: requests addressed to other access points must not allocate controller slots. A replay of the captured association requests preserved all three controller requests and rejected the unrelated request.
