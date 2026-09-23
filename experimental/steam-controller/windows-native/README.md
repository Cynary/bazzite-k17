# Native Steam Controller Windows prototype

This is a separately installed UMDF/VHF driver for the 2026 Steam Controller's native reports. It uses the vendor collection captured from a Valve 28de:1304 puck. It does not translate the controller into an Xbox pad. Mouse and keyboard collections are deliberately absent.

**Experimental: not integrated into Moonlight or Vibepollo yet.** The SSH relay is a development harness for controller reports. The intended transport is Moonlight’s authenticated connection; neither uses USB/IP. Normal Vibepollo continues using its existing driver.

## Verified so far

- Built with MSVC `/W4 /WX`, UMDF 2.15, SDK/WDK 10.0.26100.6584 NuGet packages.
- Microsoft's catalog generation checks passed without warnings.
- Test-signed driver installed and loaded on Windows 11 with Secure Boot still enabled. No boot configuration or signature-enforcement settings were changed.
- Windows Steam discovered VID 28de/PID 1304 and opened its Steam Controller backend. Full initialization and game compatibility are **not** established.
- A Windows HID reader received twenty recorded 54-byte native reports byte-for-byte intact. The test compares a checksum with the original bytes, including pads, pressure and motion fields.
- Descriptor tests check every advertised input length and known haptic output length, both feature report sizes, and rejection of firmware/pairing/calibration writes.
- Real hardware answered the attributes query on feature report 2. Steam's `CGetTritonDonglePairingBondWorkItem` sends `02 a3 00`; the real puck answers with `02 a3 18`. These replies contain device-specific data and are not checked in.

## Driver behavior

One broker owns the virtual controller. Native input is passed without reinterpretation through a bounded queue. Feature requests and output writes have unique IDs, a bounded queue and a two-second timeout. Closing the broker removes the virtual HID child and cancels pending operations before deleting it. The driver refuses replies from another owner or to an expired operation.

The controller command channel uses report 1; the puck's pairing-information query uses report 2. Unknown feature commands are reported to the diagnostic broker but always fail, even if the broker replies with success. The Linux endpoint independently validates allowed commands. Firmware updates, factory reset, writing pairing data and calibration operations are not permitted. Unknown haptic formats remain unsupported.

The virtual driver's source device is `ROOT\MOONMACHINESTEAMHID`. It has its own device-interface GUID, service and package name, so it does not replace `ROOT\VIBESHINEVIRTUALGAMEPAD`.

## Development

`build.cmd` builds the driver, broker, HID read probe and protocol tests. It expects Visual Studio 2022 Build Tools and the pinned SDK/WDK NuGet packages under `%USERPROFILE%\controller-forwarding\wdk-packages`.

`package.ps1` creates a development code-signing certificate with a non-exportable key and a 90-day validity period, signs the DLL and creates/signs its catalog. It does not trust the certificate or install the driver. Development installation requires trusting that particular certificate in LocalMachine Root and TrustedPublisher, then:

```powershell
.\broker.exe install "$PWD\package\MoonmachineSteamHid.inf"
```

This is a local development package, not a distributable release signature. Retain `certificate-thumbprint.txt` to remove precisely this certificate later. Remove only the `ROOT\MOONMACHINESTEAMHID` device and its associated OEM INF when uninstalling; do not remove the existing Vibepollo driver.

`relay.py` is currently a lab harness using the `k17` and `shed` SSH aliases. `gateway.py` runs on Linux and checks the physical device identity before any write. `replay_test.py` exercises native input delivery with a recorded report; it deliberately fails all firmware requests, so its success does not imply Steam initialization succeeded.

## Remaining work

Complete initialization with the powered-on controller, capture all requested feature exchanges, and test haptics and Steam Input mappings. Then integrate attachment negotiation and the bounded request/reply protocol into Moonlight/Vibepollo's authenticated connection. That integration must transfer ownership away from local Steam Input during the stream, avoid duplicate Xbox forwarding, and restore local control on disconnect. Multi-controller routing, reconnects and latency need tests before enabling this in an image.
