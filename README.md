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
- Moonlight with VRR support, Decky (Steam's plugin menu), and upstream MoonDeck.
- A custom kernel with BORE, which schedules CPU work with responsiveness in mind,
  and ThinLTO, which lets the compiler optimise across source files.
- Graphical boot and updates through Bazzite's normal system-update controls.
- [MediaTek Wi-Fi and Xbox Wireless Adapter fixes](docs/HARDWARE-FIXES.md)
  for firmware loading and controller reconnection after restarting.

**[Install Moonmachine →](RELEASES.md)**

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
