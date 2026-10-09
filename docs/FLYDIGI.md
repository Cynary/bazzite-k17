# Vader 5 Pro integration in development

This branch packages [Flydigi Control](https://github.com/Cynary/flydigi-control),
a controller-friendly configuration app for lighting, Turbo and Fn profile
shortcuts. It uses a pinned source commit from `apps/sources.json`.

**Release hold:** after the latest candidate boot, the tester saw a kernel panic
and the machine restarted twice unexpectedly. The panic stack was not preserved.
A subsequent filesystem scan found checksum errors. The cause is unresolved;
the successful controller checks below do not establish system stability. This
candidate must not be promoted until the crash and storage integrity are addressed.

After preserving recoverable data and replacing damaged logs, cache files and an
old container artifact, a full 302 GiB filesystem scrub completed with no errors.
Crash-report storage is now enabled for a recurrence. The panic itself remains
unexplained, so the release hold still applies.

Settings persistence is also required before release: the latest applied lights
and settings must survive reconnecting with the app closed. The current app only
uploads temporary lighting. [Persistence research and validation](https://github.com/Cynary/flydigi-control/blob/main/docs/LIGHTING.md#settings-persistence)
track onboard saving and the fallback of restoring settings from the PC.

The app has passed protocol and offscreen UI tests on the K17. All extra buttons
have been captured from hardware. All ten extra buttons, including LM/RM,
have also delivered assigned keyboard actions through Steam Input. An ordered
paddle test confirmed the printed M1–M4 labels. The corrected colors and Steam
Identify rumble have been confirmed physically. Flow animation still needs
visual validation. The user has
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

These revisions subsequently passed the image boot check recorded below.

### Native rumble

Steam Identify exposed a separate framing bug: rumble bypassed the helper that
removes the report ID for this receiver, so an extra `03` reached USB before
`5A A5`. The SDL fork now queues an unnumbered report for the Vader receiver;
other models keep their existing format. Steam's start and stop commands were
captured with the corrected framing. The user confirmed feeling Steam's Identify pulse with this driver.
The build runs the rumble callback regression as well as the input tests.

The full build also caught an unwritable log-directory startup failure in the
app. Logging now falls back to stderr; it cannot prevent the UI from opening.

### Reconnect and rumble image boot check (2026-10-09 UTC)

The image built from `9e150a4` passed 33 app tests, the SDL input/reconnect/battery/
rumble regressions, loader checks, application tests and 13 bootc checks. It booted
with OSTree checksum
`ebd735b88e8f235a273dfa300d53e5d0cde4211375aa6955f32eb2a7632e3774`.
Its OCI manifest digest is
`sha256:a8547988c157388c18a79f559761bac2e85f62db876758d01a9a4ca126434d1e`.

Steam loads the image's SDL, SHA-256
`94978e88828ca011fd358ff1f41b27312e7d7df8a573d5f66c7be4163290180f`,
with the temporary Steam launcher override removed. The app launcher now uses
the image's `/usr/bin/flydigi-control`. The kernel, Intel display module and xone
checksums pass the boot health check. Existing firmware ACPI warnings remain.
The user confirmed the controller remained connected across this reboot and
could navigate Steam. Steam initially showed an incorrect battery level, then
updated to 40%, matching the earlier hardware reading. The initial display
problem remains unresolved; eventual correction is not proof of a startup fix.
The remaining lighting check is pending. This candidate has not been promoted
to the public channel.

The assigned-action test caught reversed paddle assignments in its own Steam
configuration. Correcting those assignments produced A, B, C, D when the user
pressed M1, M2, M3, M4. No driver paddle changes were needed. See the
[reproducible test mapping](https://github.com/Cynary/flydigi-control/blob/main/experimental/STEAM-INPUT-CHECK.md).


## Candidates after the October 9 release hold

Two follow-up candidates are saved separately from the image's pinned sources:

- [Onboard settings](https://github.com/Cynary/flydigi-control/tree/onboard-settings),
  branch `onboard-settings`: back up the active profile, verify lighting and unchanged
  mappings, then save once and verify the new version. The app also has a guarded
  circle/rectangle and response-curve editor, passive analog/motion diagnostics
  and separate tests for all four motors, plus saved trigger/grip vibration
  controls. Commit `4c953ca` adds global filtering, calibration, precision,
  sensitivity and sleep controls with capability checks and verified readback.
  All 97 tests pass, including official
  curve reference vectors and offscreen UI tests, and the
  new pages have been visually inspected. Read-only hardware access confirmed the expected
  840-byte mapping format. No save has yet been sent to the controller; power-cycle
  validation remains required. Global-setting writes also await hardware tests;
  report-rate changes are excluded because the vendor UI and SDK disagree.
- [Four rumble motors](https://github.com/Cynary/SDL/tree/vader5-four-motors),
  commit `e4fe95e6d`: independent grip/trigger pairs, with one pair's stop preserving
  the other. Callback tests, existing regression replays and the full 32-bit
  build pass. It is not loaded into Steam, and physical motor testing is pending.

The [official-app coverage checklist](https://github.com/Cynary/flydigi-control/blob/onboard-settings/docs/FEATURES.md)
also tracks stick shape/curves/deadzones, motion, trigger settings and diagnostic
tests. This expands the remaining scope; LED controls alone are not app parity.
Neither candidate is in a released image. The panic investigation remains open.
