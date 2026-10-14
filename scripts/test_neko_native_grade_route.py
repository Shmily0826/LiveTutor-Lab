"""Replayed Core methods + actual SDK/SQLite/arbiter, local model/transport doubles.

No host, network, capture, playback, or physical device is started.
"""
import __future__
import ast
import asyncio
import contextlib
from dataclasses import dataclass,field
import importlib
import json
import logging
import os
from pathlib import Path
import queue
import sys
import tempfile
import time
import types
from typing import Any
import unittest
from unittest.mock import patch,Mock,AsyncMock
from uuid import uuid4
import neko_native_grade_patch as grade_patch
import neko_material_control_sdk_audit as sdk
import test_neko_answer_material_guard as grade

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'benchmarks/raw/neko-product-host'
LOGGER=logging.getLogger('native-grade-test')

def replay(relative):
    text=(HOST/relative).read_text(encoding='utf-8')
    for old,new in grade_patch.UPGRADES.get(relative,()):
        if new not in text:
            assert text.count(old)==1,(relative,old[:60])
            text=text.replace(old,new)
    return ast.parse(text)

def methods(tree,names):
    found=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in found}==set(names)
    return found

def compile_class(name,nodes,namespace):
    cls=ast.ClassDef(name=name,bases=[],keywords=[],body=nodes,decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),name,'exec',
        flags=__future__.annotations.compiler_flag),namespace)
    return namespace[name]

# Load only dataclass tool records and the method bodies used, not the app.
record_tree=ast.parse((HOST/'main_logic/tool_calling.py').read_text(encoding='utf-8'))
record_ns={'dataclass':dataclass,'field':field,'Any':Any}
records=[n for n in record_tree.body if isinstance(n,ast.ClassDef) and n.name in {'ToolCall','ToolResult'}]
exec(compile(ast.Module(body=records,type_ignores=[]),'tool records','exec',flags=__future__.annotations.compiler_flag),record_ns)
ToolCall,ToolResult=record_ns['ToolCall'],record_ns['ToolResult']
tools_tree=ast.parse((HOST/'main_logic/omni_realtime_client/_tools.py').read_text(encoding='utf-8'))
tools_ns={'asyncio':asyncio,'logger':LOGGER,'dataclass':dataclass,'Any':Any}
owner=next(n for n in tools_tree.body if isinstance(n,ast.ClassDef) and n.name=='_ToolTaskOwner')
exec(compile(ast.Module(body=[owner],type_ignores=[]),'actual tool owner','exec',flags=__future__.annotations.compiler_flag),tools_ns)
tool_names={'_capture_tool_task_owner','_tool_task_owner_is_current','_tool_task_connection_is_current',
    '_track_tool_task','_create_tool_task','_retired_tool_task_registry',
    '_tool_batch_entries_by_task','_tool_batch_by_collector_task'}
client_nodes=methods(tools_tree,tool_names)+methods(replay('main_logic/omni_realtime_client/_transport.py'),
    {'_capture_study_grade_pin','_take_study_grade_asr','_advance_study_grade_ingress_scope'})
ClientBase=compile_class('ClientMethods',client_nodes,tools_ns)

# Import the real pure transcript policy without importing the application.
voice_package=types.ModuleType('grade_voice_policy')
voice_package.__path__=[str(HOST/'main_logic/voice_turn')]
sys.modules[voice_package.__name__]=voice_package
admission_module=importlib.import_module('grade_voice_policy.transcript_admission')

# Actual arbiter modules, with the logger sink isolated; no realtime __init__.
package=types.ModuleType('grade_protocol');package.__path__=[str(HOST/'main_logic/omni_realtime_client')]
sys.modules[package.__name__]=package
import utils.logger_config as logger_config
with patch.object(logger_config,'get_module_logger',lambda *args:LOGGER):
    arbiter_module=importlib.import_module('grade_protocol._response_arbiter')

