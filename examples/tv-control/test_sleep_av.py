"""Regression checks for the condition that authorizes two-device standby."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import sleep_av


class SleepGuardTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, tv_inputs, avr_inputs, *, check_only=False,
                       tv_failure=None, avr_failure=None):
        inputs = iter(tv_inputs)
        current = [None]
        commands = []

        async def request(uri):
            if uri.endswith("getPowerState"):
                current[0] = next(inputs)
                if isinstance(current[0], Exception):
                    raise current[0]
                return {"state": "Active"}
            if uri.endswith("getForegroundAppInfo"):
                return {"appId": current[0]}
            commands.append(("tv", uri))
            if tv_failure:
                raise tv_failure
            return {"returnValue": True}

        async def command(session, value):
            commands.append(("avr", value))
            if avr_failure:
                raise avr_failure

        tv = AsyncMock()
        tv.request.side_effect = request
        with patch.object(sleep_av, "avr_state", AsyncMock(side_effect=avr_inputs)), \
             patch.object(sleep_av, "avr_command", command), \
             patch.object(sleep_av, "log"):
            try:
                result = await sleep_av.guarded_off(tv, object(), check_only)
            except Exception:
                self.assertEqual(commands, [], "A failed input read must not send standby")
                raise
        return result, commands

    async def test_both_match(self):
        result, commands = await self.exercise(
            ["com.webos.app.hdmi2"] * 2, [("ON", "AUX2")] * 2)
        self.assertTrue(result)
        self.assertCountEqual(commands, [("tv", "system/turnOff"), ("avr", "PWSTANDBY")])

    async def test_either_mismatch_or_unknown_does_nothing(self):
        for app, avr in [
            ("com.webos.app.hdmi1", ("ON", "AUX2")),
            ("com.webos.app.hdmi2", ("ON", "GAME")),
            ("com.webos.app.netflix", ("ON", "AUX2")),
            (None, ("ON", "AUX2")),
            ("com.webos.app.hdmi2", (None, None)),
            ("com.webos.app.hdmi2", ("STANDBY", "AUX2")),
        ]:
            with self.subTest(app=app, avr=avr):
                result, commands = await self.exercise([app], [avr])
                self.assertFalse(result)
                self.assertEqual(commands, [])

    async def test_input_changes_during_check(self):
        for apps, avrs in [
            (["com.webos.app.hdmi2", "com.webos.app.hdmi1"], [("ON", "AUX2")] * 2),
            (["com.webos.app.hdmi2"] * 2, [("ON", "AUX2"), ("ON", "GAME")]),
        ]:
            result, commands = await self.exercise(apps, avrs)
            self.assertFalse(result)
            self.assertEqual(commands, [])

    async def test_read_errors_do_not_send_either_command(self):
        with self.assertRaises(TimeoutError):
            await self.exercise([TimeoutError()], [("ON", "AUX2")])
        with self.assertRaises(OSError):
            await self.exercise(["com.webos.app.hdmi2"], [OSError("unreachable")])

    async def test_check_only(self):
        result, commands = await self.exercise(
            ["com.webos.app.hdmi2"] * 2, [("ON", "AUX2")] * 2, check_only=True)
        self.assertTrue(result)
        self.assertEqual(commands, [])

    async def test_one_poweroff_error_does_not_prevent_other_command(self):
        for failures in [{"tv_failure": ConnectionResetError()}, {"avr_failure": TimeoutError()}]:
            result, commands = await self.exercise(
                ["com.webos.app.hdmi2"] * 2, [("ON", "AUX2")] * 2, **failures)
            self.assertFalse(result)
            self.assertEqual(len(commands), 2)

    async def test_run_deadline_cancels_an_unresponsive_connection(self):
        tv = AsyncMock()

        async def hang():
            await asyncio.sleep(10)

        tv.connect.side_effect = hang
        with patch.object(sleep_av.KEY.__class__, "read_text", return_value='{"client_key":"test"}'), \
             patch.object(sleep_av, "TVConnection", return_value=tv), \
             patch.object(sleep_av, "CHECK_BUDGET", 0.03), \
             patch.object(sleep_av, "log"):
            self.assertFalse(await asyncio.wait_for(sleep_av.run(), timeout=0.5))
        tv.request.assert_not_called()
        tv.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
