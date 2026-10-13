"""Observed first-quiz ordering and genuine replacement; actual patched tooling."""
import asyncio
import os
import time
import types
import unittest
from unittest.mock import patch

from test_neko_late_asr_tool_patch import Harness


class FirstAsrOrdering(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'NEKO_STUDY_SPEECH_GATE':'0'})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def host(self):
        h=Harness()
        h._last_local_loud_time=time.time()-2.117
        h._voice_handoff_input_sequence=17
        h._LATE_ASR_TOOL_WAIT_SECONDS=.4
        return h

    def call(self):
        return types.SimpleNamespace(name='study_quiz',arguments={},call_id='observed-quiz')

    async def finish(self,h):
        h.release.set()
        await asyncio.gather(*tuple(getattr(h,'_tool_tasks',())),return_exceptions=True)

    async def test_observed_225ms_first_asr_waits_without_executing_then_sends_once(self):
        h=self.host();older=asyncio.create_task(asyncio.sleep(10));h._track_tool_task(older)
        pending=h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws),response_id='quiz-response')
        await asyncio.sleep(.225)
        self.assertFalse(h.entered.is_set())
        h.completed();await pending;await h.entered.wait()
        self.assertTrue(older.cancelled())
        self.assertEqual(h._tool_scope_generation,2)
        await self.finish(h)
        self.assertEqual([result.call_id for result in h.outputs],['observed-quiz'])
        self.assertEqual(h._late_raw_tool_pending,[])

    async def test_new_speech_foreign_turn_connection_socket_or_second_asr_never_readopts(self):
        for change in ('speech','counter','foreign','connection','socket','second_asr','fatal','handoff'):
            with self.subTest(change=change):
                h=self.host();pending=h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
                await asyncio.sleep(0)
                if change=='speech':h._last_local_loud_time=time.time()
                elif change=='counter':h._voice_handoff_input_sequence+=1
                elif change=='foreign':h.note_user_turn_started()
                elif change=='connection':h._connection_generation+=1
                elif change=='socket':h.ws=object()
                elif change=='fatal':h._fatal_error_occurred=True
                elif change=='handoff':h._native_barge_in_pending=True
                h.completed()
                if change=='second_asr':h.completed()
                await pending
                self.assertFalse(h.entered.is_set());self.assertEqual(h.outputs,[])
                self.assertEqual(h._late_raw_tool_pending,[])

    async def test_missing_asr_or_full_queue_never_enters_paid_work(self):
        h=self.host();h._LATE_ASR_TOOL_WAIT_SECONDS=.03
        await h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
        self.assertFalse(h.entered.is_set());self.assertEqual(h.abandoned,['observed-quiz'])
        h=self.host();h._late_raw_tool_pending=[{}]*16
        await h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
        self.assertFalse(h.entered.is_set());self.assertEqual(h.abandoned,['observed-quiz'])

    async def test_first_input_fence_and_no_asr_hold_across_two_second_boundary(self):
        for age in (1.999,2.000,2.001,2.117):
            for change in ('speech','counter','missing_asr'):
                with self.subTest(age=age,change=change):
                    h=self.host();h._last_local_loud_time=time.time()-age
                    h._LATE_ASR_TOOL_WAIT_SECONDS=.03
                    pending=h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
                    await asyncio.sleep(0)
                    if change=='speech':h._last_local_loud_time=time.time()
                    elif change=='counter':h._voice_handoff_input_sequence+=1
                    if change!='missing_asr':h.completed()
                    await pending
                    self.assertFalse(h.entered.is_set());self.assertEqual(h.outputs,[])

    async def test_foreign_input_before_call_does_not_borrow_first_asr_exception(self):
        h=self.host();h.note_user_turn_started()
        h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
        await h.entered.wait();jobs=tuple(h._tool_tasks)
        h.completed();await asyncio.gather(*jobs,return_exceptions=True)
        self.assertEqual(h.outputs,[])
        self.assertFalse(getattr(h,'_late_raw_tool_pending',None))

    async def test_handoff_or_fatal_arrival_is_rejected_even_with_gate_default_off(self):
        for field in ('_native_barge_in_pending','_fatal_error_occurred'):
            h=self.host();setattr(h,field,True)
            await h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
            self.assertFalse(h.entered.is_set());self.assertEqual(h.abandoned,['observed-quiz'])

    async def test_connection_reuse_does_not_inherit_previous_connection_asr(self):
        h=self.host();h._late_raw_transcript_connection=0;h._late_raw_transcript_at=time.time()-30
        pending=h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
        await asyncio.sleep(0);h.completed();await pending;await h.entered.wait();await self.finish(h)
        self.assertEqual(len(h.outputs),1)

    async def test_later_prefix_is_not_granted_the_first_transcript_exception(self):
        h=self.host();h._late_raw_transcript_connection=1;h._late_raw_transcript_at=time.time()-10
        h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws))
        await h.entered.wait();jobs=tuple(h._tool_tasks)
        h.completed();await asyncio.gather(*jobs,return_exceptions=True)
        self.assertEqual(h.outputs,[])
        # Later-input endpointing is still incomplete; it must not get a fresh
        # scope by borrowing the first-input compatibility exception.
        self.assertFalse(getattr(h,'_late_raw_tool_pending',None))


if __name__=='__main__':
    unittest.main(verbosity=2)