class Client(ClientBase):
    def __init__(self):
        self._connection_generation=1;self._tool_scope_generation=1
        self._is_gemini=False;self._is_free_proxy=True;self.ws=object()
        self._native_output_connection_token='native_connection_original'
        self._voice_handoff_input_sequence=10;self._current_turn_host_id='previous-response'
        self._read_host_turn_id=lambda:'previous-host'
        self.wire=[];self.connects=0;self.closes=0;self.arbiters=[]
        self.before_send=None;self.before_connect=None
        self.capabilities=None
    async def send_event(self,event,*,send_guard=None):
        if self.before_send is not None:await self.before_send(event)
        if send_guard is not None and not send_guard():raise ConnectionError('owner retired before local wire')
        self.wire.append(json.loads(json.dumps(event)));return True
    def _ensure_response_arbiter(self):
        if not self.arbiters:
            self.arbiters.append(arbiter_module.RealtimeResponseArbiter(self.send_event,
                protocol_capabilities=self.capabilities))
        return self.arbiters[-1]
    async def close(self):
        self.closes+=1;self._tool_scope_generation+=1;self.ws=None
        for task in tuple(getattr(self,'_tool_tasks',())):
            if task is not asyncio.current_task() and not task.done():task.cancel()
    async def connect(self,instructions,native_audio=True):
        self.connects+=1
        if self.before_connect is not None:await self.before_connect()
        self._connection_generation+=1;self.ws=object();self._study_grade_pin=None
        self._native_output_connection_token='native_connection_controlled'
        self._fatal_error_occurred=False

core_tree=replay('main_logic/core/tool_calling.py')
core_names={
    '_read_study_question_pin','_study_input_authority','_make_study_input_handler','_study_grade_claim_current',
    '_study_grade_output_held','_start_study_grade_claim','_study_grade_payload',
    '_run_study_grade_claim','_study_grade_notice','_relay_study_grade_once',
    '_on_tool_call','_capture_study_material_tool_owner','_bind_study_material_tool_result','_valid_study_material_record'}
core_nodes=methods(core_tree,core_names)
core_nodes+=methods(ast.parse((HOST/'main_logic/core/context_append.py').read_text(encoding='utf-8')),{'_fire_task'})
core_nodes+=methods(replay('main_logic/core/turn.py'),{'handle_input_transcript'})
core_ns={'asyncio':asyncio,'os':os,'logger':LOGGER,'ToolCall':ToolCall,'ToolResult':ToolResult,'OmniRealtimeClient':Client,
    'time':time,'uuid4':uuid4,'assess_transcript':admission_module.assess_transcript,
    'TranscriptDisposition':admission_module.TranscriptDisposition,
    'get_active_game_route_generation_identity':lambda role:None}
CoreBase=compile_class('CoreMethods',core_nodes,core_ns)

class Socket:
    def __init__(self):self.events=[]
    async def send_json(self,event):self.events.append(event)

class Core(CoreBase):
    def __init__(self,client,registry):
        self.session=client;self.tool_registry=registry;self.websocket=Socket()
        self.is_active=True;self.use_tts=False;self._takeover_active=False
        self._asr_route_mode='native';self._voice_lease_owner='native';self.lanlan_name='GradeRole'
        self.activation=('native-lease',1);self._bg_tasks=set()
        self._core_voice_session_swap_lock=asyncio.Lock();self.audio_lock=asyncio.Lock()
        self._native_activation_reconnect_timeout_s=1;self._core_voice_listener_cancel_timeout_s=.2
        # Peripheral UI/activity/plugin-bus sinks; real transcript admission and
        # claim initiation above remain unmodified method bodies.
        self._takeover_input_dispatcher=None;self._activity_tracker=Mock()
        self._should_suppress_dirty_voice_transcript=lambda text:False
        self._broadcast_voice_transcript_observed=AsyncMock()
        self._note_user_turn=Mock();self.note_user_engagement=Mock()
        self._publish_user_utterance_to_plugin_bus=Mock()
        self._inject_pending_user_directives=AsyncMock()
        self._dispatch_mini_game_invite_keyword=AsyncMock()
        self._session_turn_count=0;self.sync_message_queue=queue.Queue()
    def _capture_voice_session_activation_generation(self):return self.activation
    def _ensure_audio_frame_send_lock(self):return self.audio_lock
    async def _restart_message_handler_after_session_reconnect(self,*args,**kwargs):return True


