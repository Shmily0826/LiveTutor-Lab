"""Replay actual source into temporary files; never start an app or device."""
import __future__
import ast
import asyncio
import contextvars
import hashlib
import json
from pathlib import Path
import queue
import re
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

import neko_voice_host_patch as patcher

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'benchmarks/raw/neko-product-host'
REPLY='答对了：WEX 是起点，箭头终点是 NUD。'


class StudyTextTrace(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='neko-text-trace-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.sources={}
        for relative in ('main_logic/omni_realtime_client/_wire_trace.py',
                         'main_logic/omni_realtime_client/_transport.py',
                         'main_logic/core/turn.py','main_logic/core/tool_calling.py'):
            target=Path(cls.temp.name)/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((HOST/relative).read_bytes())
            patcher.apply_to(target)
            assert patcher.state(target)=='patched',relative
            first=target.read_bytes();patcher.apply_to(target)
            assert target.read_bytes()==first,relative
            cls.sources[relative]=target.read_text(encoding='utf-8')
            ast.parse(cls.sources[relative])
        cls.module=ModuleType('actual_text_trace')
        exec(compile(cls.sources['main_logic/omni_realtime_client/_wire_trace.py'],'actual wire trace','exec'),cls.module.__dict__)

    def setUp(self):
        self.records=[]
        self.logger=SimpleNamespace(info=lambda fmt,*args:self.records.append(json.loads(args[-1])))
        self.trace=self.module.RealtimeWireTrace(self.logger)

    def text_records(self,stage):return [r for r in self.records if r.get('stage')==stage]

    def methods(self,relative,names,namespace):
        tree=ast.parse(self.sources[relative])
        nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
        self.assertEqual({n.name for n in nodes},set(names))
        cls=ast.ClassDef(name='ActualMethods',bases=[],keywords=[],body=nodes,decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),relative,'exec',
             flags=__future__.annotations.compiler_flag),namespace)
        return namespace['ActualMethods']

    async def test_every_provider_delta_precedes_throttle_and_keeps_ordered_digest_without_body(self):
        parts=[REPLY[:7],REPLY[7:12],REPLY[12:]]
        for part in parts:
            self.trace.record_recv({'type':'response.audio_transcript.delta','response_id':'actual-r',
                                    'delta':part},generation=2)
        self.trace.record_recv({'type':'response.audio_transcript.done','response_id':'actual-r',
                                'transcript':REPLY},generation=2)
        rows=self.text_records('provider_delta')
        self.assertEqual([r['chars'] for r in rows],list(map(len,parts)))
        self.assertEqual(rows[-1]['stream_chunks'],3)
        self.assertEqual(rows[-1]['stream_chars'],22)
        self.assertEqual(rows[-1]['stream_sha256'],hashlib.sha256(REPLY.encode()).hexdigest())
        self.assertEqual(self.text_records('provider_done')[0]['sha256'],rows[-1]['stream_sha256'])
        self.assertNotIn(REPLY,json.dumps(self.records,ensure_ascii=False))
        self.assertNotIn(parts[0],json.dumps(self.records,ensure_ascii=False))

    async def test_missing_identity_capacity_and_logger_failure_never_fabricate_prefix_or_raise(self):
        self.trace.record_study_text('provider_delta',REPLY,generation=2,cumulative=True)
        self.assertFalse(self.text_records('provider_delta')[-1]['cumulative_available'])
        for i in range(65):
            self.trace.record_study_text('provider_delta',REPLY,generation=2,response_id=str(i),cumulative=True)
        self.assertEqual(len(self.trace._study_text_streams),64)
        self.assertFalse(self.text_records('provider_delta')[-1]['cumulative_available'])
        self.trace._logger=SimpleNamespace(info=Mock(side_effect=RuntimeError('sink offline')))
        self.trace.record_study_text('provider_delta',REPLY,generation=2,response_id='0',cumulative=True)
        self.trace.record_study_relay_write('invalid json',generation=2)

    async def test_actual_relay_expression_and_socket_payload_are_distinct_digests(self):
        tree=ast.parse(self.sources['main_logic/core/tool_calling.py'])
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='_relay_study_grade_once')
        assignment=next(n for n in ast.walk(method) if isinstance(n,ast.Assign)
                        and any(isinstance(t,ast.Name) and t.id=='text' for t in n.targets))
        namespace={'claim':{'result':{'reply':REPLY,'score':100,'verdict':'correct','relay':'Read as written.'}}}
        exec(compile(ast.Module(body=[assignment],type_ignores=[]),'actual relay expression','exec'),namespace)
        payload=json.dumps({'type':'conversation.item.create','item':{'type':'message','role':'user',
                           'content':[{'type':'input_text','text':namespace['text']}]}})
        self.trace.record_study_relay_write(payload,generation=2)
        rows=self.text_records('relay_write')
        self.assertEqual(len(rows),1,'exact authoritative prefix must match actual expression')
        self.assertEqual(rows[0]['sha256'],hashlib.sha256(REPLY.encode()).hexdigest())
        envelope=self.text_records('relay_envelope_write')[0]
        self.assertEqual(envelope['sha256'],hashlib.sha256(payload.encode()).hexdigest())
        self.assertNotEqual(envelope['sha256'],rows[0]['sha256'])
        self.assertEqual(envelope['delivery'],'local_socket_write_only')

    async def test_actual_formal_grade_marker_hashes_only_reply_after_completion(self):
        cls=self.methods('main_logic/core/tool_calling.py',{'_record_study_grade_event'},{'logger':Mock()})
        core=cls()
        source=SimpleNamespace(_wire_trace=self.trace,_connection_generation=1,_tool_scope_generation=3,
                               _native_output_connection_token='native_connection_old')
        claim={'client':source,'result':{'reply':REPLY,'private_rubric':'DO NOT LOG'}}
        core._record_study_grade_event(claim,'accepted')
        self.assertEqual(self.text_records('grade_reply'),[])
        core._record_study_grade_event(claim,'grade_complete')
        self.assertEqual(self.text_records('grade_reply')[0]['sha256'],hashlib.sha256(REPLY.encode()).hexdigest())
        self.assertNotIn('DO NOT LOG',json.dumps(self.records))

    async def test_actual_socket_write_success_uses_frozen_payload_and_generation_and_failure_has_no_write_receipt(self):
        namespace={'json':json,'time':time,'asyncio':asyncio,'logger':Mock(),
            'OMNI_WS_FRAME_LIMIT_BYTES':1_000_000,
            '_RealtimeEventOwnerRetired':type('Retired',(Exception,),{}),
            'RealtimeImagePayloadTooLargeError':type('TooLarge',(Exception,),{})}
        cls=self.methods('main_logic/omni_realtime_client/_transport.py',{'send_event'},namespace)
        client=cls();client._fatal_error_occurred=False;client._is_gemini=False;client._is_throttled=False
        client._send_semaphore=asyncio.Semaphore(1);client._wire_trace=self.trace;client._connection_generation=2
        # This is the exact authoritative prefix, not a provider or ASR identity.
        text='[Authoritative Study result; do not regrade or ask a question.]\n'+json.dumps({'reply':REPLY})
        event={'type':'conversation.item.create','item':{'role':'user','content':[{'type':'input_text','text':text}]}}
        written=[]
        async def write(payload):written.append(payload);client._connection_generation=3
        client.ws=SimpleNamespace(send=write)
        self.assertTrue(await client.send_event(event,send_guard=lambda:True))
        self.assertEqual(self.text_records('relay_write')[0]['gen'],2)
        self.assertEqual(self.text_records('relay_envelope_write')[0]['sha256'],hashlib.sha256(written[0].encode()).hexdigest())
        client.ws=SimpleNamespace(send=AsyncMock(side_effect=ConnectionError('fixture write refused')))
        with self.assertRaises(ConnectionError):await client.send_event(event,send_guard=lambda:True)
        self.assertEqual(len(self.text_records('relay_write')),1)

    async def test_actual_omni_buffer_flush_keeps_full_callback_text_and_digest(self):
        cls=self.methods('main_logic/omni_realtime_client/_transport.py',
            {'_take_pending_output_transcript','_emit_pending_output_transcript','_flush_pending_output_transcript'},
            {'logger':Mock()})
        client=cls();client._wire_trace=self.trace;client._connection_generation=2
        client._current_response_id='actual-r';client._tool_scope_generation=5
        client._native_output_connection_token='native_connection_t'
        client._output_transcript_buffer=REPLY;client._audio_delta_count=6;client._is_first_transcript_chunk=True
        client.on_output_transcript=AsyncMock()
        await client._flush_pending_output_transcript()
        client.on_output_transcript.assert_awaited_once_with(REPLY,True)
        self.assertEqual(self.text_records('omni_callback')[0]['sha256'],hashlib.sha256(REPLY.encode()).hexdigest())

    async def test_actual_core_callback_keeps_full_text_and_traces_entry_queue_and_successful_ws(self):
        namespace={'time':time,'logger':Mock(),'_REQUEST_ID_UNSET':object(),
                   '_proactive_expected_sid':contextvars.ContextVar('fixture_sid',default=None),
                   'OmniOfflineClient':type('Offline',(),{}),'OmniRealtimeClient':type('Realtime',(),{}),
                   'TurnOwner':SimpleNamespace(PROACTIVE=object()),'WebSocketDisconnect':type('Disconnect',(Exception,),{})}
        cls=self.methods('main_logic/core/turn.py',{'handle_output_transcript','send_lanlan_response'},namespace)
        core=cls();core.session=SimpleNamespace(_wire_trace=self.trace,_connection_generation=2,
            _current_response_id='actual-r',_tool_scope_generation=5,_native_output_connection_token='native_connection_t')
        core._takeover_active=False;core._study_grade_output_held=lambda:False
        core.current_speech_id='s';core.use_tts=False;core.emotion_pattern=re.compile('<(.*?)>')
        core._active_text_request_id=None;core._current_ai_turn_text='';core.sync_message_queue=queue.Queue()
        core._remember_recent_ai_voice_echo=Mock();core._push_focus_thinking=AsyncMock()
        state=SimpleNamespace(CONNECTED=1)
        core.websocket=SimpleNamespace(client_state=state,send_json=AsyncMock());state.CONNECTED=state
        core.websocket_lock=None;core.lanlan_name='Tutor';core.master_name='Learner'
        await core.handle_output_transcript(REPLY,True)
        sent=core.websocket.send_json.await_args.args[0]
        self.assertEqual(sent['text'],REPLY)
        self.assertEqual(core.sync_message_queue.get()['data']['text'],REPLY)
        for stage in ('core_entry','core_queue','core_ws'):
            self.assertEqual(self.text_records(stage)[0]['sha256'],hashlib.sha256(REPLY.encode()).hexdigest())
        core._takeover_active=True
        await core.handle_output_transcript('blocked tail',False)
        self.assertEqual(len(self.text_records('core_entry')),2)
        self.assertEqual(len(self.text_records('core_queue')),1)
        self.assertEqual(core.websocket.send_json.await_count,1)
        core._takeover_active=False
        async def replace_session(message):core.session=SimpleNamespace(_connection_generation=99)
        core.websocket.send_json=AsyncMock(side_effect=replace_session)
        await core.handle_output_transcript('second chunk',False)
        self.assertEqual(self.text_records('core_ws')[-1]['gen'],2)
        self.assertEqual(self.text_records('core_ws')[-1]['token'],'native_connection_t')


if __name__=='__main__':unittest.main(verbosity=2)
