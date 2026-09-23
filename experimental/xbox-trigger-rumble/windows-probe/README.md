# Windows four-motor probe

This probe creates a temporary virtual Xbox controller through the installed libvirtualgamepad driver. It does not forward anything to a physical controller. The control connection owns the virtual device; exiting releases it.

Place a checkout of Nonary/libvirtualgamepad in `libvirtualgamepad/` beside `probe.cpp`, then run `build.cmd` from Windows with Visual Studio C++ build tools and the Windows SDK installed. Tested source revision: `4b56fb9da177f320fb2d7ddb1b6262e5d55d2750`.

Modes:

- `probe.exe --hid`: sends four individual motor commands through WriteFile on the newly enumerated Xbox HID device, then checks driver feedback.
- `probe.exe --wgi`: uses Windows.Gaming.Input, the API that includes trigger vibration.
- `probe.exe --xinput`: tests ordinary two-motor XInput vibration.
- `--one-wgi` and `--one-xinput`: repeat using the Xbox One profile.

Close streams and disconnect other host gamepads first. These tests temporarily create a controller and the WGI test opens a window. They finish automatically. They are diagnostics, not a new streaming service.

## Results on September 23

Host: Windows build 26220.9492, signed Vibepollo 2.0.0-beta.3 package, driver source revision `0b3970e1a8c839f14f20a7c8eaf48ff59b8c1986`, protocol 2.

- Direct HID WriteFile: **passed** all four channels, each at 35% strength; feedback magnitude 22937/65535.
- Windows.Gaming.Input: controller enumerated, but no nonzero motor feedback arrived.
- XInput: controller enumerated, both rumble capabilities reported 65535, and SetState returned success; no nonzero feedback arrived.
- The game-API failure also occurred with Steam closed and with the Xbox One profile. A WGI test in the interactive desktop with its own foreground window also failed.
- HidD_SetOutputReport returned error 50. The driver’s PROFILE_CONTRACT.md documents that its supported output path is WriteFile, not that control-transfer API. This may be relevant, but we have not traced the internal Windows API path and have not established it as the cause of the WGI/XInput failure.

Consequently the host was returned to automatic selection, which prefers the existing ViGEm backend. The new signed driver remains installed for diagnosis. The beta installation preserved the app list and pairing-state file; the previous application directory was backed up. No end-to-end trigger-rumble success is claimed.

Next: trace which output requests the Windows game APIs issue and compare them with a physical Xbox controller. Do not treat a successful direct HID write as proof that games can generate the same feedback.
