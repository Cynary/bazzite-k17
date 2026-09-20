#!/usr/bin/env python3
"""Put the viewing chain in standby only while both inputs show the PC."""
import argparse
import asyncio
import json

import aiohttp

from direct_av import KEY, TVConnection, avr_command, avr_state, log, TV_APP, AVR_INPUT

CHECK_BUDGET = 3
TARGET = ("Active", TV_APP, "ON", AVR_INPUT)


async def snapshot(tv, session):
    async def tv_state():
        power = await tv.request("com.webos.service.tvpower/power/getPowerState")
        app = await tv.request("com.webos.applicationManager/getForegroundAppInfo")
        return power.get("state"), app.get("appId")

    television, receiver = await asyncio.gather(tv_state(), avr_state(session))
    state = (*television, *receiver)
    log(f"Sleep check: TV={television}, Denon={receiver}")
    return state


async def guarded_off(tv, session, check_only=False):
    # Read live state twice, so an input change during the first check also vetoes
    # standby. Never select inputs or wake a device as part of this operation.
    for _ in range(2):
        if await snapshot(tv, session) != TARGET:
            log("Standby skipped: both active inputs must point to the PC")
            return False
    if check_only:
        log("Check only: both inputs match; would send TV and Denon standby")
        return True

    # Send together: the TV may close its socket immediately on standby, and
    # that must not prevent the already-approved receiver command being sent.
    results = await asyncio.gather(
        tv.request("system/turnOff"),
        avr_command(session, "PWSTANDBY"),
        return_exceptions=True,
    )
    for device, result in zip(("TV", "Denon"), results):
        if isinstance(result, BaseException):
            log(f"{device} standby acknowledgement failed: {type(result).__name__}: {result}")
        else:
            log(f"{device} standby acknowledged")
    return not any(isinstance(result, BaseException) for result in results)


async def run(check_only=False):
    try:
        key = json.loads(KEY.read_text())["client_key"]
        if not key:
            raise ValueError("No existing TV pairing key")
        timeout = aiohttp.ClientTimeout(total=1.5, connect=0.75, sock_connect=0.75)
        async with asyncio.timeout(CHECK_BUDGET):
            async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
                tv = TVConnection(session, key)
                try:
                    await tv.connect()
                    return await guarded_off(tv, session, check_only)
                finally:
                    await tv.close()
    except Exception as error:
        # Missing/unreachable/ambiguous state must never authorize standby or
        # prevent the PC from sleeping. There is deliberately no later retry.
        log(f"Sleep control stopped: {type(error).__name__}: {error}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read inputs without sending standby")
    asyncio.run(run(parser.parse_args().check))
