# Vader 5 Pro integration in development

This branch packages [Flydigi Control](https://github.com/Cynary/flydigi-control),
a controller-friendly configuration app for lighting, Turbo and Fn profile
shortcuts. It uses a pinned source commit from `apps/sources.json`.

The app has passed protocol and offscreen UI tests on the K17. All extra buttons
have been captured from hardware, and Steam events confirm M1–M4, C/Z, Fn and
Turbo. The corrected colors have been confirmed visually. LM/RM Steam events,
actual bindings, animations, reconnect behavior and controller-triggered wake
still need hardware validation. This branch must not be promoted as full
Vader support until those checks pass.

The image installation adds `/usr/bin/flydigi-control`, its desktop entry and a
udev rule granting the active desktop user access to the Vader configuration
interface. It does not replace xpad, create a virtual gamepad, automatically change
Steam controller settings, or enable a wake policy. The app offers an explicit
Native Steam Input permission toggle; this was necessary for native detection
on firmware 7.1.5.0. Restart Steam after enabling it; a receiver reconnect alone did not refresh
the input path in our test.

Use the app's [validation procedure](https://github.com/Cynary/flydigi-control/blob/main/docs/VALIDATION.md)
for the remaining hardware checks. The image build runs its protocol tests and
renders the app offscreen to check runtime dependencies.

The preview now includes a safe button-test page and RGB editing, multicolor breathing and gradient, Flow and steady lighting controls with configuration readback. [Lighting notes](https://github.com/Cynary/flydigi-control/blob/main/docs/LIGHTING.md) record the official app’s settings, exact presets and remaining gaps.

## Steam's controller driver

The candidate image also builds the [SDL fork](https://github.com/Cynary/SDL/tree/vader5-turbo)
that adds Turbo to Steam's existing native Vader driver. Turbo reports a short
pulse; it does not report a continuous held state like an ordinary button. Fn
can be mapped independently with the controller's built-in profile shortcuts off.
The app exposes both firmware feature toggles.

Gaming Mode runs Steam through `steam-flydigi`. This keeps Steam's files intact
and selects the replacement only when the bundled 32-bit SDL has the tested
checksum. Games and steamwebhelper retain their normal libraries. An unknown
Steam update falls back to Steam's driver; Turbo support then needs revalidation
against that SDL version. Do not update the approved checksum without rebuilding
and testing the matching source revision.

The application, SDL source, launcher and licenses are included in the image.
`FLYDIGI_STEAM_DISABLE=1` disables the replacement on the next Steam start.
An explicit `STEAMCMD` override needs to use `steam-flydigi` to select it.
The launcher has fallback and argument-preservation tests; its native loader test
checks both ordinary and isolated library namespaces and child environment
cleanup. Full image boot and hardware checks remain required before release.


### Driver-stage build check (2026-10-08)

Built the new stage from the pinned Bazzite base on the K17. The loader tests,
launch-argument and update-fallback tests passed, along with 12,289 SDL parser
cases. The packaged library is 32-bit and exports all 1,307 SDL symbols from the
installed Steam library; none are missing. Its linked dependencies resolve.
The output includes the SDL and launcher sources and both licenses.

This verifies the driver build and packaging, not a full Moonmachine boot. The
live hardware test still uses the earlier locally built candidate. The packaged
library must be checked in Steam before promotion.
