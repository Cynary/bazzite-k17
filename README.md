# Moonmachine

Moonmachine is a modification of [Bazzite](https://bazzite.gg/) for a Steam
Machine-like experience, with a focus on streaming without compromising display
quality: **4K120, HDR, 10-bit colour, 4:4:4 and VRR**. It's validated specifically
on the **GMKtec K17**. Other Intel machines with a native HDMI 2.1 FRL output may
work too; compatibility depends on the GPU and how the port is wired.

Moonlight handles streaming, and MoonDeck lets you launch games on your gaming PC
straight from Steam's Gaming Mode. You can also install and play games locally.

## What you get

- Steam Gaming Mode at startup.
- Experimental HDMI support for **4K at 120 Hz, HDR, 10-bit colour and variable
  refresh rate (VRR)** on the K17. VRR lets the TV follow the game's frame rate
  instead of refreshing at a fixed speed.
- Moonlight with VRR support, Decky (Steam's plugin menu), and MoonDeck, with
  [streaming fixes carried as patches](apps/README.md).
- Optimized Moonlight + Gamescope for extremely low latency from receiving a frame
  to presenting it on the TV.
  [How we reached 6.08 ms client latency, with graphs](docs/LATENCY.md).
- CPU performance preference and higher K17 GPU clock floors selected by default,
  [measured to reduce both average streaming latency and occasional slow frames](#performance-defaults).
- A custom kernel with BORE, which schedules CPU work with responsiveness in mind,
  and ThinLTO, which lets the compiler optimise across source files.
- [HDMI recovery and Steam sleep handling](docs/DISPLAY-RECOVERY.md).
- Graphical boot and updates through Bazzite's normal system-update controls.
- [MediaTek Wi-Fi and Xbox Wireless Adapter fixes](docs/HARDWARE-FIXES.md)
  for firmware loading and controller reconnection after restarting.

**[Install Moonmachine →](RELEASES.md)**

## Streaming latency

On the K17, the current release averaged **6.08 ms from complete frame receipt
to the display driver’s timestamp**, at 4K HDR, 4:4:4 and about 116 FPS. The
99th percentile was **7.09 ms** across 8,453 measured frames. Host processing,
network transit and TV processing are outside that measurement.

We traced and fixed queueing, presentation feedback, extra rendering passes and
late GPU-surface exports. Read [the investigation](docs/LATENCY.md) for the
breakdown, comparison graphs, test settings and downloadable data. The
[release audit](docs/RELEASE-AUDIT-20260922.md) records the streaming changes;
[the Xbox release notes](docs/XBOX-RELEASE-20260923.md) cover the later packaged
restart and suspend fixes.

## Performance defaults

Moonmachine selects a streaming performance profile automatically. On the K17,
it asks the CPU to favour responsiveness and raises the GPU’s minimum clocks to
**1850 MHz for graphics and 1200 MHz for the media engine**. These are within the
GPU’s supported range; the maximum clocks are unchanged.

We tested the CPU preference, GPU clocks and power limits separately, then in
combination, with two runs of each setting. CPU preference and GPU clocks each
helped. Together they reduced average client latency from **8.00 to 6.29 ms**
and p99 from **10.55 to 7.24 ms**. p99 is the time within which 99% of measured
frames were presented, so its improvement means fewer slow frames.

Higher GPU clocks cut decode wait from about **5.5 to 4.6 ms**. CPU performance
preference mostly shortened frame preparation and the wait for presentation.
The graph shows the full comparison; dots mark the individual runs.

![Streaming latency with individual CPU, GPU and power settings](docs/tuning/tuning-effects.png)

These measurements cover frame receipt on the client through the display
controller’s flip timestamp, at 4K HDR, 4:4:4 and roughly 116 FPS. They exclude
host processing, network transit before receipt and TV processing.
[Full results and how to change the profile](PERFORMANCE.md#streaming-profile).

## Before you start

This is an experimental community project, not an official Bazzite release.
Tested on the K17 with Intel Arc 130V graphics. Other PCs are untested.
Secure Boot must be disabled.

Only one of the K17's two HDMI ports supports **HDMI 2.1 FRL**, the link mode
needed for this output. If 4K120 isn't available, try the other port. Use a
suitable HDMI cable and TV; any receiver between the PC and TV must also support
the signal.

The main missing console convenience is **CEC**—the HDMI feature that turns on a
TV and selects its input. The K17 does not expose usable CEC control in this setup.
You can add similar behaviour over your network. See
[TV and receiver control](docs/TV-CONTROL.md) for setup examples.

## Start streaming

[Set up your gaming PC and pair MoonDeck](docs/STREAMING.md). Once paired, pick a
Steam game and use its MoonDeck button to play it on the TV.

For the underlying hardware work, see the [kernel notes](kernel-notes/README.md).
Build and publishing instructions live in [MAINTAINING.md](MAINTAINING.md).

Built on the work of Bazzite, the Linux and Intel graphics communities, BORE,
Moonlight, Nonary's VRR work, Decky and MoonDeck. Project changes were developed
with Codex; source and test details are included in this repository.
