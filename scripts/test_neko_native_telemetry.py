"""Protocol/JS checks for task-native observation; no browser, host or provider."""
import asyncio
import json
import subprocess
import unittest
from neko_native_telemetry import NativeTelemetry, NativeRendererPending, INSTALL, SNAPSHOT, BEGIN_FIXED_INPUT
import urllib.error
import time
from pathlib import Path
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
    async def test_bounded_ready_wait_only_polls_the_same_task_port(self):
        ready=object()
        attach=AsyncMock(side_effect=[NativeRendererPending('loading'),
                                     urllib.error.URLError(ConnectionRefusedError()),ready])
        with patch.object(NativeTelemetry,'attach',attach),patch('neko_native_telemetry.asyncio.sleep',AsyncMock()):
            self.assertIs(await NativeTelemetry.attach_when_ready(9233),ready)
        self.assertEqual(attach.await_count,3)
        self.assertTrue(all(call.args==(9233,) and 0<call.kwargs['timeout']<=8 for call in attach.await_args_list))

    async def test_ready_wait_never_retries_identity_install_or_other_network_errors(self):
        for error in (RuntimeError('foreign root'),RuntimeError('2 root pages'),RuntimeError('install failed'),
                      urllib.error.URLError('HTTP access refused')):
            attach=AsyncMock(side_effect=error)
            with patch.object(NativeTelemetry,'attach',attach):
                with self.assertRaises(type(error)):await NativeTelemetry.attach_when_ready(9233)
            self.assertEqual(attach.await_count,1)
            self.assertEqual(attach.await_args.args,(9233,))

    async def test_ready_wait_expires_without_launching_or_reconnecting_anything(self):
        attach=AsyncMock(side_effect=NativeRendererPending('loading'))
        started=asyncio.get_running_loop().time()
        with patch.object(NativeTelemetry,'attach',attach):
            with self.assertRaisesRegex(TimeoutError,'deadline expired'):
                await NativeTelemetry.attach_when_ready(9233,timeout=.005)
        self.assertLess(asyncio.get_running_loop().time()-started,.2)
        self.assertGreaterEqual(attach.await_count,1)
        self.assertTrue(all(call.args==(9233,) for call in attach.await_args_list))

    async def test_blocking_local_http_does_not_block_the_attachment_deadline(self):
        def delayed_http(*args):
            time.sleep(.2)
            return []
        started=asyncio.get_running_loop().time()
        with patch('neko_native_telemetry.read_task_targets',delayed_http):
            with self.assertRaises(TimeoutError):await NativeTelemetry.attach(9233,timeout=.01)
        self.assertLess(asyncio.get_running_loop().time()-started,.1)

    async def test_installation_timeout_is_not_retried_and_closes_the_socket(self):
        targets=[{'type':'page','url':'http://localhost:48911/','webSocketDebuggerUrl':'ws://task/pet'}]
        socket=SimpleNamespace(close=AsyncMock())
        evaluate=AsyncMock(side_effect=[{'socketReady':1,'audioPlaybackAvailable':True},TimeoutError('install')])
        connect=AsyncMock(return_value=socket)
        with patch('neko_native_telemetry.read_task_targets',return_value=targets),\
             patch('neko_native_telemetry.websockets.connect',connect),patch.object(NativeTelemetry,'evaluate',evaluate):
            with self.assertRaisesRegex(RuntimeError,'installation timed out'):
                await NativeTelemetry.attach_when_ready(9233)
        self.assertEqual(connect.await_count,1);socket.close.assert_awaited_once()

    async def test_failed_attachment_close_has_an_independent_bounded_cleanup(self):
        from neko_native_telemetry import close_failed_attachment
        from unittest.mock import Mock
        transport=SimpleNamespace(abort=Mock())
        async def stalled_close():await asyncio.sleep(60)
        socket=SimpleNamespace(close=stalled_close,transport=transport)
        started=asyncio.get_running_loop().time()
        await close_failed_attachment(socket)
        self.assertLess(asyncio.get_running_loop().time()-started,3)
        transport.abort.assert_called_once()

    async def test_actual_controller_trace_binds_ticket_and_late_old_status_to_socket(self):
        fixture=(Path(__file__).parent/'neko_fixed_input_fixture.mjs').as_uri()
        script=r'''import vm from 'node:vm';import {fixture} from FIXTURE;
const f=fixture();
function observable(socket){const handlers=[];socket.addEventListener=(name,fn)=>{if(name==='message')handlers.push(fn);};socket.emit=payload=>handlers.forEach(fn=>fn({data:JSON.stringify(payload)}));socket.emitBinary=()=>handlers.forEach(fn=>fn({data:{byteLength:8}}));return socket;}
const firstSocket=observable(f.S.socket);
vm.runInContext(process.argv[1],f.context);
const first=vm.runInContext(process.argv[2],f.context);
f.api.endFixedInput(first.id);
const secondSocket=observable({readyState:1,send(){}});
f.S.socket=secondSocket;
const second=vm.runInContext(process.argv[2],f.context);
firstSocket.emit({type:'status',message:JSON.stringify({code:'VOICE_INPUT_CONTROL_REJECTED',details:{reason:'old_control'}})});
secondSocket.emit({type:'status',message:JSON.stringify({code:'VOICE_INPUT_CONTROL_REJECTED',details:{reason:'current_control'}})});
firstSocket.emit({type:'audio_chunk',sdk_speech_correlation_id:'old-correlation'});
secondSocket.emit({type:'audio_chunk',sdk_speech_correlation_id:'current-correlation'});
firstSocket.emit({type:'audio_chunk',sdk_speech_correlation_id:'late-old-correlation'});
secondSocket.emitBinary();
const trace=f.context.__dailyNativeTelemetry;
process.stdout.write(JSON.stringify({first,second,events:trace.events,currentSocketId:trace.currentSocketId,captureCalls:f.captured()}));'''.replace('FIXTURE',json.dumps(fixture))
        result=json.loads(subprocess.check_output(['node','--input-type=module','-e',script,INSTALL,BEGIN_FIXED_INPUT],timeout=10))
        self.assertEqual(result['captureCalls'],0)
        self.assertEqual((result['first']['socket_id'],result['second']['socket_id']),(1,2))
        self.assertNotEqual(result['first']['id'],result['second']['id'])
        self.assertEqual(result['currentSocketId'],2)
        binary=next(e for e in result['events'] if e.get('type')=='audio_frame')
        self.assertEqual((binary['socket_id'],binary['correlation_id']),(2,'current-correlation'))
        rejects=[e for e in result['events'] if e.get('code')=='VOICE_INPUT_CONTROL_REJECTED']
        self.assertEqual([(e['socket_id'],e['reason']) for e in rejects],[(1,'old_control'),(2,'current_control')])
        for receipt in (result['first'],result['second']):
            controls=[e for e in result['events'] if e['direction']=='send' and e.get('owner')=='core' and e['socket_id']==receipt['socket_id']]
            self.assertTrue(controls);self.assertEqual(controls[0]['lease_generation'],receipt['lease_generation'])
            self.assertGreaterEqual(controls[0]['wall'],receipt['started_wall'])

    async def test_python_registration_preserves_scope_and_refuses_unbound_receipt(self):
        observer=NativeTelemetry(None)
        receipt={'active':True,'capture_started':False,'owner':'core','id':1,'lease_generation':2,'socket_id':1,'started_wall':100.0}
        with patch.object(observer,'evaluate',AsyncMock(return_value={k:v for k,v in receipt.items() if k!='socket_id'})):
            with self.assertRaisesRegex(RuntimeError,'registration failed'):await observer.begin_fixed_input()
        self.assertIsNone(observer.fixed_input_id)
        with patch.object(observer,'evaluate',AsyncMock(return_value=receipt)):
            self.assertEqual(await observer.begin_fixed_input(),receipt)
        self.assertEqual(observer.fixed_input_scope,{'ticket_id':1,'socket_id':1,'started_wall':100.0})

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
        for expression in (INSTALL, SNAPSHOT, BEGIN_FIXED_INPUT):
            subprocess.run(["node", "-e", "new Function(process.argv[1])", expression], check=True, timeout=5)
            self.assertNotIn("getUserMedia", expression)
            self.assertNotIn("localStorage", expression)
            self.assertNotIn("document.cookie", expression)


if __name__ == "__main__": unittest.main(verbosity=2)
