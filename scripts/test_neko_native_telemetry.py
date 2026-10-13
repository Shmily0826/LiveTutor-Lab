"""Protocol/JS checks for task-native observation; no browser, host or provider."""
import asyncio
import json
import subprocess
import unittest
from neko_native_telemetry import NativeTelemetry, INSTALL, SNAPSHOT


class FakeDevTools:
    def __init__(self):
        self.pending = asyncio.Queue()
        self.sent = []

    async def send(self, raw):
        message = json.loads(raw)
        self.sent.append(message)
        await self.pending.put(json.dumps({"method": "Runtime.consoleAPICalled", "params": {}}))
        await self.pending.put(json.dumps({"id": message["id"], "result": {"result": {"value": message["id"]}}}))

    async def recv(self):
        return await self.pending.get()


class NativeTelemetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_observations_preserve_protocol_ids_and_notifications(self):
        socket = FakeDevTools()
        observer = NativeTelemetry(socket)
        result = await asyncio.gather(observer.evaluate("one"), observer.evaluate("two"))
        self.assertEqual(result, [1, 2])
        self.assertTrue(all(p["method"] == "Runtime.evaluate" and p["params"]["returnByValue"] for p in socket.sent))

    async def test_installed_expressions_parse_and_never_request_microphone(self):
        for expression in (INSTALL, SNAPSHOT):
            subprocess.run(["node", "-e", "new Function(process.argv[1])", expression], check=True, timeout=5)
            self.assertNotIn("getUserMedia", expression)
            self.assertNotIn("localStorage", expression)
            self.assertNotIn("document.cookie", expression)


if __name__ == "__main__": unittest.main(verbosity=2)
