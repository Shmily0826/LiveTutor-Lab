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
    async def test_fixed_input_uses_current_renderer_socket_and_refuses_closed(self):
        observer=NativeTelemetry(None)
        payload={'action':'stream_data','input_type':'text','data':'quote\" 中文 </script> \\'}
        for state in (1,3):
            async def evaluate(expression):
                script="const sent=[];global.window={appState:{socket:{readyState:"+str(state)+",send:x=>sent.push(JSON.parse(x))}}};try{const result=eval(process.argv[1]);process.stdout.write(JSON.stringify({result,sent}));}catch(e){process.stdout.write(JSON.stringify({error:e.message,sent}));}"
                result=json.loads(subprocess.check_output(['node','-e',script,expression],timeout=5))
                if 'error' in result:
                    self.assertEqual(result['sent'],[])
                    raise RuntimeError(result['error'])
                self.assertEqual(result['sent'],[payload])
                return result['result']
            observer.evaluate=evaluate
            if state==1:await observer.send_current(payload)
            else:
                with self.assertRaisesRegex(RuntimeError,'controller unavailable'):await observer.send_current(payload)

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
