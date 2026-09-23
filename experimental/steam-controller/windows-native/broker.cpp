// SPDX-License-Identifier: MIT
#include "protocol.h"
#include <atomic>
#include <devguid.h>
#include <iomanip>
#include <iostream>
#include <newdev.h>
#include <setupapi.h>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
using namespace steam_native;
static constexpr GUID system_class{
    0x4d36e97d,
    0xe325,
    0x11ce,
    {0xbf, 0xc1, 0x08, 0x00, 0x2b, 0xe1, 0x03, 0x18}};
int install(const wchar_t *path) {
  auto set =
      SetupDiGetClassDevsW(&system_class, nullptr, nullptr, DIGCF_PRESENT);
  SP_DEVINFO_DATA d{sizeof(d)};
  bool exists = false;
  for (DWORD i = 0; SetupDiEnumDeviceInfo(set, i, &d); ++i) {
    wchar_t ids[1024]{};
    if (SetupDiGetDeviceRegistryPropertyW(set, &d, SPDRP_HARDWAREID, nullptr,
                                          reinterpret_cast<PBYTE>(ids),
                                          sizeof(ids), nullptr) &&
        _wcsicmp(ids, root_id) == 0) {
      exists = true;
      break;
    }
  }
  SetupDiDestroyDeviceInfoList(set);
  if (!exists) {
    set = SetupDiCreateDeviceInfoList(&system_class, nullptr);
    d = {sizeof(d)};
    if (!SetupDiCreateDeviceInfoW(set, L"MoonmachineSteamHid", &system_class,
                                  L"Moonmachine Experimental Steam HID",
                                  nullptr, DICD_GENERATE_ID, &d))
      return 1;
    const wchar_t ids[] = L"ROOT\\MOONMACHINESTEAMHID\0";
    if (!SetupDiSetDeviceRegistryPropertyW(set, &d, SPDRP_HARDWAREID,
                                           reinterpret_cast<const BYTE *>(ids),
                                           sizeof(ids)) ||
        !SetupDiCallClassInstaller(DIF_REGISTERDEVICE, set, &d)) {
      std::cerr << "register " << GetLastError() << '\n';
      return 1;
    }
    SetupDiDestroyDeviceInfoList(set);
  }
  BOOL reboot{};
  if (!UpdateDriverForPlugAndPlayDevicesW(nullptr, root_id, path,
                                          INSTALLFLAG_FORCE, &reboot)) {
    std::cerr << "install " << GetLastError() << '\n';
    return 1;
  }
  std::cout << "installed reboot=" << reboot << '\n';
  return 0;
}
HANDLE open_control() {
  auto set = SetupDiGetClassDevsW(&interface_id, nullptr, nullptr,
                                  DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
  SP_DEVICE_INTERFACE_DATA d{sizeof(d)};
  HANDLE h = INVALID_HANDLE_VALUE;
  if (SetupDiEnumDeviceInterfaces(set, nullptr, &interface_id, 0, &d)) {
    DWORD size{};
    SetupDiGetDeviceInterfaceDetailW(set, &d, nullptr, 0, &size, nullptr);
    std::vector<BYTE> b(size);
    auto *p = reinterpret_cast<SP_DEVICE_INTERFACE_DETAIL_DATA_W *>(b.data());
    p->cbSize = sizeof(*p);
    if (SetupDiGetDeviceInterfaceDetailW(set, &d, p, size, nullptr, nullptr))
      h = CreateFileW(p->DevicePath, GENERIC_READ | GENERIC_WRITE,
                      FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                      OPEN_EXISTING, 0, nullptr);
  }
  SetupDiDestroyDeviceInfoList(set);
  return h;
}
bool call(HANDLE h, DWORD code, void *in, DWORD n, void *out, DWORD m) {
  DWORD got{};
  return DeviceIoControl(h, code, in, n, out, m, &got, nullptr) != 0;
}
bool unhex(const std::string &s, std::uint8_t *b, unsigned &n) {
  if (s.size() % 2 || s.size() > 128)
    return false;
  n = static_cast<unsigned>(s.size() / 2);
  for (unsigned i = 0; i < n; i++) {
    auto digit = [](char c) {
      if (c >= '0' && c <= '9')
        return c - '0';
      if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
      return -1;
    };
    int a = digit(s[2 * i]), v = digit(s[2 * i + 1]);
    if (a < 0 || v < 0)
      return false;
    b[i] = static_cast<std::uint8_t>(a * 16 + v);
  }
  return true;
}
int wmain(int argc, wchar_t **argv) {
  if (argc == 3 && wcscmp(argv[1], L"install") == 0)
    return install(argv[2]);
  auto h = open_control();
  if (h == INVALID_HANDLE_VALUE) {
    std::cerr << "open " << GetLastError() << '\n';
    return 1;
  }
  if (!call(h, start, nullptr, 0, nullptr, 0)) {
    std::cerr << "start " << GetLastError() << '\n';
    CloseHandle(h);
    return 2;
  }
  std::cerr << "virtual Steam HID started\n";
  std::atomic_bool done = false;
  std::thread poller([&] {
    while (!done) {
      packet p{};
      if (call(h, poll, nullptr, 0, &p, sizeof(p))) {
        std::cout << "Q " << p.id << ' ' << static_cast<unsigned>(p.op) << ' ';
        for (unsigned i = 0; i < p.size; i++)
          std::cout << std::hex << std::setfill('0') << std::setw(2)
                    << static_cast<unsigned>(p.data[i]);
        std::cout << std::dec << std::endl;
      } else {
        const auto e = GetLastError();
        if (e != ERROR_NO_MORE_ITEMS && e != ERROR_NO_MORE_FILES) {
          std::cerr << "poll " << e << '\n';
          break;
        }
        Sleep(1);
      }
    }
  });
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    char command{};
    in >> command;
    std::string hex;
    bool ok = false;
    if (command == 'I') {
      packet p{};
      in >> hex;
      if (unhex(hex, p.data, p.size))
        ok = call(h, input, &p, sizeof(p), nullptr, 0);
    }
    if (command == 'R') {
      response r{};
      in >> r.id >> r.status >> hex;
      if (hex == "-")
        hex.clear();
      if (unhex(hex, r.data, r.size))
        ok = call(h, reply, &r, sizeof(r), nullptr, 0);
    }
    if (command == 'X')
      break;
    if (!ok)
      std::cerr << "request failed " << GetLastError() << '\n';
  }
  done = true;
  poller.join();
  call(h, stop, nullptr, 0, nullptr, 0);
  CloseHandle(h);
  return 0;
}
