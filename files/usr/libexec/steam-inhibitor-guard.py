#!/usr/bin/python3
"""Keep Steam's suspend UI from starting while logind blocks sleep."""
import json
import logging
import signal

import gi

gi.require_version("Soup", "3.0")
from gi.repository import Gio, GLib, GLibUnix, Soup

logging.basicConfig(level=logging.INFO, format="%(message)s")


class Guard:
    def __init__(self):
        self.proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.login1", "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager", None)
        self.proxy.connect("g-properties-changed", lambda *_: self.sync())
        self.session = Soup.Session(timeout=3)
        self.busy = False
        self.generation = 0
        self.resync = False
        self.socket = None
        self.last_report = None
        self.loop = GLib.MainLoop()
        GLib.timeout_add_seconds(5, self.tick)
        GLib.idle_add(self.sync)

    def tick(self):
        self.sync()
        return GLib.SOURCE_CONTINUE

    def blocked(self):
        value = self.proxy.get_connection().call_sync(
            "org.freedesktop.login1", "/org/freedesktop/login1",
            "org.freedesktop.DBus.Properties", "Get",
            GLib.Variant("(ss)", ("org.freedesktop.login1.Manager", "BlockInhibited")),
            None, Gio.DBusCallFlags.NONE, 1000, None)
        return "sleep" in value.unpack()[0].split(":")

    def sync(self):
        if self.busy:
            self.resync = True
            return
        self.busy = True
        self.generation += 1
        generation = self.generation
        msg = Soup.Message.new("GET", "http://127.0.0.1:8080/json")
        self.session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, None,
            lambda session, result: self.targets(session, result, generation))
        GLib.timeout_add_seconds(4, self.timeout, generation)

    def timeout(self, generation):
        if self.busy and generation == self.generation:
            self.finish(generation, "Steam connection timed out")
        return GLib.SOURCE_REMOVE

    def targets(self, session, result, generation):
        if generation != self.generation or not self.busy:
            return
        try:
            targets = json.loads(session.send_and_read_finish(result).get_data())
            target = next(t for t in targets if t.get("title") == "SharedJSContext")
            msg = Soup.Message.new("GET", target["webSocketDebuggerUrl"])
            session.websocket_connect_async(msg, None, None, GLib.PRIORITY_DEFAULT,
                None, lambda s, r: self.connected(s, r, generation))
        except Exception as exc:
            self.finish(generation, f"Steam unavailable: {exc}")

    def connected(self, session, result, generation):
        try:
            ws = session.websocket_connect_finish(result)
            if generation != self.generation or not self.busy:
                ws.close(1000, "stale request")
                return
            self.socket = ws
            ws.connect("message", lambda w, kind, data: self.message(w, data, generation))
            ws.connect("error", lambda w, error: self.finish(generation, str(error)))
            blocked = json.dumps(self.blocked())
            expression = """(() => {
 const store = window.SuspendResumeStore;
 if (!store || typeof store.BlockSuspendAction !== 'function')
   throw new Error('Steam suspend API unavailable');
 const key = '__moonmachineSleepInhibitorGuard';
 let owned = window[key];
 if (BLOCKED) {
   if (!owned) owned = window[key] = {release: store.BlockSuspendAction()};
   clearTimeout(owned.timer);
   owned.timer = setTimeout(() => {
     if (window[key] === owned) { owned.release(); delete window[key]; }
   }, 15000);
 } else if (owned) {
   clearTimeout(owned.timer); owned.release(); delete window[key];
 }
 return {blocked: !!window[key], suspending: store.suspending};
})()""".replace("BLOCKED", blocked)
            ws.send_text(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
                "expression": expression, "returnByValue": True}}))
        except Exception as exc:
            self.finish(generation, str(exc))

    def message(self, ws, data, generation):
        if generation != self.generation or not self.busy:
            return
        try:
            reply = json.loads(data.get_data())
            if reply.get("id") != 1:
                return
            result = reply.get("result", {})
            if "error" in reply or "exceptionDetails" in result:
                raise RuntimeError("Steam rejected suspend guard")
            blocked = result["result"]["value"]["blocked"]
            self.finish(generation, "Steam sleep guard active" if blocked else "Steam sleep guard released")
        except Exception as exc:
            self.finish(generation, str(exc))

    def finish(self, generation, report):
        if generation != self.generation or not self.busy:
            return
        self.busy = False
        ws, self.socket = self.socket, None
        if ws is not None and ws.get_state() == Soup.WebsocketState.OPEN:
            ws.close(1000, "complete")
        if report != self.last_report:
            logging.info(report)
            self.last_report = report
        if self.resync:
            self.resync = False
            GLib.idle_add(self.sync)

    def run(self):
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.loop.quit)
        self.loop.run()


if __name__ == "__main__":
    Guard().run()
