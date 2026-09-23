# Steam Controller Lab

A Windows app for checking the new Steam Controller's native reports. It shows buttons and touch sensors, stick and trackpad coordinates, trigger and pad pressure, accelerometer and gyro values, and a 3D view driven by the controller's quaternion. The guided check records what actually arrived in Windows; skipped controls remain unverified.

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
