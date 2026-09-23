# SPDX-License-Identifier: MIT
import unittest
from imu_clock import ImuClock

def report(t, kind=0x42):
    b = bytearray(range(54 if kind == 0x42 else 46))
    b[0] = kind
    b[30:34] = t.to_bytes(4, 'little')
    return bytes(b)

def stamp(b):
    return int.from_bytes(b[30:34], 'little')

class ClockTests(unittest.TestCase):
    def test_repeated_sample_keeps_buttons_and_every_other_byte(self):
        c = ImuClock()
        self.assertEqual(c.normalize(report(4000)), report(4000))
        b = bytearray(report(4000)); b[2] ^= 1
        fixed = c.normalize(bytes(b))
        self.assertEqual(stamp(fixed), 4001)
        self.assertEqual(fixed[:30] + fixed[34:], bytes(b[:30] + b[34:]))
        self.assertEqual(stamp(c.normalize(report(4000))), 4002)
        self.assertEqual(c.normalize(report(8166)), report(8166))

    def test_wrap_and_real_reset(self):
        c = ImuClock()
        self.assertEqual(stamp(c.normalize(report(0xffffffff))), 0xffffffff)
        self.assertEqual(stamp(c.normalize(report(0xffffffff))), 0)
        self.assertEqual(stamp(c.normalize(report(0))), 1)
        self.assertEqual(stamp(c.normalize(report(4000))), 4000)
        self.assertEqual(stamp(c.normalize(report(10))), 10)

    def test_compact_and_unrelated_reports(self):
        c = ImuClock()
        c.normalize(report(42, 0x45))
        self.assertEqual(stamp(c.normalize(report(42, 0x45))), 43)
        for b in (b'', b'\x43hello', report(42)[:-1]):
            self.assertEqual(c.normalize(b), b)

    def test_adjustment_is_bounded(self):
        c = ImuClock()
        for i in range(1100):
            self.assertLessEqual(stamp(c.normalize(report(1000))) - 1000, 1000)

if __name__ == '__main__':
    unittest.main()
