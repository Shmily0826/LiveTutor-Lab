"""Real tool admission with resumed speech, delayed ASR, replacement and deadlines."""
import asyncio
import os
import time
import types
import unittest
from unittest.mock import patch
from test_neko_late_asr_tool_patch import Harness


class StudySpeechGate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'NEKO_STUDY_SPEECH_GATE': '1'})
        self.env.start()

    def tearDown(self): self.env.stop()

    def host(self):
        h = Harness()
        h._STUDY_SPEECH_QUIET_SECONDS = .08
        h._STUDY_SPEECH_GATE_SECONDS = .35
        return h

    def call(self, identifier='call-one', name='study_explain'):
        return types.SimpleNamespace(name=name, arguments={'question': identifier}, call_id=identifier)

    async def finish(self, h):
        h.release.set()
        await asyncio.gather(*tuple(getattr(h, '_tool_tasks', ())), return_exceptions=True)

    async def test_resumed_speech_supersedes_prefix_and_only_final_call_executes(self):
        h = self.host()
        first = h._start_raw_tool_call(self.call('prefix'), h._capture_tool_task_owner(h.ws))
        await asyncio.sleep(0); h.completed()
        await asyncio.sleep(.02)
        h._last_local_loud_time = time.time() # suffix resumes before quiet threshold
        await asyncio.sleep(.11) # quiet enough, but prefix ASR predates suffix
        self.assertFalse(h.entered.is_set())
        # The recorded final fragment arrived ~9 s after the prefix; keep
        # separate fragments outside the 200 ms adjacency compatibility window.
        await asyncio.sleep(.15)
        final = h._start_raw_tool_call(self.call('full question and final constraints'), h._capture_tool_task_owner(h.ws))
        await asyncio.sleep(0); h.completed()
        await asyncio.gather(first, final)
        self.assertEqual(h.abandoned, ['prefix'])
        await h.entered.wait(); await self.finish(h)
        self.assertEqual([r.call_id for r in h.outputs], ['full question and final constraints'])

    async def test_call_arriving_after_asr_still_waits_for_quiet(self):
        h = self.host(); h.completed()
        started = time.monotonic()
        task = h._start_raw_tool_call(self.call(name='study_point'), h._capture_tool_task_owner(h.ws))
        await asyncio.sleep(.025)
        self.assertFalse(h.entered.is_set())
        await task; await h.entered.wait()
        self.assertGreaterEqual(time.monotonic() - started, .07)
        await self.finish(h)

    async def test_call_just_after_ready_asr_with_new_pcm_keeps_prefix_scope_until_replaced(self):
        h = self.host(); h.completed()
        await asyncio.sleep(.01); h._last_local_loud_time = time.time()
        prefix = h._start_raw_tool_call(self.call('asr-first-prefix'), h._capture_tool_task_owner(h.ws))
        await asyncio.sleep(.12) # beyond old .04/.4-scaled wait; no early release
        self.assertFalse(prefix.done()); self.assertEqual(h.abandoned, [])
        self.assertFalse(h.entered.is_set())
        h.completed(); await prefix
        self.assertEqual(h.abandoned, ['asr-first-prefix']); self.assertFalse(h.entered.is_set())

    async def test_callback_completion_does_not_change_asr_receipt_time(self):
        h = self.host()
        h._late_raw_expected_asr_advance = True
        try: h.note_user_turn_started()
        finally: h._late_raw_expected_asr_advance = False
        h._begin_raw_input_transcript(); received = h._late_raw_transcript_at
        await asyncio.sleep(.01); h._last_local_loud_time = time.time()
        h._finish_raw_input_transcript()
        self.assertEqual(h._late_raw_transcript_at, received)
        task = h._start_raw_tool_call(self.call(), h._capture_tool_task_owner(h.ws))
        await task
        self.assertFalse(h.entered.is_set()); self.assertEqual(len(h.abandoned), 1)

    async def test_reconnect_handoff_foreign_scope_or_new_asr_never_readopts_owner(self):
        for mutation in ('connection', 'handoff', 'foreign', 'new_asr'):
            with self.subTest(mutation=mutation):
                h = self.host(); h.completed()
                task = h._start_raw_tool_call(self.call(), h._capture_tool_task_owner(h.ws))
                await asyncio.sleep(.01)
                if mutation == 'connection': h._connection_generation += 1
                elif mutation == 'handoff': h._native_barge_in_pending = True
                elif mutation == 'foreign': h.note_user_turn_started()
                else: h.completed()
                await task
                self.assertFalse(h.entered.is_set()); self.assertEqual(h.outputs, [])
                self.assertEqual(h._late_raw_tool_pending, [])

    async def test_missing_asr_and_queue_full_never_execute_gated_work(self):
        h = self.host()
        task = h._start_raw_tool_call(self.call(), h._capture_tool_task_owner(h.ws))
        await task; self.assertFalse(h.entered.is_set())
        self.assertEqual(h.abandoned, ['call-one'])
        h._late_raw_tool_pending = [{}] * 16
        full = h._start_raw_tool_call(self.call('over-cap'), h._capture_tool_task_owner(h.ws))
        await full; self.assertFalse(h.entered.is_set())
        self.assertEqual(len(h._late_raw_tool_pending), 16)

    async def test_untranscribed_speech_with_late_call_does_not_bypass_gate(self):
        h = self.host(); h._last_local_loud_time = time.time() - 3
        task = h._start_raw_tool_call(self.call(), h._capture_tool_task_owner(h.ws))
        await task
        self.assertFalse(h.entered.is_set()); self.assertEqual(h.abandoned, ['call-one'])

    async def test_call_arriving_during_handoff_or_fatal_retirement_is_never_executed(self):
        for field in ('_native_barge_in_pending', '_fatal_error_occurred'):
            with self.subTest(field=field):
                h = self.host(); setattr(h, field, True)
                task = h._start_raw_tool_call(self.call(), h._capture_tool_task_owner(h.ws))
                await task
                self.assertFalse(h.entered.is_set()); self.assertEqual(h.outputs, [])
                self.assertEqual(h.abandoned, ['call-one'])

    async def test_fast_and_slow_siblings_queued_at_different_times_send_one_batch(self):
        h = self.host(); h.completed(); batches = []
        # Use the real ToolResult shape expected by the original collector.
        from test_neko_late_asr_tools import ToolResult
        async def execute(call):
            if call.call_id == 'slow': await h.release.wait()
            return ToolResult(call.call_id, call.name, {'ok': True})
        async def send(results, **kwargs):
            batches.append([r.call_id for r in results]); h.outputs.extend(results)
        h._execute_tool_call = execute; h._send_tool_results_openai_realtime = send
        first = h._start_raw_tool_call(self.call('fast', 'study_point'), h._capture_tool_task_owner(h.ws), response_id='one-response')
        await asyncio.sleep(.025)
        second = h._start_raw_tool_call(self.call('slow'), h._capture_tool_task_owner(h.ws), response_id='one-response')
        await asyncio.gather(first, second)
        await asyncio.sleep(.02)
        self.assertEqual(batches, [])
        await self.finish(h)
        self.assertEqual(len(batches), 1); self.assertEqual(set(batches[0]), {'fast','slow'})

    async def test_known_gated_call_and_later_read_only_sibling_share_one_batch(self):
        h = self.host(); h.completed(); batches = []
        from test_neko_late_asr_tools import ToolResult
        async def execute(call):
            if call.name == 'study_explain': await h.release.wait()
            return ToolResult(call.call_id, call.name, {'ok': True})
        async def send(results, **kwargs): batches.append([r.call_id for r in results])
        h._execute_tool_call = execute; h._send_tool_results_openai_realtime = send
        first = h._start_raw_tool_call(self.call('gated'), h._capture_tool_task_owner(h.ws), response_id='mixed')
        await asyncio.sleep(.01)
        second = h._start_raw_tool_call(self.call('read-only', 'study_material'), h._capture_tool_task_owner(h.ws), response_id='mixed')
        await asyncio.sleep(.02); self.assertEqual(batches, [])
        await asyncio.gather(first, second); await self.finish(h)
        self.assertEqual(len(batches), 1); self.assertEqual(set(batches[0]), {'gated','read-only'})

    async def test_same_scope_siblings_keep_original_batch_and_all_four_tools_are_gated(self):
        h = self.host(); h.completed()
        pending = [h._start_raw_tool_call(self.call(str(i), name), h._capture_tool_task_owner(h.ws), response_id='same-response')
                   for i, name in enumerate(('study_explain','study_quiz','study_answer','study_point'))]
        await asyncio.sleep(.01); self.assertFalse(h.entered.is_set())
        await asyncio.gather(*pending); await h.entered.wait(); await self.finish(h)
        self.assertEqual({r.call_id for r in h.outputs}, {'0','1','2','3'})

    async def test_material_and_preference_or_session_changes_also_wait_for_complete_asr(self):
        for name in ('study_material','study_preferences','study_language','study_session','study_code'):
            with self.subTest(name=name):
                h = self.host(); h._last_local_loud_time = time.time() - 3
                task = h._start_raw_tool_call(self.call(name=name), h._capture_tool_task_owner(h.ws))
                await task
                self.assertFalse(h.entered.is_set())
                self.assertEqual(h.abandoned, ['call-one'])

    async def test_opt_in_does_not_hold_non_study_or_old_completed_voice(self):
        for name, old_voice in (('recall_memory', False), ('study_material', True)):
            with self.subTest(name=name, old_voice=old_voice):
                h = self.host()
                if old_voice:
                    h.completed()
                    h._last_local_loud_time = time.time() - 3
                    h._late_raw_transcript_at = time.time() - 2.9
                else:
                    # Same ready ASR, no incomplete input: ordinary native work.
                    h.completed()
                task = h._start_raw_tool_call(self.call(name=name), h._capture_tool_task_owner(h.ws))
                await asyncio.sleep(.01)
                self.assertTrue(h.entered.is_set())
                await self.finish(h)

    async def test_old_prefix_arguments_never_promote_into_final_asr_scope(self):
        for name in ('study_explain', 'study_preferences'):
            with self.subTest(name=name):
                h = self.host(); h.completed()
                h._late_raw_transcript_at = time.time() - 1
                h._last_local_loud_time = time.time()
                prefix = self.call('old partial question or remember=True', name)
                task = h._start_raw_tool_call(prefix, h._capture_tool_task_owner(h.ws))
                await asyncio.sleep(.23) # beyond the neighboring-ASR tolerance
                self.assertFalse(h.entered.is_set())
                h.completed(); await task
                self.assertEqual(h.outputs, [])
                self.assertEqual(h.abandoned, [prefix.call_id])
                self.assertEqual(h._late_raw_tool_pending, [])


if __name__ == '__main__': unittest.main(verbosity=2)
