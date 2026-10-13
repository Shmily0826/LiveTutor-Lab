"""Actual patched tool/event methods with owned fake provider/socket; offline only."""
import ast
import asyncio
import copy
import logging
from pathlib import Path
import types
import unittest
from neko_material_audio_patch import UPGRADES,normalize_material_audio,_EXECUTE_PRIOR,_EXECUTE_ROUTED_PRIOR,_EXECUTE_CURRENT_PRIOR,_EXECUTE_EXPLAIN_PRIOR,_EXECUTE_QUAD_PRIOR,_EXECUTE

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'benchmarks/raw/neko-product-host'

def patched(relative):
    source=(RUNTIME/relative).read_text(encoding='utf-8')
    if relative=='main_logic/core/tool_calling.py':
        source=normalize_material_audio(source)
        for prior in (_EXECUTE_QUAD_PRIOR, _EXECUTE_EXPLAIN_PRIOR, _EXECUTE_CURRENT_PRIOR, _EXECUTE_ROUTED_PRIOR, _EXECUTE_PRIOR):
            if _EXECUTE not in source and source.count(prior)==1:source=source.replace(prior,_EXECUTE,1)
    for before,after in UPGRADES[relative]:
        if after in source:continue
        if source.count(before)!=1:raise RuntimeError('unknown material patch fixture anchor')
        source=source.replace(before,after,1)
    return ast.parse(source)

class Provider:
    def __init__(self):
        self._is_free_proxy=True;self._has_server_vad=False;self._is_gemini=False;self.ws=object()
        self._connection_generation=1;self.scope=1;self._native_output_connection_token='native_connection_old'
        self.closes=0;self.connects=0;self.fail_connect=False;self._native_barge_in_pending=False
        self._fatal_error_occurred=False;self._interrupted=False;self.instructions='existing instructions'
    def _capture_tool_task_owner(self,provider):return (self._connection_generation,self.scope,provider)
    def _tool_task_owner_is_current(self,owner):return owner==(self._connection_generation,self.scope,self.ws)
    def note_user_turn_started(self):
        self.scope+=1;self._study_material_user_epoch=getattr(self,'_study_material_user_epoch',0)+1
    async def close(self):self.closes+=1
    async def connect(self,*args,**kwargs):
        self.connects+=1;self._connection_generation+=1;self.ws=object()
        self._native_output_connection_token='native_connection_new'
        if self.fail_connect:raise RuntimeError('bounded provider refusal')
        self._fatal_error_occurred=False;self._interrupted=False

scope={'asyncio':asyncio,'OmniRealtimeClient':Provider,'ToolCall':object,
       'ToolResult':lambda **kwargs:types.SimpleNamespace(images=[],**kwargs),
       'logger':logging.getLogger('material-audio-test')}
node=next(n for n in patched('main_logic/core/tool_calling.py').body if isinstance(n,ast.ClassDef))
keep=[n for n in node.body if getattr(n,'name','').startswith(('_study_material_native','_valid_study_material','_capture_study_material','_bind_study_material','_apply_study_material','_replace_study_material')) or getattr(n,'name','')=='_on_tool_call']
node.body=keep
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'actual tool_calling.py','exec'),scope)

def context(identity='a',session='s',course='c'):
    return {'course_id':course,'session_id':session,'material_identity':identity*64}
BOOT='a'*32
def record(seq=0,ctx=None):return {'v':1,'boot_id':BOOT,'change_seq':seq,'context':ctx or context()}
def control(seq=1,before=None,after=None,boot=BOOT):return {'v':1,'boot_id':boot,'change_seq':seq,'before':before or context(),'after':after or context('b'),'reason':'image'}