class NativeGradeRoute(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='neko-native-grade-')
        self.runtime=Path(self.temporary.name)/'runtime'
        self.store=grade.Store(self.runtime/'plugins/study_companion/data/study_companion.db',
            Path(self.temporary.name)/'unused.json',LOGGER)
        self.store.open();self.h=grade.GradeHarness(self.store)
        await grade.AnswerMaterial.prepare(self)
        self.h._state.current_question['attempt_evaluated']=False
        await self.h._persist_state()
        self.env=patch.dict(os.environ,{'NEKO_STUDY_AUTO_GRADE':'1','NEKO_STORAGE_SELECTED_ROOT':str(self.runtime)})
        self.env.start()
        # Telemetry is irrelevant to admission and must not contact any sink.
        telemetry=types.ModuleType('utils.token_tracker')
        telemetry.TokenTracker=types.SimpleNamespace(get_instance=lambda:Mock())
        self.telemetry=patch.dict(sys.modules,{'utils.token_tracker':telemetry})
        self.telemetry.start()
        legacy=sdk.PluginContext(plugin_id='study_companion',config_path=Path(self.temporary.name)/'plugin.toml',
            logger=sdk.QuietLogger(),status_queue=queue.Queue(),message_queue=queue.Queue())
        registry=sdk.NekoPluginBase.__new__(sdk.NekoPluginBase)
        registry._host_ctx,registry.ctx,registry.logger=legacy,sdk.SdkContext(legacy),sdk.QuietLogger()
        registry._routers,registry._dynamic_entries,registry._llm_tools=[],{},{}
        for name,handler in [('study_answer',self.h.study_answer_tool),('study_session',self.h.study_session_tool)]:
            registry._register_llm_tool_internal(sdk.LlmToolMeta(name=name,description='actual grade route',parameters={'type':'object'}),handler)
        serialize=sdk.host_result_serializer()
        class Trigger:
            async def trigger(inner,entry_id,arguments,timeout):
                entry=registry.collect_entries()[entry_id]
                kwargs=sdk.prepare_entry_kwargs(plugin_id='study_companion',entry_id=entry_id,
                    handler=entry.handler,meta=entry.meta,args=arguments)
                return serialize(await entry.handler(**kwargs))['data']
        class State:
            plugin_hosts={'study_companion':Trigger()}
            def acquire_plugin_hosts_read_lock(inner):return contextlib.nullcontext()
        callback=sdk.callback_function(State())
        class Registry:
            def get(inner,name):return types.SimpleNamespace(metadata={'source':'plugin:study_companion'})
            async def execute(inner,call):
                packet=await callback('study_companion',call.name,{'arguments':call.arguments,'call_id':call.call_id})
                return ToolResult(call_id=call.call_id,name=call.name,output=packet['output'],is_error=packet.get('is_error',False))
        self.client=Client();self.core=Core(self.client,Registry())
        self.client.get_study_question_pin=lambda:self.core._read_study_question_pin(self.client)
        self.client.get_study_input_authority=lambda:self.core._study_input_authority(self.client)
    async def asyncTearDown(self):
        for task in tuple(self.core._bg_tasks):
            if not task.done():task.cancel()
        await asyncio.gather(*tuple(self.core._bg_tasks),return_exceptions=True)
        for arbiter in self.client.arbiters:await arbiter.shutdown()
        for task in tuple(getattr(self.client,'_tool_tasks',())):
            if not task.done():task.cancel()
        await asyncio.gather(*tuple(getattr(self.client,'_tool_tasks',())),return_exceptions=True)
        self.telemetry.stop();self.env.stop();self.store.close();self.temporary.cleanup()
    def capture(self):
        self.client._capture_study_grade_pin(True,10)
        return self.client._take_study_grade_asr(self.client.ws,self.client._connection_generation)
    async def settle(self):
        await asyncio.gather(*tuple(getattr(self.client,'_tool_tasks',())),return_exceptions=True)
        await asyncio.gather(*tuple(self.core._bg_tasks),return_exceptions=True)
    async def test_zero_provider_call_runs_one_actual_sdk_grade_and_owned_plain_relay(self):
        receipt=self.capture()
        normal=self.client._capture_tool_task_owner(self.client.ws)
        self.assertFalse(self.client._tool_task_owner_is_current(normal))
        self.assertTrue(self.client._tool_task_owner_is_current(receipt['owner']))
        original='我 回 答 刚 才 的 题，我 的 答 案 是 REZ，请 判 断 对 不 对。'
        self.assertTrue(self.core._start_study_grade_claim(original,self.client,receipt,self.core.activation))
        claim=self.core._study_grade_claim
        self.assertFalse(claim['task'].done())
        self.assertTrue(self.core._study_grade_output_held())
        await self.settle()
        self.assertTrue(claim.get('relay_written'),claim)
        self.h._agent.answer_evaluate.assert_awaited_once()
        self.assertEqual(self.h._agent.answer_evaluate.call_args.kwargs['answer'],original)
        self.assertEqual(len(self.store.list_qa_records()),1)
        self.assertEqual(self.client.connects,1)
        self.assertEqual([e['type'] for e in self.client.wire],['conversation.item.create','response.create'])
        self.assertEqual(self.client.wire[0]['item']['type'],'message')
        self.assertFalse(any('function_call_output' in json.dumps(e) for e in self.client.wire))
        self.assertEqual(self.core.websocket.events[0]['sdk_speech_correlation_id'],'native_connection_original')
    async def test_question_replaced_after_audio_snapshot_cannot_grade_latest(self):
        receipt=self.capture()
        self.h._state.current_question.update(question_id='new-question',attempt_id='new-attempt')
        await self.h._persist_state()
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,receipt,self.core.activation)
        await self.settle()
        self.h._agent.answer_evaluate.assert_not_awaited()
        self.assertEqual(self.store.list_qa_records(),[])
        self.assertEqual(self.client.connects,0)
    async def test_frame_pin_is_read_once_and_overlap_poison_never_adopts_new_question(self):
        calls=[];read=self.client.get_study_question_pin
        self.client.get_study_question_pin=lambda:(calls.append(True),read())[1]
        self.client._capture_study_grade_pin(True,10)
        self.h._state.current_question.update(question_id='new-question',attempt_id='new-attempt')
        await self.h._persist_state()
        self.client._capture_study_grade_pin(True,10.1)
        self.assertEqual(len(calls),1)
        self.client._capture_study_grade_pin(True,12)
        first=self.client._take_study_grade_asr(self.client.ws,1)
        self.assertIsNone(first['pin'])
        self.client._capture_study_grade_pin(True,12.1)
        self.assertIsNone(self.client._take_study_grade_asr(self.client.ws,1)['pin'])
        self.assertEqual(len(calls),1)
    async def test_ordinary_intent_stale_scope_and_missing_pin_have_no_paid_grade(self):
        receipt=self.capture()
        self.assertFalse(self.core._start_study_grade_claim('请解释这张图对不对。',self.client,receipt,self.core.activation))
        self.client._tool_scope_generation+=1
        self.assertFalse(self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,receipt,self.core.activation))
        self.h._agent.answer_evaluate.assert_not_awaited()
    async def test_new_speech_during_grade_keeps_commit_but_suppresses_late_relay(self):
        original=self.h.model
        async def changed(**kwargs):
            result=await original(**kwargs)
            self.client._voice_handoff_input_sequence+=1
            return result
        self.h._agent.answer_evaluate.side_effect=changed
        receipt=self.capture()
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,receipt,self.core.activation)
        await self.settle()
        self.assertEqual(len(self.store.list_qa_records()),1)
        self.assertEqual(self.client.connects,0)
        self.assertEqual(self.client.wire,[])

    async def test_actual_transcript_admission_reaches_background_grade_without_waiting(self):
        receipt=self.capture();entered=asyncio.Event();release=asyncio.Event();model=self.h.model
        async def delayed(**kwargs):
            entered.set();await release.wait();return await model(**kwargs)
        self.h._agent.answer_evaluate.side_effect=delayed
        accepted=self.core._make_study_input_handler(self.client)
        text='我回答刚才的题，我的答案是 REZ，请评分。'
        self.assertTrue(await asyncio.wait_for(accepted(text,source_game_route_identity=None,
            study_input_owner=receipt),1))
        await asyncio.wait_for(entered.wait(),1)
        self.assertFalse(self.core._study_grade_claim['task'].done())
        self.assertEqual(self.core.sync_message_queue.get_nowait()['data']['data'],text)
        release.set();await self.settle()
        self.assertEqual(len(self.store.list_qa_records()),1)

    async def test_actual_route_and_echo_rejection_precede_claim(self):
        receipt=self.capture();accepted=self.core._make_study_input_handler(self.client)
        text='我回答刚才的题，我的答案是 REZ，请评分。'
        self.assertFalse(await accepted(text,source_game_route_identity=('game','old','route'),study_input_owner=receipt))
        self.core._should_suppress_dirty_voice_transcript=lambda text:True
        self.assertFalse(await accepted(text,source_game_route_identity=None,study_input_owner=receipt))
        self.assertFalse(hasattr(self.core,'_study_grade_claim'))
        self.h._agent.answer_evaluate.assert_not_awaited()

    async def test_one_failed_reconnect_keeps_grade_and_reports_honestly(self):
        async def fail():raise ConnectionError('offline')
        self.client.before_connect=fail
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        self.assertEqual(len(self.store.list_qa_records()),1)
        self.assertEqual(self.client.connects,1)
        self.assertEqual(self.client.wire,[])
        self.assertTrue(any('正式成绩已保存' in e.get('message','') for e in self.core.websocket.events))

    async def test_provider_grade_during_local_grade_joins_original_result(self):
        entered=asyncio.Event();release=asyncio.Event();model=self.h.model
        async def delayed(**kwargs):
            entered.set();await release.wait();return await model(**kwargs)
        self.h._agent.answer_evaluate.side_effect=delayed
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await asyncio.wait_for(entered.wait(),1)
        joined=asyncio.create_task(self.core._on_tool_call(ToolCall(name='study_answer',arguments={'answer':'duplicate'},
            call_id='provider-real-call'),invoking_session=self.client))
        await asyncio.sleep(0)
        release.set();result=await joined;await self.settle()
        self.assertEqual(result.call_id,'provider-real-call')
        self.h._agent.answer_evaluate.assert_awaited_once()
        self.assertEqual(len(self.store.list_qa_records()),1)

    async def test_new_input_at_wire_prevents_late_send_and_does_not_close_new_owner(self):
        async def new_input(event):self.client._voice_handoff_input_sequence+=1
        self.client.before_send=new_input
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        self.assertEqual(len(self.store.list_qa_records()),1)
        self.assertEqual(self.client.wire,[])
        self.assertEqual(self.client.closes,1) # Initial owned close only.

    async def test_controlled_relay_cannot_regrade_or_create_unsolicited_new_quiz(self):
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        result=await self.core._on_tool_call(ToolCall(name='study_answer',arguments={'answer':'regrade'},
            call_id='relay-real-call'),invoking_session=self.client)
        self.assertEqual(result.call_id,'relay-real-call');self.assertEqual(result.output['verdict'],'wrong')
        quiz=await self.core._on_tool_call(ToolCall(name='study_quiz',arguments={},call_id='relay-quiz'),invoking_session=self.client)
        self.assertTrue(quiz.is_error);self.assertEqual(quiz.output['error'],'explicit_answer_is_being_graded')
        self.h._agent.answer_evaluate.assert_awaited_once()

    async def test_explicit_correction_uses_new_attempt_and_retains_original_wrong(self):
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        wrong=self.store.list_qa_records()[0]
        self.client._tool_scope_generation+=1;self.client._voice_handoff_input_sequence+=1
        self.core._start_study_grade_claim('我纠正刚才那道题，我的答案改为 WEX，请重新评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        rows=self.store.list_qa_records()
        self.assertEqual(len(rows),2)
        self.assertIn(wrong,rows)
        self.assertEqual(self.core._study_grade_claim['intent'],'correction')
        self.assertNotEqual(self.core._study_grade_claim['result']['attempt_id'],'attempt-owned')
        self.assertEqual(self.h._agent.answer_evaluate.await_count,2)

    async def test_pre_asr_activation_socket_and_foreign_scope_cannot_rebind_old_audio(self):
        for change in ('activation','socket','scope'):
            with self.subTest(change=change):
                self.client._study_grade_pin=None
                self.client._capture_study_grade_pin(True,10)
                if change=='activation':self.core.activation=('new-lease',2)
                elif change=='socket':self.core.websocket=Socket()
                else:self.client._tool_scope_generation+=1
                receipt=self.client._take_study_grade_asr(self.client.ws,self.client._connection_generation)
                self.assertIsNone(receipt['pin'])
                await self.core._make_study_input_handler(self.client)(
                    '我回答刚才的题，我的答案是 REZ，请评分。',source_game_route_identity=None,study_input_owner=receipt)
                await self.settle()
                self.h._agent.answer_evaluate.assert_not_awaited()
        self.assertEqual(self.store.list_qa_records(),[])

    async def test_only_explicit_protocol_scope_advance_keeps_input_pin(self):
        self.client._capture_study_grade_pin(True,10)
        self.client._advance_study_grade_ingress_scope();self.client._tool_scope_generation+=1
        self.assertIsNotNone(self.client._take_study_grade_asr(self.client.ws,1)['pin'])
        self.client._capture_study_grade_pin(True,11)
        self.client._advance_study_grade_ingress_scope();self.client._tool_scope_generation+=1
        self.client._advance_study_grade_ingress_scope();self.client._tool_scope_generation+=1
        self.assertIsNone(self.client._take_study_grade_asr(self.client.ws,1)['pin'])

    async def test_unknown_question_on_owned_input_is_muted_and_reports_no_grade(self):
        self.client.get_study_question_pin=lambda:None
        receipt=self.capture()
        self.assertTrue(self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,receipt,self.core.activation))
        await self.settle()
        self.h._agent.answer_evaluate.assert_not_awaited()
        self.assertTrue(self.core._study_grade_output_held())
        self.assertTrue(any('这次没有评分' in e.get('message','') for e in self.core.websocket.events))
        self.client._tool_scope_generation+=1
        self.assertFalse(self.core._study_grade_output_held())

    async def test_new_frames_before_claim_cannot_install_hold_for_old_asr(self):
        receipt=self.capture();self.client._voice_handoff_input_sequence+=1
        self.assertFalse(self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,receipt,self.core.activation))
        self.assertFalse(self.core._study_grade_output_held())

    async def test_actual_lanlan_profile_uses_owned_item_driven_relay(self):
        capabilities=importlib.import_module('grade_protocol._protocol_capabilities')
        self.client.capabilities=capabilities.LANLAN_APP_REALTIME_PROTOCOL_CAPABILITIES
        self.core._start_study_grade_claim('我回答刚才的题，我的答案是 REZ，请评分。',self.client,self.capture(),self.core.activation)
        await self.settle()
        self.assertTrue(self.core._study_grade_claim.get('relay_written'))
        self.assertEqual([event['type'] for event in self.client.wire],['conversation.item.create'])
        self.assertFalse(self.core._study_grade_output_held())
        self.h._agent.answer_evaluate.assert_awaited_once()


if __name__=='__main__':unittest.main(verbosity=2)
