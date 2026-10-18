import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / 'files/usr/libexec/moonmachine-usb-health.py'
if not source.exists():
    source = Path('/usr/libexec/moonmachine-usb-health.py')
spec = importlib.util.spec_from_file_location('health', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PolicyTests(unittest.TestCase):
    def test_healthy_never_recovers(self):
        state = {}
        for now in (0, 15, 30, 90):
            self.assertEqual(module.plan(state, [], now), [])

    def test_boot_enumeration_gets_time_to_settle(self):
        state = {}
        self.assertEqual(module.plan(state, ['unconfigured:vader'], 20), [])
        self.assertEqual(module.plan(state, [], 35), [])

    def test_two_separated_observations_required(self):
        state = {}
        for now in (0, 0.1, 14):
            self.assertEqual(module.plan(state, ['unconfigured:vader'], now), [])
        self.assertEqual(module.plan(state, ['unconfigured:vader'], 15), ['unconfigured:vader'])

    def test_transient_fault_does_not_count_as_persistent(self):
        state = {}
        module.plan(state, ['vader'], 0)
        module.plan(state, [], 15)
        self.assertEqual(module.plan(state, ['vader'], 50), [])
        self.assertEqual(module.plan(state, ['vader'], 51), [])
        self.assertEqual(module.plan(state, ['vader'], 65), ['vader'])

    def test_failed_recovery_does_not_loop(self):
        state = {}
        module.plan(state, ['puck'], 0)
        self.assertEqual(module.plan(state, ['puck'], 15), ['puck'])
        for now in (30, 60, 120, 600):
            self.assertEqual(module.plan(state, ['puck'], now), [])

    def test_new_failure_not_hidden_by_old_failed_puck(self):
        state = {}
        module.plan(state, ['puck'], 0)
        module.plan(state, ['puck'], 15)
        self.assertEqual(module.plan(state, ['puck', 'vader'], 80), [])
        self.assertEqual(module.plan(state, ['puck', 'vader'], 95), ['vader'])
        self.assertEqual(module.plan(state, ['puck'], 120), [])

    def test_minute_between_different_recoveries(self):
        state = {}
        module.plan(state, ['puck'], 0)
        module.plan(state, ['puck'], 15)
        module.plan(state, ['puck', 'vader'], 20)
        self.assertEqual(module.plan(state, ['puck', 'vader'], 40), [])
        self.assertEqual(module.plan(state, ['puck', 'vader'], 75), ['vader'])

    def test_reenumeration_gap_does_not_rearm(self):
        state = {}
        module.plan(state, ['puck'], 0)
        module.plan(state, ['puck'], 15)
        for now in (16, 17, 18):
            module.plan(state, [], now)
        self.assertEqual(module.plan(state, ['puck'], 60), [])

    def test_recovered_device_can_recover_again_with_other_fault_persistent(self):
        state = {}
        module.plan(state, ['puck', 'vader'], 0)
        module.plan(state, ['puck', 'vader'], 15)
        for now in (45, 60, 75):
            module.plan(state, ['puck'], now)
        self.assertNotIn('vader', state['faults'])
        module.plan(state, ['puck', 'vader'], 90)
        self.assertEqual(module.plan(state, ['puck', 'vader'], 105), ['vader'])

    def test_attempt_recorded_before_recovery(self):
        state = {}
        module.plan(state, ['puck'], 0)
        module.plan(state, ['puck'], 15)
        self.assertTrue(state['faults']['puck']['attempted'])
        self.assertEqual(state['last_attempt'], 15)

    def test_previously_attempted_fault_can_be_seeded_without_reset(self):
        state = {'faults': {'puck': {'since': 0, 'samples': 2, 'attempted': True}}}
        self.assertEqual(module.plan(state, ['puck'], 100), [])


if __name__ == '__main__':
    unittest.main()
