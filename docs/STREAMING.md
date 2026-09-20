# Play your gaming PC's games on the TV

Moonlight receives video and sound from your gaming PC and sends your controller
input back. MoonDeck adds a button to Steam that starts this process for the game
you choose. MoonDeck Buddy runs on the gaming PC and handles launching it.

## On your gaming PC

1. Install [Sunshine](https://docs.lizardbyte.dev/projects/sunshine/latest/) and
   finish its setup. It captures and streams your games.
2. Install [MoonDeck Buddy](https://github.com/FrogTheFrog/moondeck-buddy/releases)
   and let it run in the background. Follow its setup instructions, including
   adding the **MoonDeckStream** application to Sunshine.
3. Sign into Steam. A wired network connection is a good starting point for both PCs.

## On Moonmachine

1. Open Moonlight from the desktop application menu. Select your gaming PC and
   enter the displayed pairing PIN in Sunshine's web interface on that PC.
2. Return to Gaming Mode. Open the quick-access menu, select Decky, then MoonDeck.
3. Add your host in MoonDeck and pair with Buddy, following the prompts. This is
   a separate pairing from Moonlight's.
4. Open a Steam game's page and use the MoonDeck button to stream it.

Moonmachine configures MoonDeck to use the included Moonlight executable. You
can also open Moonlight directly when you want to stream the whole desktop.

Start at a resolution and frame rate your network and host can sustain. Then
increase to 4K120 and enable HDR if the complete path supports it. Enable VRR in
Steam's display settings and in Moonlight. To check VRR, run a stable frame-rate test below the TV's maximum refresh rate
and watch its refresh-rate display follow the stream.

Quit through the game's own menu to close it on the host and finish the session.
Disconnecting the stream can leave the game running on the host.

## Included versions

The image bundles Decky 3.2.9, upstream MoonDeck 1.12.2, and
[Nonary's Moonlight 6.1.0-vrr17.1](https://github.com/Nonary/moonlight-qt/releases/tag/v6.1.0-vrr17.1),
which adds VRR support. Moonlight is packaged in the OS so its libraries are
available immediately, without downloading a Flatpak runtime on first boot.
Decky and MoonDeck retain their normal upstream update controls.

If you remove Decky or MoonDeck and want them to stay removed, create
`/etc/moonmachine/disable-app-setup` before uninstalling. That disables the
first-boot setup helper on subsequent boots too.
