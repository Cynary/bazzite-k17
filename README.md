# Moonmachine

A little PC under the TV, a controller on the couch, and your Steam library ready
when you sit down. Moonmachine is a version of [Bazzite](https://bazzite.gg/)
built for that setup on the **GMKtec K17**.

Play games on the mini PC itself, or stream them from a more powerful gaming PC
with Moonlight. MoonDeck puts a streaming button in Steam so you can launch games
without leaving the controller-friendly interface.

## What you get

- Steam Gaming Mode at startup.
- Experimental HDMI support for **4K at 120 Hz, HDR, 10-bit colour and variable
  refresh rate (VRR)** on the K17. VRR lets the TV follow the game's frame rate
  instead of refreshing at a fixed speed.
- Moonlight with VRR support, Decky (Steam's plugin menu), and upstream MoonDeck.
- A custom kernel with BORE, which schedules CPU work with responsiveness in mind,
  and ThinLTO, a compiler optimisation. These aren't a promise of higher game FPS.
- Graphical boot and updates through Bazzite's normal system-update controls.
- Fixes for the K17's MediaTek Wi-Fi driver and Xbox Wireless Adapter
  reconnection after restarting.

**[Install Moonmachine →](RELEASES.md)**

## Wi-Fi and Xbox controllers

The included kernel fixes a bug when the K17's **MediaTek MT7922 Wi-Fi** driver
reads newer firmware. It checks the firmware records safely and skips entries
it doesn't recognise. Initialization and network scanning passed after the fix;
connecting to Wi-Fi and measuring throughput haven't been tested yet.
See the [Wi-Fi notes](PLATFORM-FIRMWARE.md#mt7922-wi-fi) for details.

The **xone driver**, which handles Xbox Wireless Adapters, includes two fixes:
it answers repeated controller connection requests and restores a startup reset
for adapter model `045e:02e6`. These address cases where the controller keeps
flashing or appears connected but never becomes usable after a restart. The
combined fix passed five consecutive restarts with a controller input device
and continuing input traffic verified each time. Other adapter revisions,
multiple controllers and suspend/resume still need testing. See the
[Xbox adapter investigation](experimental/xone/probe-reset-investigation.md)
for the findings and test results.

## Before you start

This is an experimental community project, not an official Bazzite release.
The supported test machine is the K17 with Intel Arc 130V graphics. Other PCs
may work, but haven't been qualified. Secure Boot must be disabled.

For 4K120, use the K17's HDMI 2.1 output, a suitable HDMI cable, and a TV that
supports the mode. The two HDMI ports do not have the same capabilities. Any
receiver between the PC and TV must also support the signal.

The main missing console convenience is **CEC**—the HDMI feature that turns on a
TV and selects its input. The K17 does not expose usable CEC control in this setup.
You can add similar behaviour over your network, or investigate a USB CEC adapter.
See [TV and receiver control](docs/TV-CONTROL.md) for an example you can adapt.

## Start streaming

[Set up your gaming PC and pair MoonDeck](docs/STREAMING.md). Once paired, pick a
Steam game and use its MoonDeck button to play it on the TV.

For the underlying hardware work, see the [kernel notes](kernel-notes/README.md).
Build and publishing instructions live in [MAINTAINING.md](MAINTAINING.md).

Built on the work of Bazzite, the Linux and Intel graphics communities, BORE,
Moonlight, Nonary's VRR work, Decky and MoonDeck. Project changes were developed
with Codex; source and test details are included in this repository.