class Harness(scope[node.name]):
    def __init__(self):
        self.session=Provider();self.sent=[];self.is_active=True;self._asr_route_mode='native'
        self._voice_lease_owner='core';self._takeover_active=False;self.generation=5
        self.lanlan_name='OwnedRole';self.dispatched=[]
        async def send(value):self.sent.append(value)
        self.websocket=types.SimpleNamespace(send_json=send)
        self._core_voice_session_swap_lock=asyncio.Lock();self.frames=asyncio.Lock()
        self._core_voice_session_swap_barrier_timeout_s=.04;self._core_voice_listener_cancel_timeout_s=.1
        self._native_activation_reconnect_timeout_s=.15;self.restarts=[];self.statuses=[];self.disconnected=False
        self.definition=types.SimpleNamespace(metadata={'source':'plugin:study_companion'})
        self.result=types.SimpleNamespace(output={'reply':'current answer','degraded':False,'_study_material_binding':record()},is_error=False,images=[])
        async def execute(call):self.dispatched.append(call);return self.result
        self.tool_registry=types.SimpleNamespace(get=lambda name:self.definition,execute=execute)
    def _capture_voice_session_activation_generation(self):return self.generation
    def _ensure_audio_frame_send_lock(self):return self.frames
    async def _restart_message_handler_after_session_reconnect(self,source,**kwargs):self.restarts.append(kwargs);return True
    async def send_status(self,status):self.statuses.append(status)
    async def disconnected_by_server(self,**kwargs):
        # Existing teardown can acquire this barrier; it must be released first.
        self.assert_unlocked=not self._core_voice_session_swap_lock.locked();self.disconnected=True
    async def bind(self,rec=None):
        if rec is not None:self.result.output['_study_material_binding']=rec
        return await self._on_tool_call(types.SimpleNamespace(name='study_explain',call_id='actual-call'),invoking_session=self.session)

