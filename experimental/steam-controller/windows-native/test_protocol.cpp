// SPDX-License-Identifier: MIT
#include "descriptor.h"
#include "protocol.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>
using namespace steam_native;
int main() {
  assert(input_size(0x42) == 54 && input_size(0x45) == 46);
  for (unsigned i = 0; i < 256; i++)
    assert(input_size(i) <= 64);
  for (unsigned id = 0; id < 256; id++)
    for (unsigned command = 0; command < 256; command++) {
      assert(!safe_feature(id, command, 62));
      if (id != 1 && !(id == 2 && command == 0xa3))
        assert(!safe_feature(id, command, 0));
    }
  for (auto command : {0x86, 0xa7, 0xa9, 0xad, 0xaf, 0xb0, 0xb1, 0xb2, 0xb3,
                       0xb5, 0xbf, 0xc0, 0xc3})
    assert(!safe_feature(1, command, 0));
  assert(safe_feature(2, 0xa3, 0) && !safe_feature(2, 0xa3, 1));
  assert(safe_feature(1, 0x83, 0) && safe_feature(1, 0x87, 3));
  assert(!output_size(0x86) && output_size(0x80) == 10);
  unsigned current = 0, count = 0, size = 0;
  unsigned lengths[3][256]{};
  for (unsigned i = 0; i < sizeof(descriptor);) {
    auto prefix = descriptor[i++];
    assert(prefix != 0xfe);
    unsigned n = prefix & 3;
    if (n == 3)
      n = 4;
    unsigned value = 0;
    for (unsigned j = 0; j < n; j++) {
      assert(i < sizeof(descriptor));
      value |= descriptor[i++] << (j * 8);
    }
    switch (prefix & 0xfc) {
    case 0x84:
      current = value;
      break;
    case 0x94:
      count = value;
      break;
    case 0x74:
      size = value;
      break;
    case 0x80:
      lengths[0][current] += count * size;
      break;
    case 0x90:
      lengths[1][current] += count * size;
      break;
    case 0xb0:
      lengths[2][current] += count * size;
      break;
    }
  }
  for (unsigned i = 0; i < 256; i++) {
    if (lengths[0][i])
      assert(input_size(i) == lengths[0][i] / 8 + 1);
    if (output_size(i))
      assert(output_size(i) == lengths[1][i] / 8 + 1);
  }
  assert(lengths[2][1] == 504 && lengths[2][2] == 504);
  std::puts("Steam HID descriptor and command-policy checks passed");
}
