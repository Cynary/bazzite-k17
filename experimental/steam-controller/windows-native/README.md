# Native Steam Controller Windows prototype

This is a separately installed UMDF/VHF driver for the 2026 Steam Controller's native reports. It uses the vendor collection captured from a Valve 28de:1304 puck. It does not translate the controller into an Xbox pad. Mouse and keyboard collections are deliberately absent.

**Experimental: not integrated into Moonlight or Vibepollo yet.** The SSH relay is a development harness for controller reports. The intended transport is Moonlight’s authenticated connection; neither uses USB/IP. Normal Vibepollo continues using its existing driver.

## Verified so far

- Built with MSVC `/W4 /WX`, UMDF 2.15, SDK/WDK 10.0.26100.6584 NuGet packages.
- Microsoft's catalog generation checks passed without warnings.
- Test-signed driver installed and loaded on Windows 11 with Secure Boot still enabled. No boot configuration or signature-enforcement settings were changed.
- Windows Steam discovered VID 28de/PID 1304 and opened its Steam Controller backend. With live forwarding, Steam read the real hardware/firmware information, established the wireless connection and loaded its Triton controller configuration. Per-game control mappings still need validation.
- A 40-second live run forwarded 10,652 native reports. Twenty-one output operations completed successfully, including independent left/stop/right/stop rumble commands; the user confirmed feeling vibration on the physical controller.
- A Windows HID reader received twenty recorded 54-byte native reports byte-for-byte intact. The test compares a checksum with the original bytes, including pads, pressure and motion fields.
- Descriptor tests check every advertised input length and known haptic output length, both feature report sizes, and rejection of firmware/pairing/calibration writes.
- Real hardware answered the attributes query on feature report 2. Steam's `CGetTritonDonglePairingBondWorkItem` sends `02 a3 00`; the real puck answers with `02 a3 18`. These replies contain device-specific data and are not checked in.

## Driver behavior

One broker owns the virtual controller. Native input is passed without reinterpretation through a bounded queue. Feature requests and output writes have unique IDs, a bounded queue and a two-second timeout. Closing the broker removes the virtual HID child and cancels pending operations before deleting it. The driver refuses replies from another owner or to an expired operation.

Report 1 addresses the controller; report 2 addresses the puck. Read replies can be temporarily unavailable while a command is crossing the radio link. Unknown feature commands are reported to the diagnostic broker but always fail, even if the broker replies with success. The Linux endpoint independently validates allowed commands. Firmware updates, factory reset, writing pairing data and calibration operations are not permitted. Unknown haptic formats remain unsupported.

The virtual driver's source device is `ROOT\MOONMACHINESTEAMHID`. It has its own device-interface GUID, service, package name and non-shared UMDF host process, so it does not replace `ROOT\VIBESHINEVIRTUALGAMEPAD`.

## Development

`build.cmd` builds the driver, broker, HID read probe and protocol tests. It expects Visual Studio 2022 Build Tools and the pinned SDK/WDK NuGet packages under `%USERPROFILE%\controller-forwarding\wdk-packages`.

`package.ps1` creates a development code-signing certificate with a non-exportable key and a 90-day validity period, signs the DLL and creates/signs its catalog. It does not trust the certificate or install the driver. Development installation requires trusting that particular certificate in LocalMachine Root and TrustedPublisher, then:

```powershell
.\broker.exe install "$PWD\package\MoonmachineSteamHid.inf"
```

This is a local development package, not a distributable release signature. Retain `certificate-thumbprint.txt` to remove precisely this certificate later. Remove only the `ROOT\MOONMACHINESTEAMHID` device and its associated OEM INF when uninstalling; do not remove the existing Vibepollo driver.

`relay.py` is currently a lab harness using the `k17` and `shed` SSH aliases. `gateway.py` runs on Linux and checks the physical device identity before any write. `replay_test.py` exercises native input delivery with a recorded report; it deliberately fails all firmware requests, so its success does not imply Steam initialization succeeded.

## Remaining work

Validate per-game Steam Input mappings and all remaining feature/haptic formats. Native identification, input transport and a physical haptic round trip have passed. User-store writes and unknown commands remain deliberately unsupported. Then integrate attachment negotiation and the bounded request/reply protocol into Moonlight/Vibepollo's authenticated connection. That integration must transfer ownership away from local Steam Input during the stream, avoid duplicate Xbox forwarding, and restore local control on disconnect. Multi-controller routing, reconnects and latency need tests before enabling this in an image.

## Initialization findings

Use the puck’s actual `bcdDevice=0x0002`. A placeholder revision caused Steam to choose its older HID protocol. With the real revision, Steam uses the native Triton path. The controller and puck each have a feature channel; replies must remain associated with their operation and controller.

The initial asynchronous feature implementation retained the callback packet-wrapper address. Returning a feature response later caused an access violation. The driver now copies that wrapper, retaining only the outstanding operation’s report buffer. Subsequent live runs, including native feature replies and haptics, completed without that crash. Process pooling is disabled for this experimental driver so failures cannot terminate the regular Vibepollo driver’s UMDF process.

Additional command names were checked against the original research/code in [openpuck](https://github.com/safijari/openpuck/blob/main/OpenPuck/steam_commands.h) and [sc26re](https://github.com/mwdmwd/sc26re/blob/main/app/src/valve_feature.h). These are community protocol reconstructions, not a Valve compatibility guarantee.
