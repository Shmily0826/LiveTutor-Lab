"""Real owner/batch execution with simultaneous distinct provider call ids, offline."""
import asyncio
import os
import types
import unittest
from unittest.mock import patch
from test_neko_late_asr_tool_patch import Harness
from test_neko_late_asr_tools import ToolResult

class StudySingleflight(unittest.IsolatedAsyncioTestCase):
    def setUp(self):self.env=patch.dict(os.environ,{'NEKO_STUDY_SPEECH_GATE':'1'});self.env.start()
    def tearDown(self):self.env.stop()
    def host(self):
        h=Harness();h.completed();h.executed=[];h.batches=[]
        async def execute(call):
            h.executed.append(call.call_id);h.entered.set();await h.release.wait()
            return ToolResult(call.call_id,call.name,{'ok':True,'reply':'one actual result','nested':[]})
        async def send(results,**kwargs):
            h.batches.append([r.call_id for r in results]);h.outputs.extend(results)
        h._execute_tool_call=execute;h._send_tool_results_openai_realtime=send
        return h
    def call(self,h,identifier,arguments=None,name='study_explain'):
        call=types.SimpleNamespace(call_id=identifier,name=name,arguments=arguments or {'question':'same final input','language':'en-US'})
        return h._start_raw_tool_call_now(call,h._capture_tool_task_owner(h.ws),response_id='response-'+identifier)
    async def drain(self,h):
        h.release.set();await asyncio.gather(*tuple(h._tool_tasks),return_exceptions=True)
    async def test_identical_inflight_calls_share_backend_but_keep_ids_batches_and_payload_isolation(self):
        h=self.host();self.call(h,'first');await h.entered.wait()
        self.call(h,'second',{'language':'en-US','question':'same final input'});self.call(h,'third')
        await asyncio.sleep(.01);self.assertEqual(h.executed,['first'])
        await self.drain(h)
        self.assertEqual({r.call_id for r in h.outputs},{'first','second','third'})
        self.assertEqual(len(h.batches),3) # no unknown-response alias
        h.outputs[1].output['nested'].append('changed')
        self.assertEqual(sum(bool(r.output['nested']) for r in h.outputs),1)
        self.assertEqual(h._study_explanation_inflight,{})
    async def test_different_arguments_and_side_effecting_tools_are_not_shared(self):
        for names,args in [(('study_explain','study_explain'),({'question':'one'},{'question':'two'})),
                           (('study_quiz','study_quiz'),({'topic':'same'},{'topic':'same'})),
                           (('study_preferences','study_preferences'),({'remember':True},{'remember':True}))]:
            with self.subTest(names=names):
                h=self.host();self.call(h,'one',args[0],names[0]);self.call(h,'two',args[1],names[1])
                await asyncio.sleep(.01);self.assertEqual(len(h.executed),2);await self.drain(h)
    async def test_follower_cancel_does_not_cancel_original_work(self):
        h=self.host();original=self.call(h,'original');await h.entered.wait()
        follower=self.call(h,'follower');await asyncio.sleep(.01);follower.cancel()
        await asyncio.gather(follower,return_exceptions=True)
        self.assertFalse(original.cancelled());self.assertEqual(h.executed,['original'])
        await self.drain(h)
        self.assertEqual([r.call_id for r in h.outputs],['original'])
        self.assertEqual(h._study_explanation_inflight,{})
    async def test_new_input_or_connection_never_receives_retired_shared_payload(self):
        for mutation in ('input','connection','session'):
            with self.subTest(mutation=mutation):
                h=self.host();self.call(h,'old');await h.entered.wait();self.call(h,'old-copy');await asyncio.sleep(.01)
                if mutation=='input':h.completed()
                elif mutation=='connection':h._connection_generation+=1;h.ws=object();h.note_user_turn_started()
                else:h.ws=object();h.note_user_turn_started()
                await self.drain(h)
                self.assertEqual(h.outputs,[]);self.assertEqual(h._study_explanation_inflight,{})
    async def test_finished_answers_are_not_cached_for_material_changes_or_followups(self):
        h=self.host();self.call(h,'first');await h.entered.wait();await self.drain(h)
        self.call(h,'later');await asyncio.sleep(.01);await self.drain(h)
        self.assertEqual(h.executed,['first','later'])
        self.assertEqual([r.call_id for r in h.outputs],['first','later'])
    async def test_failure_is_shared_as_failure_and_does_not_leave_pending_work(self):
        h=self.host()
        async def fail(call):
            h.executed.append(call.call_id);h.entered.set();await h.release.wait()
            return ToolResult(call.call_id,call.name,{'error':'provider unavailable'},True,'provider unavailable')
        h._execute_tool_call=fail;self.call(h,'first');await h.entered.wait();self.call(h,'second');await asyncio.sleep(.01)
        await self.drain(h)
        self.assertEqual(h.executed,['first']);self.assertTrue(all(r.is_error for r in h.outputs))
        self.assertEqual(h._study_explanation_inflight,{})
    async def test_opt_out_other_routes_server_vad_or_unready_asr_keep_original_execution(self):
        for mutation in ('off','route','vad','asr'):
            with self.subTest(mutation=mutation):
                h=self.host()
                if mutation=='route':h._realtime_protocol_capabilities.route_key='other'
                elif mutation=='vad':h._has_server_vad=True
                elif mutation=='asr':h._late_raw_transcript_ready_scope=None
                with patch.dict(os.environ,{'NEKO_STUDY_SPEECH_GATE':'0' if mutation=='off' else '1'}):
                    self.call(h,'one');self.call(h,'two');await asyncio.sleep(.01)
                    self.assertEqual(len(h.executed),2);await self.drain(h)

if __name__=='__main__':unittest.main(verbosity=2)
