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
    async def test_fixed_control_delegates_only_to_registered_source_and_refuses_denial(self):
        observer=NativeTelemetry(None)
        for payload in ({'action':'start_session','input_type':'audio'}, {'action':'stream_data','input_type':'audio','data':[1]}, {'action':'end_session'}):
            with self.assertRaisesRegex(RuntimeError,'not registered'):await observer.send_current(payload)
        payload={'action':'start_session','input_type':'audio','request_id':'quote\" 中文 </script> \\'}
        observer.fixed_input_id=4
        for allowed in (True,False):
            async def evaluate(expression):
                script="const sent=[];global.window={appState:{socket:{send(){throw Error('Raw socket bypass');}}},appAudioCapture:{sendFixedInputControl:(id,p)=>{if(id!==4)throw Error('Wrong source');sent.push(p);return "+str(allowed).lower()+";}}};try{const result=eval(process.argv[1]);process.stdout.write(JSON.stringify({result,sent}));}catch(e){process.stdout.write(JSON.stringify({error:e.message,sent}));}"
                result=json.loads(subprocess.check_output(['node','-e',script,expression],timeout=5))
                if 'error' in result:
                    self.assertEqual(result['sent'],[])
                    raise RuntimeError(result['error'])
                self.assertEqual(result['sent'],[payload])
                return result['result']
            observer.evaluate=evaluate
            if allowed:await observer.send_current(payload)
            else:
                with self.assertRaisesRegex(RuntimeError,'did not accept'):await observer.send_current(payload)

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
