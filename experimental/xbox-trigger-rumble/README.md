# Independent Xbox trigger rumble: hardware trial

This candidate adds separate control of the two grip motors and two trigger motors on Microsoft Xbox controllers connected through xone. It is ready for a physical test, not a published image feature.

## Changes

- Linux: backport Guillaume Casal’s proposed `FF_TRIGGER_RUMBLE` input API and mixer support. This remains an experimental API. The four kernel patches include attribution and source links.
- xone: update either motor pair independently, including independent stops. Only Microsoft controllers advertise the new capability. The dongle firmware, radio initialization, restart and suspend fixes are unchanged.
- SDL 3: implement Linux evdev trigger rumble using a separate effect slot. This library is private to Moonlight; Steam and system SDL are unchanged.

Moonlight already receives trigger-rumble messages and calls SDL’s trigger-rumble API. Its SDL2 compatibility library forwards that call to SDL3. No new network message is needed for this trial.

The Windows host needs Vibepollo’s newer Xbox Series virtual-controller backend for the eventual network test. The installed stable host still uses the virtual Xbox 360 path; it has not been upgraded. Test the Linux half first.

## Hardware validation

Close the stream, then run from the computer with the `k17` SSH alias:

```sh
ssh -t k17 '~/xbox-trigger-rumble-20260923/validate.sh --stage'
ssh k17 'sudo systemctl reboot'
```

The first command verifies the local image digest and asks you to type `stage`. After reboot, turn on the controller and run:

```sh
ssh -t k17 '~/xbox-trigger-rumble-20260923/validate.sh'
```

Choose the controller index printed by the script. Hold the controller and press Enter. It exercises each motor separately, then checks that stopping one pair leaves the other pair running. Pulses use 35% strength for about one second. Ctrl+C stops the test.

Report which motors you felt for each labeled step, especially whether LEFT TRIGGER and RIGHT TRIGGER are distinct. Also report any failure to reconnect after reboot. Accepted API calls do not establish that physical motors work.

To return to the published image:

```sh
ssh -t k17 '~/xbox-trigger-rumble-20260923/validate.sh --restore'
ssh k17 'sudo systemctl reboot'
```

If the candidate cannot boot, select the previous deployment in the boot menu. Nothing was published. Return to the published channel with `--restore` before expecting normal image updates.

## Checks completed

The kernel, force-feedback module, xone module and SDL compile. Tests compile the actual changed callbacks with mocked OS calls, checking independent motors, magnitude conversion, stops, capability gating and error handling. The SDL motor test compiles with warnings treated as errors and detects the connected controller without issuing motor commands.

The image passes `bootc container lint`; the initramfs contains the new modules and libraries resolve. The dongle module is unchanged. Candidate boot, physical feedback and end-to-end streaming remain untested.

`windows-motor-test.ps1` exercises the same four motors through Windows.Gaming.Input. Syntax and API types were checked. It requires the new host backend and an active stream; it has not sent physical effects yet.

## Build record

Base: `moonmachine-20260923.2`, kernel `7.2.4-k17bore1+` with existing configuration and patches. SDL: release 3.4.16, commit `fa2c02bb6e21974a89ea9824bc53c9932abe5f9c`. xone: packaged source `982cbcb019ae4d2bee5ae69385223409ee555c88` plus existing image fixes.

Apply the four kernel patches, build `bzImage` and `drivers/input/ff-memless.ko`, and generate sanitized headers with `make headers_install`. Build patched xone against that kernel. Build patched SDL with the sanitized input headers on its include path; confirm `SDL_JOYSTICK_LINUX` is enabled. This trial retains X11/Wayland and disables SDL KMSDRM.

`test_effects.py WORKSPACE` expects patched sources under `WORKSPACE/xone` and `WORKSPACE/SDL`, and sanitized headers under `WORKSPACE/uapi/linux`. `Containerfile.candidate` packages the artifacts into a separate local image. Its base tag and paths are this trial’s build inputs, not a general release pipeline.

Exported OCI manifest:

```
sha256:caf5eb2099924b0ddbb99a19135e357c8fa7676314caa364ef7515bd5643c3dd
```

References: [Linux API proposal](https://lists.openwall.net/linux-kernel/2026/07/31/470), [Vibepollo beta](https://github.com/Nonary/Vibepollo/releases/tag/2.0.0-beta.3), [libvirtualgamepad](https://github.com/Nonary/libvirtualgamepad).
