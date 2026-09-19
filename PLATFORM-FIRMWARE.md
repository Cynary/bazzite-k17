# K17 platform firmware and wireless checks — 2026-09-19

## BIOS

Installed AMI BIOS: `Nucbox_K17_V1.01`, dated 2026-03-03; firmware revision 5.32, EC 1.2.
The official GMKtec download catalog lists K17 Windows drivers but no newer K17 BIOS was found. After refreshing LVFS metadata, fwupd offered only a Secure Boot dbx update, not a K17 BIOS. No firmware was flashed.

The machine exposes UEFI capsule devices. This may permit a vendor-supplied compatible capsule to be installed from Linux; detection alone does not establish that an arbitrary vendor BIOS archive is usable. Obtain the exact K17/226V package and its instructions first. A UEFI-shell updater would not require Windows; a Windows-only updater needs its supported Windows environment, not an assumed-compatible WinPE/Hiren environment.

Existing ACPI errors reference missing TPD0 and IETM thermal-policy objects. Their full functional impact has not been established; do not disable ACPI/thermal management to hide them.

Source: https://www.gmktec.com/pages/drivers-and-software

## MT7922 Wi-Fi

PCI 14c3:0616 uses mt7921e/mt7921-common. Firmware build 20260724143402 introduces CLC records with index 3 while this kernel stores only three CLC pointers. The original loader indexed the array before validating the index, triggering UBSAN during initialization.

Backported two upstream changes, in order, preserving their authorship in wifi-patches:

- 9417c5818a01: validate CLC firmware records (length and index checks).
- 1a296bfd3e775e515233f746218824fc7dd5ff16: skip unknown CLC firmware records rather than reject valid newer firmware.

The second patch is essential: the first alone would reject the installed firmware. Firmware itself was not changed. CLC regulatory handling is retained; bounds instrumentation is not disabled.

Built mt7921-common against the exact installed kernel-devel and symbol versions. Repeated initialization and Wi-Fi scanning succeeded without new UBSAN reports. One reboot also passed: k17-wifi.service active, 53 scan results, no boot-time UBSAN report and no failed systemd units. No saved Wi-Fi credentials exist on the test machine, so association and throughput have not been tested.

The image recipe installs the replacement via updates/k17 and includes it in initramfs. Until that image is built/deployed, the test machine uses a kernel-version-guarded modprobe loader in /usr/local/sbin/k17-wifi-load, module in /var/lib/k17-wifi, and k17-wifi.service. The module has a persistent modules_object_t SELinux file-context rule; enforcement remains enabled. Remove /etc/modprobe.d/99-k17-wifi.conf and disable/remove k17-wifi.service when transitioning to the image-integrated module. The loader falls back to stock on other kernel versions.

Upstream discussion: https://lists.openwall.net/linux-kernel/2026/09/14/334

## Bluetooth warning

USB 0e8d:0616 initializes successfully and bluetoothctl reports powered on. The message about Enhanced Setup Synchronous Connection comes from HCI_QUIRK_BROKEN_ENHANCED_SETUP_SYNC_CONN, deliberately set for MediaTek in btusb.c. It disables one command used to establish SCO audio links; it does not impose a generic bandwidth or controller-count cap. Normal connection handling can use the older command path. Actual Bluetooth headset and gamepad functionality has not been tested here.

MediaTek's own MT7922 device-support submission includes the identical warning alongside successful pairing:
https://lists.infradead.org/pipermail/linux-mediatek/2025-February/088979.html

The AOSP quality-report warning concerns optional Android telemetry support, not controller input functionality. Neither workaround was removed.
