// Cross-check our decoder against Valve's published packed structures.
#include <cassert>
#include <cstdint>
#include <cstring>
using Uint32 = std::uint32_t;
using Uint64 = std::uint64_t;
#include "steam/controller_constants.h"
#include "steam/controller_structs.h"
#pragma pack()
#include "triton.hpp"
int main() {
  static_assert(sizeof(TritonMTUNoQuat_t) == 45);
  static_assert(sizeof(TritonMTUFull_t) == 53);
  static_assert(sizeof(TritonMTUNoQuat32TS_t) == 45);
  TritonMTUFull_t v{};
  v.seq_num = 17;
  v.buttons = 0x30000181;
  v.sLeftStickX = -1234;
  v.sLeftPadY = -1500;
  v.unPressureRight = 123;
  v.imu.timestamp = 123456;
  v.imu.sAccelY = -25;
  v.imu.sGyroZ = 32767;
  v.imu.sGyroQuatW = -123;
  std::array<std::uint8_t, 54> raw{};
  raw[0] = ID_TRITON_CONTROLLER_STATE;
  std::memcpy(raw.data() + 1, &v, sizeof(v));
  auto s = triton::decode(raw);
  assert(s && s->sequence == v.seq_num && s->buttons == v.buttons);
  assert(s->sticks[0] == v.sLeftStickX && s->pads[1] == v.sLeftPadY &&
         s->pressure[1] == v.unPressureRight);
  assert(s->imu_timestamp == v.imu.timestamp && s->accel[1] == v.imu.sAccelY &&
         s->gyro[2] == v.imu.sGyroZ &&
         s->quaternion->at(0) == v.imu.sGyroQuatW);
  auto out = triton::rumble(123, 456);
  OutputReportMsg m{};
  m.report_id = ID_OUT_REPORT_HAPTIC_RUMBLE;
  m.payload.hapticRumble.left.speed = 123;
  m.payload.hapticRumble.right.speed = 456;
  assert(std::memcmp(out.data(), &m, out.size()) == 0);
}
