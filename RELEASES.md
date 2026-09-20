# Install Moonmachine

Start with a normal Bazzite installation, then switch it to Moonmachine. You don't
need to build a kernel or make a special installer USB.

## Connect your TV

Only one of the K17's two HDMI ports supports **HDMI 2.1 FRL**, which is needed
for 4K120 with 10-bit colour and 4:4:4. If that mode isn't available after
installing Moonmachine, try the other HDMI port. The cable, TV and any receiver
in between also need to support it.

## 1. Install Bazzite

Use the [Bazzite download page](https://bazzite.gg/) to choose the Intel-compatible
HTPC image with Steam Gaming Mode. Install it on the K17, finish the initial setup,
and check that Steam opens. Secure Boot must be disabled for Moonmachine's kernel.

## 2. Switch to Moonmachine

In Steam's power menu, choose **Switch to Desktop**. Open Konsole and run:

```sh
git clone https://github.com/Cynary/bazzite-k17.git
cd bazzite-k17
sudo ./scripts/join-moonmachine-channel.sh
```

This downloads Moonmachine, checks its signature, and keeps your current Bazzite
system as a fallback. It changes the operating system on the next boot; it does
not erase your games or home folder. Only install this if you trust the project:
its signing key is the `cosign.pub` file in this repository.

When the command finishes, reboot:

```sh
sudo systemctl reboot
```

Moonlight, Decky and MoonDeck are included. Open the Steam quick-access menu to
find Decky, then follow the [streaming setup guide](docs/STREAMING.md) to pair your
gaming PC. Decky is prepared for the first regular account created during installation.

## Updates

Use Bazzite's normal system-update controls and reboot when prompted. You will
receive new Moonmachine releases as they are published. There is no need to clone
this repository or run the installation command again.

The update source is `ghcr.io/cynary/bazzite-k17:moonmachine`. The final part,
`moonmachine`, is the release channel: a name that always points at the latest
approved image. Updates are signed and checked before installation.

Prefer the terminal? Run `sudo bootc upgrade`, then reboot.

## If an update goes wrong

Bazzite keeps an earlier copy of the operating system so you can go back without
reinstalling. If you can reach the desktop, run:

```sh
sudo bootc rollback
sudo systemctl reboot
```

If the desktop won't start, hold Shift during startup to show the boot menu and
choose the previous system entry. The original Bazzite installation is also kept
by the installation script. Keep a keyboard handy for this recovery step.

## Release notes

[GitHub releases](https://github.com/Cynary/bazzite-k17/releases) list what changed,
the checks performed, and known limitations. The large archive files there are
for image publishing and offline development; they are not installer ISOs and
don't need to be downloaded for the installation above.
