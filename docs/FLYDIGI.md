# Vader 5 Pro integration in development

This branch packages [Flydigi Control](https://github.com/Cynary/flydigi-control),
a controller-friendly configuration app for lighting, Turbo and Fn profile
shortcuts. It uses a pinned source commit from `apps/sources.json`.

The app has passed protocol and offscreen UI tests on the K17. All extra buttons
have been captured from hardware, and Steam events confirm M1–M4, C/Z, Fn and
Turbo. The corrected colors have been confirmed visually. LM/RM Steam events,
actual bindings and animations still need hardware validation. The user has
confirmed off/on navigation recovery and raw button testing without restarting
the app. Controller-triggered wake is not supported by the tested receiver. This branch must not be promoted as full
Vader support until those checks pass.

The image installation adds `/usr/bin/flydigi-control`, its desktop entry and a
udev rule granting the active desktop user access to the Vader configuration
interface. It does not replace xpad, create a virtual gamepad, automatically change
Steam controller settings, or enable a wake policy. The app offers an explicit
Native Steam Input permission toggle; this was necessary for native detection
on firmware 7.1.5.0. The patched driver switches between native and Xbox-compatible input when
this setting changes; earlier Steam drivers may need a restart.

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
cleanup. The full image boots successfully; the remaining physical checks below
are required before release.


### Driver-stage build check (2026-10-08)

Built the new stage from the pinned Bazzite base on the K17. The loader tests,
launch-argument and update-fallback tests passed, along with 12,289 SDL parser
cases. The packaged library is 32-bit and exports all 1,307 SDL symbols from the
installed Steam library; none are missing. Its linked dependencies resolve.
The output includes the SDL and launcher sources and both licenses.

These stage checks were followed by the full image boot check below.


The stage-produced SDL was then loaded by Steam on the K17. Steam enumerated
one native Vader 5 Pro (controller type 30, style 7), retained the complete
mapping including `misc1:b20`, and reported capability mask `66586431487`.
The 32-bit process mapped only the replacement SDL. Flydigi Control relaunched
through its Steam shortcut. This checks initialization after a Steam restart;
it does not replace the physical reconnect or binding tests.


## Waking the PC

The tested wireless receiver (`37d7:2401`) reports USB configuration attributes
`0x80`: it does not advertise remote wake. Linux consequently exposes no
`power/wakeup` setting for that device. Its runtime power control is already
`on`, so disabling autosuspend does not supply the missing capability.

Linux distinguishes a device's ability to signal wake from the policy allowing
it to do so; see [device power management](https://docs.kernel.org/driver-api/pm/devices.html).
Enabling a parent USB hub's wake policy cannot establish receiver support.
There is currently no verified way to wake this PC with this receiver. No wake
quirk, firmware write or global USB power-policy change is included in the image.


Steam's configuration editor also accepted a test keyboard binding for each of
the ten extra controls. The test did not save the edits; reopening the editor
returned the original configuration byte-for-byte after excluding its temporary
binding handle. This verifies editable bindings, not that a physical press has
produced the assigned keyboard action. That last check remains open.

The complete candidate image built successfully from commit `3e5898c`:
28 Flydigi tests, the SDL replay/loader checks, 68 Gamescope tests, Moonlight and
setup tests, and 13 bootc checks passed. The candidate's Intel display module
hash matches the running K17 exactly, and its xone source version is unchanged.
It has not been promoted to the public update channel.


### Full image boot check (2026-10-08)

The K17 booted the candidate built from `3e5898c`, with OSTree checksum
`305818a75f52bc02ad64b69abfd3d8855e21bfb0bed56d26661b877b07f79412`.
Steam loaded `/usr/lib/moonmachine/steam-sdl/lib32/libSDL3.so.0` through the
image launcher, without the temporary test launcher override. The Steam
shortcut launched the image's `/usr/bin/flydigi-control`. The refused-sleep
recovery service also runs from the image; its former override was identical.

Steam's event capture confirmed presses and releases for M1–M4, C, Z, Fn and
Turbo. An earlier raw report capture included LM and RM; their Steam event
check remains open, as does a physical press producing an assigned Steam Input
action. Lighting colour was confirmed by the tester; Flow animation still
needs a visual check.

That boot exposed a duplicate-controller bug in SDL's fallback handling. Native
mode stopped Xbox reports, but Steam retained the Xbox entry with a held A
button. The subsequent [SDL fix](https://github.com/Cynary/SDL/blob/vader5-turbo/validation/FLYDIGI-HANDOFF.md)
removes and recenters the Linux fallback when native mode takes over, and restores
it when native mode is disabled. Live permission-off/on testing switched between
one Xbox entry and one native entry without restarting Steam. The image now pins
that fix and runs its transition regression test. Physical reconnect and assigned
action delivery remain required before promotion.


The follow-up image built from `7aff03c` also passed the build tests and booted
successfully. Its OSTree checksum is
`3e91ea80266835c2d6bd1a3fb58274f445710124200f956fca9e82e8427a0a17`.
Steam mapped the image's SDL library with SHA-256
`5cd2ffdf3f1357f9d0d61ee3abc903f0c3ea51649a4de168a05fd4792a937dc3`;
the temporary library override was removed. Flydigi Control launched from the
image, and no user services failed. The controller was off after this reboot,
so its next physical reconnection remains a validation step. The public update
channel has not been changed.

### Reconnect fixes and battery follow-up

The next candidate updates both the app and Steam SDL. The app now pumps SDL
hotplug events even while unfocused, so reconnecting a controller restores
navigation without restarting the app. A missing input stream produces a
clear error in the button test. The user confirmed navigation and raw button
testing after an off/on cycle with the same app process.

SDL keeps the receiver available when Steam starts with the controller off,
retries discovery, and limits acquisition retries to once per second after
input stops. Previously, a missing reply could cause hundreds of acquisition
requests per second. The image build runs the reconnect regression alongside
the button parser and native/fallback transition tests.

Battery reporting confirms a zero reading after two seconds: the receiver was
captured reporting zero briefly and then returning to 40%. This preserves real
empty-battery warnings without immediately publishing that transient. Steam's
initial 100% display remains under investigation. Its Turn off controller menu
does not send a command for this device; remote shutdown is not implemented.

These newer revisions are pinned in the branch but have not yet passed the full
image boot check. The running machine currently uses a local SDL/app override
for validation; the older boot-check results above do not cover these changes.
