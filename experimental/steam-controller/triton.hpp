// SPDX-License-Identifier: MIT
// Experimental report bridge. Wire layouts follow Valve's public SDL headers;
// see README for pinned sources. This is not a registered Windows HID profile.
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
namespace triton {
using bytes = std::span<const std::uint8_t>;
inline std::uint16_t u16(bytes b, unsigned o) {
  return std::uint16_t(b[o] | unsigned(b[o + 1]) << 8);
}
inline std::uint32_t u32(bytes b, unsigned o) {
  return u16(b, o) | std::uint32_t(u16(b, o + 2)) << 16;
}
inline std::int16_t i16(bytes b, unsigned o) {
  auto v = u16(b, o);
  return static_cast<std::int16_t>(v < 32768 ? v : int(v) - 65536);
}
struct state {
  std::uint8_t report_id{}, sequence{};
  std::uint32_t buttons{};
  std::array<std::int16_t, 2> triggers{};
  std::array<std::int16_t, 4> sticks{};
  std::array<std::int16_t, 4> pads{};
  std::array<std::uint16_t, 2> pressure{};
  std::uint32_t imu_timestamp{};
  std::uint16_t pad_timestamp{};
  bool timestamp_32us{};
  std::array<std::int16_t, 3> accel{}, gyro{};
  std::optional<std::array<std::int16_t, 4>> quaternion;
};
inline std::optional<state> decode(bytes b) {
  if (b.empty() || b.size() > 64)
    return {};
  const auto id = b[0];
  if (id != 0x42 && id != 0x45 && id != 0x47)
    return {};
  if (b.size() < 46)
    return {};
  state s{};
  s.report_id = id;
  s.sequence = b[1];
  s.buttons = u32(b, 2);
  for (unsigned i = 0; i < 2; ++i)
    s.triggers[i] = i16(b, 6 + i * 2);
  for (unsigned i = 0; i < 4; ++i)
    s.sticks[i] = i16(b, 10 + i * 2);
  unsigned p = 18;
  if (id == 0x47) {
    s.timestamp_32us = true;
    s.pad_timestamp = u16(b, p);
    p += 2;
  }
  for (unsigned i = 0; i < 2; ++i) {
    s.pads[i * 2] = i16(b, p);
    s.pads[i * 2 + 1] = i16(b, p + 2);
    s.pressure[i] = u16(b, p + 4);
    p += 6;
  }
  if (id == 0x47) {
    s.imu_timestamp = u16(b, p);
    p += 2;
  } else {
    s.imu_timestamp = u32(b, p);
    p += 4;
  }
  for (unsigned i = 0; i < 3; ++i)
    s.accel[i] = i16(b, p + i * 2);
  p += 6;
  for (unsigned i = 0; i < 3; ++i)
    s.gyro[i] = i16(b, p + i * 2);
  // Report 0x42's full form has quaternion data. BLE padding is not quaternion.
  if (id == 0x42 && b.size() >= 54) {
    std::array<std::int16_t, 4> q{};
    for (unsigned i = 0; i < 4; ++i)
      q[i] = i16(b, 46 + i * 2);
    s.quaternion = q;
  }
  return s;
}
inline unsigned output_size(std::uint8_t id) {
  switch (id) {
  case 0x80:
    return 10;
  case 0x81:
    return 8;
  case 0x82:
    return 4;
  case 0x83:
    return 10;
  case 0x84:
    return 9;
  case 0x85:
    return 4;
  default:
    return 0;
  }
}
// Only documented haptic outputs are accepted. Settings/firmware commands are
// deliberately excluded until a separate feature-request protocol is
// implemented.
inline bool valid_output(bytes b) {
  if (b.empty())
    return false;
  const unsigned n = output_size(b[0]);
  if (!n)
    return false;
  if (b.size() == n)
    return true;
  // Windows HID writes may use the descriptor's maximum output-report length.
  return b.size() == 64 &&
         std::all_of(b.begin() + n, b.end(), [](auto v) { return v == 0; });
}
inline std::array<std::uint8_t, 10> rumble(std::uint16_t left,
                                           std::uint16_t right) {
  return {0x80,
          0,
          0,
          0,
          std::uint8_t(left),
          std::uint8_t(left >> 8),
          0,
          std::uint8_t(right),
          std::uint8_t(right >> 8),
          0};
}
// Private experimental payload intended INSIDE an authenticated streaming
// connection. Not a standalone network protocol or a public Moonlight packet
// ID. Version, kind, controller slot, reserved, sequence (LE32), length (LE16),
// raw HID. Keep raw reports: normalizing to Xbox loses pad pressure, grip
// sensors and more.
struct packet {
  std::uint8_t kind{}, slot{};
  std::uint32_t sequence{};
  std::array<std::uint8_t, 64> report{};
  std::uint16_t size{};
};
inline bool valid_report(std::uint8_t kind, bytes b) {
  return kind == 1 ? decode(b).has_value() : kind == 2 && valid_output(b);
}
inline std::optional<packet> unpack(bytes b) {
  if (b.size() < 10 || b[0] != 1 || b[1] < 1 || b[1] > 2 || b[2] >= 16 || b[3])
    return {};
  auto n = u16(b, 8);
  if (n > 64 || b.size() != 10u + n || !valid_report(b[1], b.subspan(10)))
    return {};
  packet p{};
  p.kind = b[1];
  p.slot = b[2];
  p.sequence = u32(b, 4);
  p.size = n;
  std::copy(b.begin() + 10, b.end(), p.report.begin());
  return p;
}
inline std::optional<unsigned> pack(const packet &p,
                                    std::span<std::uint8_t> out) {
  if (p.size > 64 || p.slot >= 16 || out.size() < 10u + p.size ||
      !valid_report(p.kind, bytes(p.report.data(), p.size)))
    return {};
  out[0] = 1;
  out[1] = p.kind;
  out[2] = p.slot;
  out[3] = 0;
  for (unsigned i = 0; i < 4; ++i)
    out[4 + i] = std::uint8_t(p.sequence >> (8 * i));
  out[8] = std::uint8_t(p.size);
  out[9] = 0;
  std::copy_n(p.report.begin(), p.size, out.begin() + 10);
  return 10u + p.size;
}
// Instantiate per controller, direction and authenticated session. Never reuse
// across reconnects. Half-range serial arithmetic permits uint32 wraparound.
class sequence_gate {
  bool seen = false;
  std::uint32_t last = 0;

public:
  bool accept(std::uint32_t n) {
    const auto d = n - last;
    if (seen && (d == 0 || d >= 0x80000000u))
      return false;
    seen = true;
    last = n;
    return true;
  }
};
} // namespace triton