class MaterialAudio(unittest.IsolatedAsyncioTestCase):
    async def test_trusted_success_binds_exact_owner_and_strips_provider_provenance(self):
        h=Harness();source=h.session;await h.bind()
        self.assertIs(h._study_material_output_owner['source'],source)
        self.assertEqual(h._study_material_output_owner['record'],record())
        self.assertNotIn('_study_material_binding',h.result.output)
        self.assertEqual(source.connects,0)

    async def test_changed_material_stops_old_token_and_restores_once_without_replaying_audio(self):
        h=Harness();await h.bind();source=h.session
        self.assertTrue(await h._apply_study_material_control(control()))
        self.assertEqual(h.sent,[{'type':'game_route_speech_cancel','sdk_speech_correlation_id':'native_connection_old'}])
        self.assertEqual(source.connects,1);self.assertEqual(source.closes,1)
        self.assertEqual(h.restarts,[{'start_listener':False},{}]);self.assertEqual(source.scope,2)
        self.assertFalse(source._fatal_error_occurred);self.assertFalse(h.disconnected)
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.connects,1)

    async def test_material_event_before_tool_return_is_retained_and_retires_late_bound_answer(self):
        h=Harness();self.assertFalse(await h._apply_study_material_control(control()))
        await h.bind();self.assertEqual(h.session.connects,1);self.assertIsNone(h._study_material_output_owner)

    async def test_missed_intermediate_control_and_late_old_event_do_not_cancel_new_binding(self):
        h=Harness();await h.bind()
        self.assertTrue(await h._apply_study_material_control(control(3,before=context('b'),after=context('c'))))
        h.result=types.SimpleNamespace(output={'reply':'new C','_study_material_binding':record(3,context('c'))},is_error=False,images=[])
        await h.bind();self.assertFalse(await h._apply_study_material_control(control(2,after=context('b'))))
        self.assertFalse(await h._apply_study_material_control(control(4,boot='b'*32)))
        self.assertEqual(h.session.connects,1);self.assertEqual(h._study_material_output_owner['record']['context'],context('c'))

    async def test_picture_only_change_does_not_cancel_explicit_text_but_course_change_does(self):
        h=Harness();expected={'course_id':'c','session_id':'s'};await h.bind(record(ctx=expected))
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertTrue(await h._apply_study_material_control(control(2,after=context('b',course='new'))))

    async def test_replaced_input_connection_socket_activation_or_barge_in_never_cancels_new_owner(self):
        for kind in ('scope','connection','socket','activation','barge','session'):
            with self.subTest(kind=kind):
                h=Harness();await h.bind();old=h.session
                if kind=='scope':old.scope+=1
                elif kind=='connection':old._connection_generation+=1
                elif kind=='socket':h.websocket=object()
                elif kind=='activation':h.generation+=1
                elif kind=='barge':old._native_barge_in_pending=True
                else:h.session=Provider()
                self.assertFalse(await h._apply_study_material_control(control()))
                self.assertEqual(old.connects,0);self.assertEqual(h.sent,[])

    async def test_failure_after_connection_generation_changes_is_closed_and_no_retry(self):
        h=Harness();await h.bind();source=h.session;source.fail_connect=True
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.connects,1);self.assertEqual(source.closes,2)
        self.assertTrue(h.disconnected);self.assertTrue(h.assert_unlocked)
        self.assertTrue(source._fatal_error_occurred);self.assertEqual(len(h.statuses),1)

    async def test_swap_timeout_still_cancels_exact_old_queue_and_stops_without_connect(self):
        h=Harness();await h.bind();await h._core_voice_session_swap_lock.acquire()
        try:
            self.assertFalse(await h._apply_study_material_control(control()))
        finally:h._core_voice_session_swap_lock.release()
        self.assertEqual(h.session.connects,0);self.assertEqual(len(h.sent),1)
        self.assertTrue(h.disconnected)

    async def test_frame_lock_serializes_cancel_and_rechecks_replacement_before_send(self):
        h=Harness();await h.bind();await h.frames.acquire();source=h.session
        task=asyncio.create_task(h._apply_study_material_control(control()));await asyncio.sleep(.01)
        self.assertEqual(h.sent,[]);h.session=Provider();h.frames.release()
        self.assertFalse(await task);self.assertEqual(h.sent,[]);self.assertEqual(source.closes,0)
        self.assertFalse(h.session._fatal_error_occurred)

    async def test_untrusted_failed_or_malformed_binding_cannot_attach_to_output(self):
        for kind in ('foreign','error','degraded','bad-version','bad-context'):
            with self.subTest(kind=kind):
                h=Harness()
                if kind=='foreign':h.definition.metadata={'source':'plugin:other'}
                elif kind=='error':h.result.is_error=True
                elif kind=='degraded':h.result.output['degraded']=True
                elif kind=='bad-version':h.result.output['_study_material_binding']['v']=True
                else:h.result.output['_study_material_binding']['context']['raw_image']='never accepted'
                await h.bind();self.assertIsNone(getattr(h,'_study_material_output_owner',None))

    async def test_event_control_requires_trusted_targeted_blind_route_and_never_falls_through(self):
        tree=patched('app/main_server/character_runtime.py')
        method=next(n for n in tree.body if getattr(n,'name','')=='_handle_agent_event')
        h=Harness();await h.bind()
        ns={'logger':logging.getLogger('material-event-test'),'_get_session_manager':lambda target:h if target=='role' else None}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual character_runtime.py','exec'),ns)
        base={'event_type':'proactive_message','lanlan_name':'role','source_kind':'plugin','source_name':'study_companion',
              'channel':'plugin:study_companion','ai_behavior':'blind','visibility':[],'metadata':{'study_material_control':control()}}
        for field,value in [('source_name','other'),('source_kind','agent'),('channel','wrong'),('lanlan_name',''),('visibility',['chat']),('ai_behavior','respond')]:
            changed=copy.deepcopy(base);changed[field]=value;await ns['_handle_agent_event'](changed)
        self.assertEqual(h.session.connects,0)
        await ns['_handle_agent_event'](base);self.assertEqual(h.session.connects,1)

    async def test_actual_batch_owner_is_retained_instead_of_recapturing_wrong_turn_pair(self):
        h=Harness();source=h.session;owner=source._capture_tool_task_owner(source.ws)
        source._tool_batch_entry_by_task={asyncio.current_task():types.SimpleNamespace(
            call=types.SimpleNamespace(call_id='actual-call'),owner=owner,abandoned=False)}
        source._capture_tool_task_owner=lambda provider:('wrong live turn-pair',)
        await h.bind();self.assertIs(h._study_material_output_owner['tool_owner'],owner)
        self.assertTrue(await h._apply_study_material_control(control()))

    async def test_tool_retirement_cancels_binding_caller_but_independent_swap_completes(self):
        h=Harness();source=h.session;await h._apply_study_material_control(control())
        entered=asyncio.Event();release=asyncio.Event();connect=source.connect
        async def slow_connect(*args,**kwargs):
            entered.set();await release.wait();await connect(*args,**kwargs)
        source.connect=slow_connect
        source.note_user_turn_started=lambda:asyncio.current_task().cancel()
        caller=asyncio.create_task(h.bind());await asyncio.gather(caller,return_exceptions=True)
        self.assertTrue(caller.cancelled());await entered.wait()
        swap=source._study_material_replace_task;self.assertFalse(swap.cancelled())
        release.set();self.assertTrue(await swap);self.assertEqual(source.connects,1)
        self.assertFalse(source._fatal_error_occurred)

    async def test_same_connection_new_input_while_waiting_frame_lock_stops_old_swap(self):
        h=Harness();await h.bind();source=h.session;await h.frames.acquire()
        task=asyncio.create_task(h._apply_study_material_control(control()));await asyncio.sleep(.01)
        self.assertTrue(h._study_material_native_output_held());self.assertFalse(source._fatal_error_occurred)
        source.note_user_turn_started();h.frames.release()
        self.assertFalse(await task);self.assertEqual(h.sent,[]);self.assertEqual(source.closes,0)
        self.assertEqual(source.connects,0);self.assertFalse(h.disconnected)
        self.assertFalse(source._fatal_error_occurred);self.assertFalse(source._interrupted)
        self.assertFalse(h._study_material_native_output_held())

    async def test_late_listener_restart_cannot_mark_new_input_restored(self):
        h=Harness();await h.bind();source=h.session;h.session_closed_by_server=True
        async def restart(session,**kwargs):
            if not kwargs:source.note_user_turn_started()
            return True
        h._restart_message_handler_after_session_reconnect=restart
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertTrue(h.session_closed_by_server);self.assertFalse(h.disconnected)

    async def test_actual_user_epoch_changes_only_on_user_note_not_provider_scope_retirement(self):
        tree=patched('main_logic/omni_realtime_client/_tools.py')
        tools=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_ToolingMixin')
        method=next(n for n in tools.body if getattr(n,'name','')=='note_user_turn_started')
        ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual note_user_turn_started','exec'),ns)
        provider=Provider();provider._advance_tool_scope=lambda:setattr(provider,'scope',provider.scope+1)
        ns['note_user_turn_started'](provider);self.assertEqual(provider._study_material_user_epoch,1)
        provider._advance_tool_scope();self.assertEqual(provider._study_material_user_epoch,1)

    async def test_connection_replaced_during_listener_drain_is_not_reconnected_or_closed(self):
        h=Harness();await h.bind();source=h.session
        async def restart(session,**kwargs):
            source._connection_generation+=1;source._fatal_error_occurred=False;source._interrupted=False
            return True
        h._restart_message_handler_after_session_reconnect=restart
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.connects,0);self.assertEqual(source.closes,1);self.assertFalse(h.disconnected)
        self.assertFalse(source._fatal_error_occurred)

    async def test_connection_replaced_during_connect_is_not_adopted_or_closed(self):
        h=Harness();await h.bind();source=h.session;original=source.connect
        async def replaced(*args,**kwargs):
            await original(*args,**kwargs);source._connection_generation+=1
        source.connect=replaced
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.closes,1);self.assertFalse(h.disconnected)

    async def test_actual_delivery_gate_holds_old_native_output_and_allows_new_input_or_tts(self):
        h=Harness();source=h.session
        tree=patched('main_logic/core/tts_lifecycle.py')
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        method=next(n for n in cls.body if getattr(n,'name','')=='_tts_output_is_current')
        ns={'tts_output_runtime':types.SimpleNamespace(get=lambda:None)}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual tts_lifecycle.py','exec'),ns)
        h._tts_runtime_is_current=lambda runtime:True
        source._study_material_output_hold={'connection':1,'user_epoch':0}
        self.assertFalse(ns['_tts_output_is_current'](h))
        source.note_user_turn_started();self.assertTrue(ns['_tts_output_is_current'](h))
        source._study_material_output_hold['user_epoch']=1;h.use_tts=True
        self.assertTrue(ns['_tts_output_is_current'](h))

    async def test_connection_replaced_during_cancel_delivery_is_not_closed(self):
        h=Harness();await h.bind();source=h.session
        async def send(payload):
            h.sent.append(payload);source._connection_generation+=1
            source._fatal_error_occurred=False;source._interrupted=False
        h.websocket.send_json=send
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.closes,0);self.assertEqual(source.connects,0)
        self.assertFalse(source._fatal_error_occurred);self.assertFalse(h.disconnected)

    async def test_cleanup_status_delivery_cannot_disconnect_replacement_connection(self):
        h=Harness();await h.bind();source=h.session;source.fail_connect=True
        async def status(payload):
            h.statuses.append(payload);source._connection_generation+=1
            source._fatal_error_occurred=False;source._interrupted=False
        h.send_status=status
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.closes,2);self.assertFalse(h.disconnected)
        self.assertFalse(source._fatal_error_occurred)

    async def test_new_input_after_irreversible_cancel_on_same_connection_requires_explicit_restart(self):
        h=Harness();await h.bind();source=h.session
        async def send(payload):
            h.sent.append(payload);source.note_user_turn_started()
        h.websocket.send_json=send
        self.assertFalse(await h._apply_study_material_control(control()))
        self.assertEqual(source.closes,1);self.assertEqual(source.connects,0)
        self.assertTrue(h.disconnected);self.assertTrue(source._fatal_error_occurred)
        self.assertEqual(len(h.statuses),1);self.assertFalse(h._study_material_native_output_held())

    async def test_dispatch_uses_trusted_role_without_mutating_model_arguments_or_cross_plugin(self):
        h=Harness();original={'question':'same material','_ctx':{'lanlan_name':'model-guessed-role','run_id':'guessed'}}
        call=types.SimpleNamespace(name='study_explain',call_id='actual-call',arguments=original)
        await h._on_tool_call(call,invoking_session=h.session)
        self.assertIsNot(h.dispatched[0],call);self.assertIs(call.arguments,original)
        self.assertEqual(original['_ctx']['lanlan_name'],'model-guessed-role')
        self.assertEqual(h.dispatched[0].arguments['_ctx'],{'lanlan_name':'OwnedRole'})
        h.definition.metadata={'source':'plugin:other'}
        await h._on_tool_call(call,invoking_session=h.session)
        self.assertIs(h.dispatched[1],call)

    async def test_native_output_binding_is_independent_of_microphone_lease_and_vad(self):
        for route,lease,vad in [('native','none',False),('independent','core',True)]:
            with self.subTest(route=route,lease=lease,vad=vad):
                h=Harness();h._asr_route_mode=route;h._voice_lease_owner=lease;h.session._has_server_vad=vad
                await h.bind();self.assertIsNotNone(h._study_material_output_owner)
                self.assertTrue(await h._apply_study_material_control(control()))
                self.assertEqual(h.session.connects,1)

    async def test_current_trusted_role_routes_even_when_native_output_cannot_be_captured(self):
        for reason in ('no_token', 'takeover', 'tts', 'abandoned'):
            with self.subTest(reason=reason):
                h=Harness()
                if reason=='no_token':h.session._native_output_connection_token=''
                elif reason=='takeover':h._takeover_active=True
                elif reason=='tts':h.use_tts=True
                else:h.session._tool_batch_entry_by_task={asyncio.current_task():types.SimpleNamespace(
                    call=types.SimpleNamespace(call_id='actual-call'),owner=None,abandoned=True)}
                call=types.SimpleNamespace(name='study_explain',call_id='actual-call',arguments={'question':'literal'})
                await h._on_tool_call(call,invoking_session=h.session)
                self.assertEqual(h.dispatched[0].arguments['_ctx'],{'lanlan_name':'OwnedRole'})
                self.assertNotIn('_ctx',call.arguments)
                self.assertNotIn('_study_material_binding',h.result.output)
                self.assertIsNone(getattr(h,'_study_material_output_owner',None))

    async def test_private_binding_removed_for_failed_or_string_result_without_native_capture(self):
        for kind in ('failed','string'):
            h=Harness();h.use_tts=True
            if kind=='failed':h.result.is_error=True
            else:h.result.output=__import__('json').dumps(h.result.output)
            await h.bind()
            self.assertNotIn('_study_material_binding',h.result.output)
            self.assertEqual(h.result.output['reply'],'current answer')
            self.assertIsNone(getattr(h,'_study_material_output_owner',None))

    async def test_quiz_question_field_and_answer_summary_reply_bind_their_own_scope(self):
        for name in ('study_quiz','study_answer','study_summary'):
            with self.subTest(name=name):
                h=Harness()
                if name=='study_quiz':
                    h.result.output.pop('reply');h.result.output['question']='Which module calls NUD?'
                call=types.SimpleNamespace(name=name,call_id='actual-call',arguments={})
                await h._on_tool_call(call,invoking_session=h.session)
                self.assertEqual(h._study_material_output_owner['tool_name'],name)
                self.assertEqual(h.dispatched[0].arguments['_ctx'],{'lanlan_name':'OwnedRole'})
                self.assertNotIn('_study_material_binding',h.result.output)
                self.assertTrue(await h._apply_study_material_control(control()))
                self.assertEqual(h.session.connects,1)

    async def test_quiz_reply_only_cannot_bind_or_claim_a_question(self):
        h=Harness();call=types.SimpleNamespace(name='study_quiz',call_id='actual-call',arguments={})
        await h._on_tool_call(call,invoking_session=h.session)
        self.assertIsNone(getattr(h,'_study_material_output_owner',None))
        self.assertNotIn('_study_material_binding',h.result.output)

    async def test_other_readonly_study_result_is_not_a_teaching_binding(self):
        h=Harness();call=types.SimpleNamespace(name='study_material',call_id='actual-call',arguments={})
        await h._on_tool_call(call,invoking_session=h.session)
        self.assertIsNone(getattr(h,'_study_material_output_owner',None))
        self.assertIs(h.dispatched[0],call)
        self.assertIn('_study_material_binding',h.result.output)

    async def test_stale_or_absent_source_never_gets_manager_role(self):
        for source in (None,Provider()):
            h=Harness();call=types.SimpleNamespace(name='study_explain',call_id='actual-call',arguments={'_ctx':{'lanlan_name':'ForgedRole'}})
            result=await h._on_tool_call(call,invoking_session=source)
            if source is None:
                self.assertEqual(h.dispatched[0].arguments['_ctx'],{'lanlan_name':''})
            else:
                self.assertEqual(h.dispatched,[]);self.assertTrue(result.is_error)
                self.assertEqual(result.output['error'],'stale_study_role_scope')
            self.assertEqual(call.arguments['_ctx'],{'lanlan_name':'ForgedRole'})

    async def test_input_route_or_lease_change_and_tts_takeover_cannot_be_retired_by_old_binding(self):
        for mutation in ('route','lease','tts','takeover'):
            with self.subTest(mutation=mutation):
                h=Harness();await h.bind()
                if mutation=='route':h._asr_route_mode='independent'
                elif mutation=='lease':h._voice_lease_owner='game'
                elif mutation=='tts':h.use_tts=True
                else:h._takeover_active=True
                self.assertFalse(await h._apply_study_material_control(control()))
                self.assertEqual(h.sent,[]);self.assertEqual(h.session.connects,0)

if __name__=='__main__':unittest.main(verbosity=2)
