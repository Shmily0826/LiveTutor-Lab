"""Protocol/JS checks for task-native observation; no browser, host or provider."""
import asyncio
import json
import subprocess
import unittest
from neko_native_telemetry import NativeTelemetry, INSTALL, SNAPSHOT
from unittest.mock import AsyncMock,patch
from types import SimpleNamespace


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
    async def test_unique_ready_pet_is_selected_and_setup_failure_closes_it(self):
        targets=[{'type':'page','url':'http://localhost:48911/chat_full','webSocketDebuggerUrl':'ws://task/chat'},
                 {'type':'page','url':'http://localhost:48911/','webSocketDebuggerUrl':'ws://task/pet'}]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps(targets).encode()
        for fail in (False,True):
            socket=SimpleNamespace(close=AsyncMock())
            evaluate=AsyncMock(side_effect=[{'socketReady':1,'audioPlaybackAvailable':True},RuntimeError('install failed') if fail else {'installed':True}])
            connect=AsyncMock(return_value=socket)
            with patch('neko_native_telemetry.urllib.request.build_opener',return_value=SimpleNamespace(open=lambda *a,**k:Response())),\
                 patch('neko_native_telemetry.websockets.connect',connect),patch.object(NativeTelemetry,'evaluate',evaluate):
                if fail:
                    with self.assertRaisesRegex(RuntimeError,'install failed'):await NativeTelemetry.attach(9231)
                    socket.close.assert_awaited_once()
                else:
                    observer=await NativeTelemetry.attach(9231)
                    self.assertIs(observer.socket,socket);socket.close.assert_not_awaited()
            self.assertEqual(connect.await_args.args[0],'ws://task/pet')

    async def test_absent_ambiguous_or_foreign_pet_is_refused_before_connect(self):
        for urls in (['http://localhost:48911/chat_full'],['http://localhost:48911/','http://127.0.0.1:48911/'],['http://foreign:48911/','http://localhost:9231/']):
            targets=[{'type':'page','url':url,'webSocketDebuggerUrl':'ws://task/unselected'} for url in urls]
            class Response:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self):return json.dumps(targets).encode()
            with patch('neko_native_telemetry.urllib.request.build_opener',return_value=SimpleNamespace(open=lambda *a,**k:Response())),\
                 patch('neko_native_telemetry.websockets.connect',AsyncMock()) as connect:
                with self.assertRaisesRegex(RuntimeError,'identity unresolved'):await NativeTelemetry.attach(9231)
            connect.assert_not_awaited()

    async def test_not_ready_pet_never_falls_back_to_ready_chat(self):
        targets=[{'type':'page','url':'http://localhost:48911/','webSocketDebuggerUrl':'ws://task/pet'},
                 {'type':'page','url':'http://localhost:48911/chat_full','webSocketDebuggerUrl':'ws://task/chat'}]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps(targets).encode()
        pet=SimpleNamespace(close=AsyncMock(),kind='pet')
        chat=SimpleNamespace(close=AsyncMock(),kind='chat')
        async def evaluate(observer,expression):
            if expression==INSTALL:return {'installed':True}
            return {'socketReady':0 if observer.socket is pet else 1,'audioPlaybackAvailable':True}
        connect=AsyncMock(side_effect=[pet,chat])
        with patch('neko_native_telemetry.urllib.request.build_opener',return_value=SimpleNamespace(open=lambda *a,**k:Response())),\
             patch('neko_native_telemetry.websockets.connect',connect),\
             patch.object(NativeTelemetry,'evaluate',evaluate):
            with self.assertRaisesRegex(RuntimeError,'pet.*not ready'):
                await NativeTelemetry.attach(9231)
        self.assertEqual(connect.await_count,1)
        pet.close.assert_awaited_once();chat.close.assert_not_awaited()

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
