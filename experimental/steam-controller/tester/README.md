# Steam Controller Lab

A Windows app for checking the new Steam Controller's native reports. It shows buttons and touch sensors, stick and trackpad coordinates, trigger and pad pressure, accelerometer and gyro values, and a 3D orientation view. The optional Steam Input mode asks Windows Steam for orientation; the raw controller quaternion remains visible for comparison. The guided check records what actually arrived in Windows; skipped controls remain unverified.

This is an experimental tester for the native HID prototype in `../windows-native`. Moonlight and Vibepollo carry the picture and sound. **Controller traffic currently travels through a separate authenticated SSH relay.** This does not yet add native Steam Controller support to ordinary Moonlight clients. The physical controller stays on Linux; Windows sees an emulated device. No USB/IP is used.

## Build and launch

Run `build.cmd` on Windows with .NET Framework 4.x installed. It builds the app and runs the decoder and guide tests. The virtual driver and broker must already be installed using the prototype's instructions.

Run `install-app.ps1` beside the executable as administrator to add **Steam Controller Lab** to Vibepollo. It backs up the app list and disables ordinary Xbox emulation for this app only. Restart Vibepollo when no stream is running so it reloads the list.

On the computer with SSH access to both machines, run:

```sh
python3 run-lab.py --client linux-client --host windows-host \
  --broker C:/controller-lab/broker.exe --device /dev/hidraw5
```

Replace the SSH aliases, broker path and device. The broker path currently must not contain spaces. Check `/sys/class/hidraw/hidraw5/device/uevent`: it must identify Valve `28DE:1304`, interface `input2`. Do not assume the hidraw number survives reconnecting. Linux needs passwordless sudo for the gateway and sleep inhibitor.

Open **Steam Controller Lab** in Moonlight. The relay runs for 30 minutes by default (`--minutes` changes this), blocks Linux sleep while active, and removes the virtual device when it ends. Ctrl+C stops it early. It does not log controller serials or feature payloads.

## Guided check

Follow the instruction at the bottom. Button steps require release, press, and release again. Move analog controls through their full range. Motion steps ask for movement on each axis. The orientation step requires a visual check; Menu or Enter confirms it. The last steps play separate left/right vibrations: A confirms feeling one, B records a failure.

- **R:** restart the guide; **P:** previous step; **S:** skip without passing.
- **C**, or click the orientation panel: centre the displayed pose.
- **H / J:** repeat left/right vibration.
- **F9:** save results; **F11:** fullscreen; **Esc:** leave fullscreen; **Ctrl+Q:** quit.

Completion saves JSON under `Documents/Steam Controller Lab`. Results include observed ranges, button transitions, step outcomes, device identity and the last raw report. A solid connection alone is not a successful control test.

## What has been checked

The Windows build passes 11,094 automated decoder, guide and orientation-math checks. A synthetic report sent through the real Windows virtual HID driver was received byte-for-byte. A separate physical-controller capture received 2,632 reports with zero malformed reports. These establish the transport and reader, not the correctness of every physical control. Left/right vibration was previously confirmed by hand through the prototype.

The viewer exposes 30 identified button/touch bits and labels the remaining two bits as unknown. It decodes full `0x42` and compact `0x45` reports; compact reports have no quaternion. It requests raw motion and orientation using the runtime IMU setting. Physical axis directions, touch/pressure thresholds and all guided steps still need validation. Battery/status and advanced haptic formats are not implemented in the viewer.

Steam on either side may also configure the controller or consume its input. Exclusive local-versus-remote input routing is still unfinished. Do not treat this prototype as a complete replacement for the normal streaming controller path.

## Testing Steam Input orientation

Add `SteamControllerLab.exe` as a non-Steam game in Windows Steam and set its launch options to `--steam-input`. Put `steam_api64.dll` from the current Steamworks SDK beside the executable; the DLL is not included in this repository. Launch the shortcut through Steam.

This development test uses Steam's sample application ID 480 to initialize the public Steamworks API. It is not an app registered on Steam. It calls `SteamAPI_RunCallbacks`, runs an explicit Steam Input frame, and reads `GetMotionData` for a Steam Controller. The 3D model uses that result, while the numerical raw HID quaternion below it still comes from the device reports. `steam-motion.jsonl` records Steam's motion values beside the executable.

On the tested firmware, the raw quaternion remains `(32767, 0, 0, 0)`. Windows Steam identifies the emulated controller as type 17 (Steam Controller 2026) and returns a non-identity quaternion. Steam documents this orientation as accumulated gyro rotation. This test does not implement its own motion fusion or change controller firmware.

The guided orientation step still checks raw reports; it does not automatically pass based on Steam Input's result. The separate 3D view is the Steam Input check.

The orientation model has a bevelled shell, rounded grips, raised sticks, trackpads, shoulder controls and rear buttons. It uses a depth buffer so the back and front occlude correctly during rotation. This is an illustrative model, not a measured scan.

### Orientation reset workaround

The physical controller sometimes sends multiple reports with the same IMU timestamp. In the Windows Steam Input test this made `GetMotionData` intermittently return an exact neutral quaternion, then resume its prior orientation. This occurred with an unchanged controller handle. Changing the raw quaternion or removing that field did not help. Dropping repeated-timestamp reports did, but could also drop button changes.

The prototype relay now preserves every report and separates repeated IMU timestamps by one microsecond. The next real sensor timestamp is preserved, so these small adjustments do not accumulate into clock drift. Clock wrap and genuine resets are handled separately; adjustment is bounded to 1,000 microseconds. Buttons, pressures, sensor values and raw quaternion bytes are unchanged. This is a compatibility workaround for the observed Steam Input behavior, not a firmware fix or custom orientation filter.

Two ten-second baseline phases produced 24/163 and 10/214 neutral API samples. The two adjusted phases each produced 0/213. `test_imu_clock.py` verifies button preservation, compact reports, timestamp wrap, reset and bounded adjustment. The Windows viewer's existing 11,094 checks also pass. The experiment identifies the repeated timestamp as the trigger; it does not establish the internal bug in Steam's closed-source implementation.

The final 45-second capture recorded 967 samples with zero neutral resets, and the user confirmed smooth orientation while tilting and rotating the controller.
