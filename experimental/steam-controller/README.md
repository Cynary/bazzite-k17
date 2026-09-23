# Steam Controller 2026 forwarding: first implementation

The goal is to let Windows Steam Input see a Steam Controller, including its touchpads, grip sensors, back buttons, motion and haptics, while the controller stays connected to the streaming client. This does not use USB/IP.

This directory contains the report codec, a proposed transport payload, tests and a read-only capture tool. It is **not yet connected to Moonlight or a Windows virtual controller**. Passing these tests does not establish Steam Input compatibility.

## What is available in open source

[SDL’s Triton driver](https://github.com/libsdl-org/SDL/blob/release-3.4.16/src/joystick/hidapi/SDL_hidapi_steam_triton.c) reads the 2026 controller. Valve’s accompanying report structures document native buttons, pads, pressure, IMU data and several haptic commands. SDL supports ordinary left/right rumble, but that is not the controller’s entire haptic interface.

[Vibepollo’s virtual-controller driver](https://github.com/Nonary/libvirtualgamepad) is MIT-licensed and can be extended. It does not currently provide a Steam Controller profile. Steam Input itself is not supplied as open-source code by those projects, so its recognition and initialization behavior still needs to be tested.

Sources inspected:

- SDL release 3.4.16, `fa2c02bb6e21974a89ea9824bc53c9932abe5f9c`.
- libvirtualgamepad, `4b56fb9da177f320fb2d7ddb1b6262e5d55d2750`.
- [SteamlessController](https://github.com/ddeverill/SteamlessController), `26c5b4ab6eee8aaf57eb9c99383eed3dfe475df2`, as a second source for discovery and initialization behavior.
- The two included HID descriptors were read from a connected `28de:1304` puck. They contain report declarations, not serial numbers or input captures.

## Code and checks

`triton.hpp` decodes native 0x42, 0x45 and 0x47 state layouts. It preserves signed axes, both pads and their pressure, all button bits, motion timestamps and quaternion data when present. The transport payload keeps the original report bytes, avoiding losses from mapping everything to an Xbox gamepad. It validates lengths, slot numbers and report types. A per-session sequence gate rejects duplicate and stale packets, including across sequence wraparound.

Known haptic output formats 0x80–0x85 are supported by the payload validator; the two-channel rumble encoder matches Valve’s packed structure. Unknown outputs and feature commands are not accepted. Windows-sized, zero-padded haptic reports are accepted. The captured descriptor also declares 0x86–0x89 outputs that need further investigation before claiming complete haptic support.

The payload is intended to travel **inside an authenticated streaming connection**. It has no authentication of its own, no socket listener and no assigned Moonlight network packet number. An implementation must negotiate support before sending it.

Run the portable tests:

```sh
./test.sh
```

They passed with GCC and address/undefined-behavior sanitizers on Linux, and MSVC on Windows. Tests cover native fields, haptic encoding, transport bounds, sequence wraparound and 100,000 malformed inputs. They simulate packet handling, not a complete physical controller or Steam Input.

`test_sdl_layout.cpp` separately checks the codec against Valve’s actual packed structures. Build with `SDL/src/joystick/hidapi` on the compiler include path. That cross-check passed against the pinned SDL version.

## Capturing a live controller

Build `capture.cpp` with a C++20 compiler. It opens only Valve 1302–1305 hidraw devices, read-only. It does not send initialization commands, disable local Steam Input, pair a controller or activate motors.

```sh
g++ -std=c++20 -Wall -Wextra -Werror capture.cpp -o steam-capture
./steam-capture 20 > steam-state.jsonl
```

Turn the controller on, then move sticks, touch each pad and grip, press the back buttons and rotate it during the capture. Existing hidraw permissions are required. Exit code 4 means no native state reports arrived. Only recognized state reports are saved, with a relative monotonic timestamp and local endpoint name.

The initial capture found the puck but received no native state reports. Physical field and haptic validation remain pending.

## Integration still to build

1. Add capability negotiation and controller attachment metadata to Moonlight and Vibepollo. Select native forwarding explicitly, and avoid simultaneously forwarding the same controller as an Xbox pad.
2. Give Moonlight access to native reports while streaming. Return ownership to local Steam Input on disconnect, including restoring the appropriate controller settings. Keep system-navigation behavior explicit rather than letting two Steam instances consume the same controls.
3. Add a VHF Steam Controller profile using verified identity, descriptor and input reports. A puck endpoint is not necessarily interchangeable with the wired controller; do not substitute one identity for another without testing discovery.
4. Implement bounded, correlated feature-request/reply handling. Steam’s settings and identity requests must receive real responses or a verified emulation. Handle timeout, cancellation, unplug and reconnect without replaying an old response into a new session. Do not forward firmware-update commands as ordinary controller configuration.
5. Relay haptic output through the authenticated connection. Preserve pulse order; do not coalesce distinct haptic commands as if they were interchangeable rumble strengths.
6. Validate Windows Steam recognition and per-game Steam Input features, then latency and multiplayer. Packet simulation cannot prove those behaviors.

The captured puck descriptor does not declare report 0x47. The parser understands that newer SDL layout, but a virtual profile must advertise only the reports that its chosen descriptor actually supports.
