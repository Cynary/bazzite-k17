# Play your gaming PC's games on the TV

Moonlight receives video and sound from your gaming PC and sends your controller
input back. MoonDeck adds a button to Steam that starts this process for the game
you choose. MoonDeck Buddy runs on the gaming PC and handles launching it.

## On your gaming PC

1. Install [Vibepollo](https://github.com/Nonary/Vibepollo), or your preferred
   Sunshine fork, and finish its setup. This is the streaming server that captures
   video and audio from your gaming PC.
2. Install [MoonDeck Buddy](https://github.com/FrogTheFrog/moondeck-buddy/releases)
   **1.11.0 or newer** (currently a prerelease), which supplies the protocol used
   by the bundled MoonDeck. Let it run in the background. Follow its setup instructions, including
   adding the **MoonDeckStream** application to your streaming server.
3. Sign into Steam. A wired network connection is a good starting point for both PCs.

## On Moonmachine

1. Open Moonlight from the desktop application menu. Select your gaming PC and
   enter the displayed pairing PIN in your streaming server's web interface on
   that PC.
2. Return to Gaming Mode. Open the quick-access menu, select Decky, then MoonDeck.
3. Add your host in MoonDeck and pair with Buddy, following the prompts. This is
   a separate pairing from Moonlight's.
4. Open a Steam game's page and use the MoonDeck button to stream it.

Moonmachine configures MoonDeck to use the included Moonlight executable. You
can also open Moonlight directly when you want to stream the whole desktop.

Start at a resolution and frame rate your network and host can sustain. Then
increase to 4K120 and enable HDR if the complete path supports it. Enable VRR in
Steam's display settings and in Moonlight, with Moonlight's V-sync enabled.
To check VRR, run a stable frame-rate test below the TV's maximum refresh rate
and watch its refresh-rate display follow the stream.

Quit through the game's own menu to close it on the host and finish the session.
To also close the host game when you exit from local Steam, enable **Close Steam
app on host on user game exit** in MoonDeck's game-session settings. This applies
after the game has launched; it does not cancel an installation or update.

## Included versions

The image bundles Decky 3.2.9, MoonDeck 1.12.2, and
[Nonary's Moonlight 6.1.0-vrr17.1](https://github.com/Nonary/moonlight-qt/releases/tag/v6.1.0-vrr17.1),
which adds VRR support. See [application versions and patches](../apps/README.md). Moonlight is packaged in the OS so its libraries are
available immediately, without downloading a Flatpak runtime on first boot.
The bundled upstream MoonDeck pauses its background splash automatically while
Moonlight has focus, avoiding extra display refreshes during the stream.

System updates include Moonlight and image-managed MoonDeck updates. Installing
a different MoonDeck version through Decky replaces the bundled plugin and opts
that installation out of image-managed plugin updates.

If you remove Decky or MoonDeck and want them to stay removed, create
`/etc/moonmachine/disable-app-setup` before uninstalling. That disables the
first-boot setup helper on subsequent boots too.

## Initial stream settings

New Moonlight profiles start at 3840×2160, 120 FPS, 500 Mbps, HDR, YUV 4:4:4,
Direct YUV presentation, V-sync on, legacy frame pacing off and the VRR Low Latency
preset. Existing profiles are preserved. These settings target a wired K17 and
4K120 HDR TV; reduce bitrate/resolution or disable HDR for other networks/displays.
The host must support the requested codec and colour format.

Gaming Mode's Moonmachine service keeps VRR enabled and Steam's compositor frame
limit disabled. This prevents Steam's saved performance preferences from capping
the stream independently of Moonlight. It does not add VRR hardware support; the
kernel, display and application still need to support it. The uncapped-scheduling
fix and default are separate from this FPS limiter.

To let Steam control these two settings instead, create
`~/.config/moonmachine/disable-vrr-defaults` and stop the user service:

```sh
mkdir -p ~/.config/moonmachine
touch ~/.config/moonmachine/disable-vrr-defaults
systemctl --user stop moonmachine-vrr-defaults.service
```

Remove that file and start the service to restore the streaming defaults.
