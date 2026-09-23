// Hardware-independent check of the installed Xbox Series virtual controller.
#include "libvirtualgamepad/client.h"
#include <Xinput.h>
#include <array>
#include <cstdio>
#include <cstring>
#include <hidsdi.h>
#include <set>
#include <setupapi.h>
#include <string>
#include <vector>
#include <windows.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Gaming.Input.h>

static std::set<std::wstring> xbox_paths() {
  std::set<std::wstring> paths;
  GUID guid;
  HidD_GetHidGuid(&guid);
  auto set = SetupDiGetClassDevsW(&guid, nullptr, nullptr,
                                  DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
  if (set == INVALID_HANDLE_VALUE)
    return paths;
  for (DWORD i = 0;; ++i) {
    SP_DEVICE_INTERFACE_DATA item{};
    item.cbSize = sizeof(item);
    if (!SetupDiEnumDeviceInterfaces(set, nullptr, &guid, i, &item))
      break;
    DWORD size = 0;
    SetupDiGetDeviceInterfaceDetailW(set, &item, nullptr, 0, &size, nullptr);
    if (size < sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W))
      continue;
    std::vector<unsigned char> b(size);
    auto d = reinterpret_cast<SP_DEVICE_INTERFACE_DETAIL_DATA_W *>(b.data());
    d->cbSize = sizeof(*d);
    if (!SetupDiGetDeviceInterfaceDetailW(set, &item, d, size, nullptr,
                                          nullptr))
      continue;
    auto h = CreateFileW(d->DevicePath, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
                         nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE)
      continue;
    HIDD_ATTRIBUTES a{};
    a.Size = sizeof(a);
    if (HidD_GetAttributes(h, &a) && a.VendorID == 0x045e &&
        a.ProductID == 0x0b12)
      paths.insert(d->DevicePath);
    CloseHandle(h);
  }
  SetupDiDestroyDeviceInfoList(set);
  return paths;
}
int main(int argc, char **argv) {
  winrt::init_apartment();
  const bool one = argc > 1 && std::strncmp(argv[1], "--one-", 6) == 0;
  const bool native = argc > 1 && (std::strcmp(argv[1], "--wgi") == 0 ||
                                   std::strcmp(argv[1], "--one-wgi") == 0);
  const bool xi = argc > 1 && (std::strcmp(argv[1], "--xinput") == 0 ||
                               std::strcmp(argv[1], "--one-xinput") == 0);
  const bool direct = argc > 1 && !native && !xi;
  const auto before = xbox_paths();

  if (native &&
      winrt::Windows::Gaming::Input::Gamepad::Gamepads().Size() != 0) {
    std::puts("Close streams and disconnect host controllers first");
    return 10;
  }
  if (xi) {
    for (DWORD i = 0; i < 4; ++i) {
      XINPUT_STATE st{};
      if (XInputGetState(i, &st) == ERROR_SUCCESS) {
        std::puts("Existing XInput slot; refusing ambiguous test");
        return 10;
      }
    }
  }
  lvg::client c;
  auto e = c.connect();
  if (e) {
    std::printf("connect error %lu\n", e);
    return 1;
  }
  e = c.create_controller(15, one ? lvg::profile::xbox_one
                                  : lvg::profile::xbox_series);
  if (e) {
    std::printf("create error %lu\n", e);
    return 1;
  }
  std::printf("READY: temporary virtual Xbox %s slot 15\n",
              one ? "One" : "Series");
  std::fflush(stdout);

  HANDLE hid = INVALID_HANDLE_VALUE;
  if (direct) {
    for (unsigned t = 0; t < 100 && hid == INVALID_HANDLE_VALUE; ++t) {
      const auto after = xbox_paths();
      for (const auto &path : after)
        if (!before.count(path)) {
          hid = CreateFileW(path.c_str(), GENERIC_WRITE,
                            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                            OPEN_EXISTING, 0, nullptr);
          break;
        }
      if (hid == INVALID_HANDLE_VALUE)
        Sleep(50);
    }
    if (hid == INVALID_HANDLE_VALUE) {
      std::puts("FAIL: own new HID not found");
      return 5;
    }
  }
  winrt::Windows::Gaming::Input::Gamepad pad{nullptr};
  if (native) {
    WNDCLASSW wc{};
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = GetModuleHandleW(nullptr);
    wc.lpszClassName = L"XboxMotorProbe";
    RegisterClassW(&wc);
    auto window = CreateWindowW(
        wc.lpszClassName, L"Xbox motor API test (closes automatically)",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 500, 180, nullptr,
        nullptr, wc.hInstance, nullptr);
    ShowWindow(window, SW_SHOW);
    SetForegroundWindow(window);
    DWORD foreground = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &foreground);
    std::printf("foreground pid=%lu own pid=%lu\n", foreground,
                GetCurrentProcessId());
    std::fflush(stdout);
    for (unsigned t = 0; t < 100 && !pad; ++t) {
      auto pads = winrt::Windows::Gaming::Input::Gamepad::Gamepads();
      if (pads.Size() == 1)
        pad = pads.GetAt(0);
      else if (pads.Size() > 1) {
        std::puts("FAIL: ambiguous gamepads");
        return 7;
      }
      if (!pad)
        Sleep(50);
    }
    if (!pad) {
      std::puts("FAIL: WGI enumeration");
      return 8;
    }
  }
  DWORD xi_slot = 4;
  if (xi) {
    for (unsigned t = 0; t < 100 && xi_slot == 4; ++t) {
      for (DWORD i = 0; i < 4; ++i) {
        XINPUT_STATE st{};
        if (XInputGetState(i, &st) == ERROR_SUCCESS) {
          xi_slot = i;
          break;
        }
      }
      if (xi_slot == 4)
        Sleep(50);
    }
    if (xi_slot == 4) {
      std::puts("FAIL: no XInput slot");
      return 9;
    }
  }
  if (xi) {
    XINPUT_CAPABILITIES caps{};
    auto caperr = XInputGetCapabilities(xi_slot, 0, &caps);
    std::printf("caps result=%lu type=%u sub=%u flags=%u rumble=%u,%u\n",
                caperr, caps.Type, caps.SubType, caps.Flags,
                caps.Vibration.wLeftMotorSpeed,
                caps.Vibration.wRightMotorSpeed);
  }
  unsigned seen = 0;
  unsigned step = 0;

  for (unsigned n = 0; n < 500; ++n) {
    lvg::input_state_request in{};
    in.header.size = sizeof(in);
    in.header.version = lvg::k_protocol_version;
    in.controller_id = 15;
    if (c.submit_input_state(in))
      return 2;

    if (direct && n % 25 == 0 && step < 4) {
      std::array<unsigned char, 9> report{3, 15, 0, 0, 0, 0, 100, 0, 0};
      constexpr unsigned indexes[] = {4, 5, 2, 3};
      report[indexes[step++]] = 35;
      DWORD written = 0;
      if (!WriteFile(hid, report.data(), static_cast<DWORD>(report.size()),
                     &written, nullptr) ||
          written != report.size()) {
        std::printf("output error %lu\n", GetLastError());
        CloseHandle(hid);
        return 6;
      }
    }
    if (native && n % 25 == 0 && step < 4) {
      winrt::Windows::Gaming::Input::GamepadVibration v{};
      switch (step++) {
      case 0:
        v.LeftMotor = 0.35;
        break;
      case 1:
        v.RightMotor = 0.35;
        break;
      case 2:
        v.LeftTrigger = 0.35;
        break;
      case 3:
        v.RightTrigger = 0.35;
        break;
      }
      pad.Vibration(v);
    }
    if (xi && n % 25 == 0 && step < 2) {
      XINPUT_VIBRATION v{};
      if (step++ == 0)
        v.wLeftMotorSpeed = 22937;
      else
        v.wRightMotorSpeed = 22937;
      std::printf("XInputSetState=%lu\n", XInputSetState(xi_slot, &v));
      std::fflush(stdout);
    }
    lvg::feedback_event f{};
    e = c.poll_feedback(15, &f);
    if (e == ERROR_SUCCESS && f.type == lvg::feedback_type::xbox_rumble &&
        f.payload_size == sizeof(lvg::xbox_rumble_feedback)) {
      lvg::xbox_rumble_feedback r{};
      std::memcpy(&r, f.payload, sizeof(r));
      const unsigned bits =
          (r.low_frequency ? 1 : 0) | (r.high_frequency ? 2 : 0) |
          (r.left_trigger ? 4 : 0) | (r.right_trigger ? 8 : 0);
      if (bits == 1)
        seen |= 1;
      if (bits == 2)
        seen |= 2;
      if (bits == 4)
        seen |= 4;
      if (bits == 8)
        seen |= 8;
      std::printf("feedback grips=%u,%u triggers=%u,%u\n", r.low_frequency,
                  r.high_frequency, r.left_trigger, r.right_trigger);
      std::fflush(stdout);
    } else if (e != ERROR_SUCCESS && e != ERROR_NO_MORE_ITEMS) {
      std::printf("poll error %lu\n", e);
      return 3;
    }
    if (seen == (xi ? 3u : 15u)) {
      std::puts(
          xi ? "PASS: both grip motors reached driver feedback"
             : "PASS: all four motors independently reached driver feedback");
      if (hid != INVALID_HANDLE_VALUE)
        CloseHandle(hid);
      return 0;
    }
    MSG msg;
    while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
      TranslateMessage(&msg);
      DispatchMessageW(&msg);
    }
    Sleep(20);
  }
  std::printf("FAIL: seen mask %u\n", seen);
  if (hid != INVALID_HANDLE_VALUE)
    CloseHandle(hid);
  return 4;
}
