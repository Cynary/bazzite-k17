#include "triton.hpp"
#include <cassert>
#include <iostream>
#include <random>
int main() {
  std::array<std::uint8_t, 54> r{};
  r[0] = 0x42;
  r[1] = 255;
  // Independent golden offsets: all button bits; signed stick/pad extrema;
  // pressures; IMU counters, accelerometer, gyro and quaternion.
  r[2] = 0x81;
  r[5] = 0x30;
  r[6] = 0xff;
  r[7] = 0x7f;
  r[11] = 0x80;
  r[12] = 0xff;
  r[13] = 0x7f;
  r[19] = 0x80;
  r[22] = 0x34;
  r[23] = 0x12;
  r[28] = 0x78;
  r[29] = 0x56;
  r[30] = 0x78;
  r[31] = 0x56;
  r[32] = 0x34;
  r[33] = 0x12;
  r[34] = 0xff;
  r[35] = 0xff;
  r[40] = 42;
  r[46] = 9;
  auto s = triton::decode(r);
  assert(s && s->sequence == 255 && s->buttons == 0x30000081 &&
         s->triggers[0] == 32767);
  assert(s->sticks[0] == -32768 && s->sticks[1] == 32767 &&
         s->pads[0] == -32768);
  assert(s->pressure[0] == 0x1234 && s->pressure[1] == 0x5678 &&
         s->imu_timestamp == 0x12345678);
  assert(s->accel[0] == -1 && s->gyro[0] == 42 && s->quaternion->at(0) == 9);
  for (unsigned n = 0; n < 46; ++n)
    assert(!triton::decode(triton::bytes(r.data(), n)));
  r[0] = 0x45;
  assert(!triton::decode(r)->quaternion);
  r[0] = 0x47;
  r[18] = 7;
  r[19] = 0;
  r[32] = 0xff;
  r[33] = 0xff;
  s = triton::decode(r);
  assert(s && s->timestamp_32us && s->pad_timestamp == 7 &&
         s->imu_timestamp == 65535 && s->accel[0] == -1);
  triton::packet p{};
  p.kind = 1;
  p.slot = 15;
  p.sequence = 0xffffffff;
  p.size = 54;
  std::copy(r.begin(), r.end(), p.report.begin());
  std::array<std::uint8_t, 74> wire{};
  auto len = triton::pack(p, wire);
  assert(len && *len == 64);
  auto q = triton::unpack(triton::bytes(wire.data(), *len));
  assert(q && q->sequence == p.sequence && q->report == p.report);
  for (unsigned n = 0; n < *len; ++n)
    assert(!triton::unpack(triton::bytes(wire.data(), n)));
  wire[0] = 2;
  assert(!triton::unpack(triton::bytes(wire.data(), *len)));
  wire[0] = 1;
  wire[2] = 16;
  assert(!triton::unpack(triton::bytes(wire.data(), *len)));
  wire[2] = 15;
  wire[3] = 1;
  assert(!triton::unpack(triton::bytes(wire.data(), *len)));
  wire[3] = 0;
  auto h = triton::rumble(0x1234, 0xabcd);
  assert(h[4] == 0x34 && h[5] == 0x12 && h[7] == 0xcd && h[8] == 0xab &&
         triton::valid_output(h));
  std::array<std::uint8_t, 64> padded{};
  std::copy(h.begin(), h.end(), padded.begin());
  assert(triton::valid_output(padded));
  padded[63] = 1;
  assert(!triton::valid_output(padded));
  h[0] = 0x87;
  assert(!triton::valid_output(h));
  triton::sequence_gate gate;
  assert(gate.accept(0xfffffffe));
  assert(gate.accept(0));
  assert(!gate.accept(0xffffffff));
  assert(!gate.accept(0));
  assert(gate.accept(1));
  // Malformed lengths, flags, IDs and byte values under ASan/UBSan.
  std::mt19937 rng(17);
  std::array<std::uint8_t, 100> noise{};
  for (unsigned i = 0; i < 100000; ++i) {
    for (auto &v : noise)
      v = std::uint8_t(rng());
    auto n = rng() % 101;
    (void)triton::decode({noise.data(), n});
    (void)triton::unpack({noise.data(), n});
  }
  std::cout << "PASS: native fields, haptics, transport bounds, sequence wrap "
               "and 100000 malformed packets\n";
}
