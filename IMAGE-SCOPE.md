# Shared image and personal configuration

Release scope agreed on 2026-09-19.

## Shared operating-system image

- K17 kernel, FRL/HDR/VRR fixes, Wi-Fi and Xbox driver fixes, graphical boot,
  and the selected BORE/ThinLTO configuration.
- Hardware-independent Gamescope fixes needed for working VRR. Distinguish
  correctness fixes from preferences: the current personal helper continuously
  forces VRR on and the FPS limiter off. Do not silently override everyone's
  per-game settings by shipping that helper enabled as a supposed bug fix.
  Establish which behavior needs correction and package that correction; expose
  an explicit setting if a workaround necessarily overrides those preferences.
- Target for a subsequent image: Moonlight with the required VRR support,
  Gamescope Flatpak extension, Decky and MoonDeck, with clean initial settings.
  Use public, pinned source/releases and record their provenance. Do not ship
  the owner's private launcher-support build as a hidden dependency.

## Local only

- TV/AVR control programs, wake/sleep units, device addresses and MAC mappings.
- TV, Moonlight and Buddy pairing credentials and client identifiers.
- Steam login, library shortcuts, host selection, controller preferences and
  account data. These are configured or synchronized per user after installation.
- Machine/user-specific network, SSH, encryption and recovery configuration.

Do not build the distribution by committing the configured running machine's
container/filesystem. Build from the pinned clean base and explicit source inputs.

## Application packaging approach

The application target is not implemented in `bore-20260919.1`: those applications
were installed separately on the owner's K17. The published OCI filesystem was
checked directly: its TV-control directory and all three AV service units are
absent, as are the owner's Decky directories.

For the next application-enabled image, bundle or fetch verified application
artifacts through a repeatable first-boot/first-user setup. Bazzite already uses
`bazzite-flatpak-manager.service` for system Flatpaks. Integrate with its mechanism
after inspecting the supported configuration rather than writing directly to a
running user's Flatpak repository during image construction.

Decky/MoonDeck need per-user installation and Steam integration. An idempotent
setup must preserve existing plugin settings and pairings, avoid interrupting a
running game, and never clone the maintainer's home directory. New users must
pair their own streaming host. Test a clean installation, an existing configured
installation, and an OS upgrade before publishing this variant.

The present release remains unchanged and digest-pinned; documentation of the
next-image scope does not imply that application preinstallation is complete.
