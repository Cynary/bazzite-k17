#!/usr/bin/env python3
"""Direct LG SSAP and Denon HTTP control, with measured resume timing."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import xml.etree.ElementTree as ET

import aiohttp
from aiowebostv import WebOsClient

CONFIG = json.loads(Path(os.environ.get("MOONMACHINE_AV_CONFIG", "/etc/moonmachine/av.json")).read_text())
TV = CONFIG["tv_address"]
AVR = CONFIG["receiver_url"].rstrip("/")
TV_INPUT = CONFIG["tv_input"]
TV_APP = CONFIG["tv_app"]
AVR_INPUT = CONFIG["receiver_input"]
KEY = Path("/var/lib/moonmachine-av/tv-key.json")
START = time.monotonic()


def log(message):
    print(f"+{time.monotonic() - START:.3f}s {message}", flush=True)


class TVConnection:
    def __init__(self, session, key):
        self.session = session
        self.key = key
        self.ws = None
        self.counter = 0

    async def connect(self, pair=False):
        self.ws = await self.session.ws_connect(
            f"wss://{TV}:3001", ssl=False, heartbeat=15,
            timeout=aiohttp.ClientWSTimeout(ws_close=1),
        )
        client = WebOsClient(TV, self.key)
        await self.ws.send_json(client.registration_msg())
        async with asyncio.timeout(90 if pair else 2):
            while True:
                response = await self.ws.receive_json()
                if response.get("type") == "registered":
                    self.key = response.get("payload", {}).get("client-key", self.key)
                    return
                if response.get("type") == "error":
                    raise RuntimeError(response.get("error", "TV registration error"))
                if response.get("payload", {}).get("pairingType") == "PROMPT":
                    if not pair:
                        raise RuntimeError("TV requires pairing again")
                    log("PAIRING PROMPT: accept the connection on the TV")

    async def request(self, uri, payload=None):
        self.counter += 1
        uid = f"moonmachine-{self.counter}"
        await self.ws.send_json({"id": uid, "type": "request", "uri": f"ssap://{uri}", "payload": payload or {}})
        async with asyncio.timeout(2):
            while True:
                reply = await self.ws.receive_json()
                if reply.get("id") != uid:
                    continue
                if reply.get("type") == "error":
                    raise RuntimeError(reply.get("error", "TV command error"))
                result = reply.get("payload", {})
                if result.get("returnValue") is False:
                    raise RuntimeError(f"TV rejected {uri}: {result.get('errorText', result.get('errorCode'))}")
                return result

    async def close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None


async def avr_command(session, command):
    async with session.get(AVR + "/goform/formiPhoneAppDirect.xml?" + command) as response:
        response.raise_for_status()
        await response.read()


async def avr_state(session):
    body = b'<?xml version="1.0" encoding="utf-8"?>\r\n<tx>\r\n<cmd id="1">GetAllZonePowerStatus</cmd>\r\n<cmd id="1">GetAllZoneSource</cmd>\r\n</tx>\r\n'
    async with session.post(AVR + "/goform/AppCommand.xml", data=body, headers={"Content-Type": "text/xml; charset=utf-8"}) as response:
        response.raise_for_status()
        root = ET.fromstring(await response.text())
    return root.findtext("./cmd[1]/zone1"), root.findtext("./cmd[2]/zone1/source")


def tv_wol():
    mac = bytes.fromhex(CONFIG["tv_mac"].replace(":", "").replace("-", ""))
    if len(mac) != 6:
        raise ValueError("tv_mac must contain six bytes")
    target = CONFIG["broadcast_address"]
    if CONFIG.get("unicast_wake", False):
        # A sleeping Wi-Fi TV may not answer ARP. Only pin a neighbour on the
        # same subnet, never for a destination reached through a router.
        route = json.loads(subprocess.check_output(
            ["ip", "-j", "route", "get", TV], timeout=2))[0]
        if "gateway" in route:
            raise ValueError("Unicast neighbour workaround requires the same subnet")
        subprocess.run(["ip", "neigh", "replace", TV, "lladdr", CONFIG["tv_mac"],
                        "nud", "permanent", "dev", route["dev"]], check=True, timeout=2)
        target = TV
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(b"\xff" * 6 + mac * 16, (target, 9))


async def wake(session, key):
    deadline = time.monotonic() + 90
    receiver_ready = asyncio.Event()
    tv_ready = asyncio.Event()
    status = {"tv": False, "avr": False}

    async def receiver():
        previous = None
        while time.monotonic() < deadline:
            try:
                state = await avr_state(session)
                if state != previous:
                    log(f"Denon state: {state}")
                    previous = state
                if state[0] != "ON":
                    await avr_command(session, "PWON")
                    log("Denon power-on sent")
                if not receiver_ready.is_set():
                    receiver_ready.set()
                    log("Network ready; receiver contacted")
                if state[0] == "ON" and state[1] != AVR_INPUT:
                    await avr_command(session, "SI" + AVR_INPUT)
                    log("Denon target input sent")
                status["avr"] = state == ("ON", AVR_INPUT)
            except (aiohttp.ClientError, TimeoutError, ET.ParseError, OSError) as error:
                status["avr"] = False
                if receiver_ready.is_set():
                    log(f"Denon retry: {type(error).__name__}")
            await asyncio.sleep(0.25 if not receiver_ready.is_set() else 0.75)

    async def wol():
        await receiver_ready.wait()
        count = 0
        while time.monotonic() < deadline and not tv_ready.is_set():
            tv_wol()
            count += 1
            log(f"TV unicast wake sent ({count})")
            await asyncio.sleep(2)

    async def television():
        await receiver_ready.wait()
        previous = None
        while time.monotonic() < deadline:
            tv = TVConnection(session, key)
            try:
                await tv.connect()
                log("TV direct connection registered")
                # Try the port command before waiting for power-state discovery.
                try:
                    result = await tv.request("tv/switchInput", {"inputId": TV_INPUT})
                    log(f"Early TV input acknowledgement: {result.get('returnValue')}")
                except (RuntimeError, TimeoutError) as error:
                    log(f"Early TV input not ready: {type(error).__name__}: {error}")
                while time.monotonic() < deadline:
                    power = await tv.request("com.webos.service.tvpower/power/getPowerState")
                    app = await tv.request("com.webos.applicationManager/getForegroundAppInfo")
                    current = (power.get("state"), app.get("appId"))
                    if current != previous:
                        log(f"TV state: {current}")
                        previous = current
                    on = current[0] == "Active"
                    if on:
                        tv_ready.set()
                    status["tv"] = on and current[1] == TV_APP
                    if on and current[1] != TV_APP:
                        result = await tv.request("tv/switchInput", {"inputId": TV_INPUT})
                        log(f"TV input acknowledgement: {result.get('returnValue')}")
                    await asyncio.sleep(0.5)
            except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError, OSError) as error:
                status["tv"] = False
                log(f"TV retry: {type(error).__name__}: {error}")
            finally:
                await tv.close()
            await asyncio.sleep(0.3)

    tasks = [asyncio.create_task(f()) for f in (receiver, wol, television)]
    stable = None
    first_correct = False
    try:
        while time.monotonic() < deadline:
            for task in tasks:
                if task.done() and not task.cancelled() and task.exception():
                    raise task.exception()
            if all(status.values()):
                if not first_correct:
                    log("Both target inputs confirmed")
                    first_correct = True
                if stable is None:
                    stable = time.monotonic()
                elif time.monotonic() - stable >= 5:
                    log("Both target inputs stable for 5 seconds")
                    return
            else:
                stable = None
            await asyncio.sleep(0.1)
        raise TimeoutError("Direct wake did not settle within 90 seconds")
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["pair", "status", "wake"])
    args = parser.parse_args()
    key = json.loads(KEY.read_text())["client_key"] if KEY.exists() else None
    if args.mode != "pair" and not key:
        raise RuntimeError("Run pair first")
    timeout = aiohttp.ClientTimeout(total=3, connect=1, sock_connect=1)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
        if args.mode == "wake":
            await wake(session, key)
            return
        tv = TVConnection(session, None if args.mode == "pair" else key)
        try:
            await tv.connect(pair=args.mode == "pair")
            if args.mode == "pair":
                if not tv.key:
                    raise RuntimeError("No pairing key returned")
                fd = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as stream:
                    json.dump({"client_key": tv.key}, stream)
                log("TV pairing saved privately")
            else:
                log(f"TV power: {await tv.request('com.webos.service.tvpower/power/getPowerState')}")
                log(f"TV app: {await tv.request('com.webos.applicationManager/getForegroundAppInfo')}")
                log(f"Receiver: {await avr_state(session)}")
        finally:
            await tv.close()


if __name__ == "__main__":
    asyncio.run(main())
