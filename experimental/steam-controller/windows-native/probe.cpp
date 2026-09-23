// SPDX-License-Identifier: MIT
// Windows types must precede the HID SDK headers.
#include <windows.h>

#include <cstdio>
#include <cstring>
#include <cwchar>
#include <hidsdi.h>
#include <setupapi.h>
#include <vector>
int main(int argc, char **argv) {
  const bool rumble = argc == 2 && std::strcmp(argv[1], "--rumble") == 0;
  GUID guid;
  HidD_GetHidGuid(&guid);
  auto set = SetupDiGetClassDevsW(&guid, nullptr, nullptr,
                                  DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
  SP_DEVICE_INTERFACE_DATA d{sizeof(d)};
  HANDLE handle = INVALID_HANDLE_VALUE;
  for (DWORD i = 0; SetupDiEnumDeviceInterfaces(set, nullptr, &guid, i, &d);
       i++) {
    DWORD size = 0;
    SetupDiGetDeviceInterfaceDetailW(set, &d, nullptr, 0, &size, nullptr);
    std::vector<BYTE> b(size);
    auto *p = reinterpret_cast<SP_DEVICE_INTERFACE_DETAIL_DATA_W *>(b.data());
    p->cbSize = sizeof(*p);
    if (!SetupDiGetDeviceInterfaceDetailW(set, &d, p, size, nullptr, nullptr))
      continue;
    auto h = CreateFileW(p->DevicePath, GENERIC_READ | GENERIC_WRITE,
                         FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                         OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
    if (h == INVALID_HANDLE_VALUE)
      continue;
    HIDD_ATTRIBUTES attr{sizeof(attr)};
    if (HidD_GetAttributes(h, &attr) && attr.VendorID == 0x28de &&
        attr.ProductID == 0x1304) {
      handle = h;
      break;
    }
    CloseHandle(h);
  }
  SetupDiDestroyDeviceInfoList(set);
  if (handle == INVALID_HANDLE_VALUE) {
    std::puts("device missing");
    return 1;
  }
  PHIDP_PREPARSED_DATA pp{};
  HIDP_CAPS caps{};
  if (!HidD_GetPreparsedData(handle, &pp) ||
      HidP_GetCaps(pp, &caps) != HIDP_STATUS_SUCCESS)
    return 2;
  HidD_FreePreparsedData(pp);
  std::printf("usage=%04x:%04x input=%u output=%u feature=%u\n", caps.UsagePage,
              caps.Usage, caps.InputReportByteLength,
              caps.OutputReportByteLength, caps.FeatureReportByteLength);
  HANDLE event = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  if (rumble) {
    bool success = true;
    for (unsigned phase = 0; phase < 4; ++phase) {
      unsigned char report[64]{};
      report[0] = 0x80;
      // Left, stop, right, stop. Modest amplitude; finite pulses.
      if (phase == 0) report[5] = 0x18;
      if (phase == 2) report[8] = 0x18;
      OVERLAPPED ov{}; ov.hEvent = event; ResetEvent(event); DWORD written{};
      BOOL ok = WriteFile(handle, report, sizeof(report), &written, &ov);
      if (!ok && GetLastError() == ERROR_IO_PENDING) {
        if (WaitForSingleObject(event, 3000) != WAIT_OBJECT_0) CancelIoEx(handle, &ov);
        ok = GetOverlappedResult(handle, &ov, &written, TRUE);
      }
      success = success && ok && written == sizeof(report);
      Sleep(250);
    }
    CloseHandle(event); CloseHandle(handle);
    std::printf("native rumble writes=%s\n", success ? "passed" : "failed");
    return success ? 0 : 4;
  }
  unsigned count = 0;
  unsigned long long hash = 14695981039346656037ull;
  for (unsigned i = 0; i < 20; i++) {
    unsigned char b[64]{};
    OVERLAPPED ov{};
    ov.hEvent = event;
    ResetEvent(event);
    DWORD got{};
    BOOL ok = ReadFile(handle, b, caps.InputReportByteLength, &got, &ov);
    if (!ok && GetLastError() == ERROR_IO_PENDING) {
      if (WaitForSingleObject(event, 3000) != WAIT_OBJECT_0) {
        CancelIoEx(handle, &ov);
        GetOverlappedResult(handle, &ov, &got, TRUE);
        break;
      }
      ok = GetOverlappedResult(handle, &ov, &got, FALSE);
    }
    if (!ok)
      break;
    for (DWORD j = 0; j < got; j++) {
      hash ^= b[j];
      hash *= 1099511628211ull;
    }
    count++;
  }
  CloseHandle(event);
  CloseHandle(handle);
  std::printf("reports=%u fnv=%016llx\n", count, hash);
  return count == 20 ? 0 : 3;
}
