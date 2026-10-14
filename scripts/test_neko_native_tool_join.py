"""Isolated native tool continuation, using actual tool tasks and queue transport."""
import ast
import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import test_neko_native_audio_dispatch as audio
import neko_voice_host_patch as canonical
import neko_native_tool_join_patch as join
from main_logic.omni_realtime_client import OmniRealtimeClient
from main_logic.tool_calling import ToolResult
from test_neko_native_barge_in import ActivationGeneration, QueueSocket


def staged_sources():
    targets, replay = (canonical.TARGETS, canonical._OWNER_TRACE_REPLAY)
    if not getattr(canonical, '_NATIVE_TOOL_JOIN_PATCHED', False):
        targets, replay = join.upgrade_targets(targets, replay)
    sources = {}
    with tempfile.TemporaryDirectory() as directory, patch.object(canonical, 'TARGETS', targets), \
            patch.object(canonical, '_OWNER_TRACE_REPLAY', replay), \
            patch.object(canonical, 'normalize_ordering_helpers', join.normalize_ordering_helpers):
        for name in ('_response_arbiter.py', '_transport.py', '_tools.py'):
            relative = Path('main_logic/omni_realtime_client') / name
            path = Path(directory) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((audio.HOST / relative).read_bytes())
            canonical.apply_to(path)
            sources[name] = path.read_text(encoding='utf-8')
            ast.parse(sources[name])
            assert canonical.state(path) == 'patched'
            assert canonical.apply_to(path) == 'already patched'
    return sources


SOURCES = staged_sources()


def module(name, source):
    result = types.ModuleType('main_logic.omni_realtime_client.' + name)
    sys.modules[result.__name__] = result
    exec(compile(source, name, 'exec'), result.__dict__)
    return result


ARBITER = module('_draft_tool_join_arbiter', SOURCES['_response_arbiter.py'])
TOOLS = module('_draft_tool_join_tools', SOURCES['_tools.py'])
TRANSPORT = module('_draft_tool_join_transport', SOURCES['_transport.py'])
METHODS = ('_capture_tool_task_owner', '_start_raw_tool_call', '_start_raw_tool_call_now',
           '_close_unanswered_tool_calls', '_send_tool_results_openai_realtime', '_answer_raw_tool_batch')


class NativeToolJoin(audio.AutomaticAudio):
    # Do not inherit the phase40 known-blocker assertion or repeat unrelated cases.
    async def asyncSetUp(self):
        self.join_patches = [patch.object(audio, 'DRAFT', ARBITER),
            patch.object(OmniRealtimeClient, 'handle_messages', TRANSPORT._TransportMixin.handle_messages)] + [
            patch.object(OmniRealtimeClient, name, getattr(TOOLS._ToolingMixin, name)) for name in METHODS]
        for item in self.join_patches:
            item.start()
        await super().asyncSetUp()
        self.calls = []
        self.tasks = []
        self.origins = []
        actual_start = self.client._start_raw_tool_call
        actual_now = self.client._start_raw_tool_call_now
        def start(call, owner, **kwargs):
            task = actual_start(call, owner, **kwargs)
            self.tasks.append(task)
            return task
        def now(call, owner, **kwargs):
            self.origins.append(owner.native_audio_origin)
            return actual_now(call, owner, **kwargs)
        self.client._start_raw_tool_call = start
        self.client._start_raw_tool_call_now = now
        async def handler(call):
            self.calls.append(call.call_id)
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': '方向是哪边？'})
        self.client.on_tool_call = handler

    async def asyncTearDown(self):
        for task in self.tasks + list(getattr(self.client, '_tool_tasks', ())):
            if not task.done():
                task.cancel()
        await asyncio.gather(*(self.tasks + list(getattr(self.client, '_tool_tasks', ()))), return_exceptions=True)
        try:
            await super().asyncTearDown()
        finally:
            for item in reversed(self.join_patches):
                item.stop()

    def function(self, call_id='tool-1', response_id='function-proxy-id'):
        self.socket.feed({'type': 'response.function_call_arguments.done', 'name': 'study_quiz',
                          'call_id': call_id, 'response_id': response_id, 'arguments': '{}'})

    def outputs(self):
        return [event for event in self.socket.sent if event['type'] == 'conversation.item.create'
                and event.get('item', {}).get('type') == 'function_call_output']

    async def complete(self, identity='actual-audio'):
        self.content(identity)
        await self.settle(lambda: self.client._current_response_id == identity)
        self.done(identity)
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)

    async def test_actual_provider_tool_task_returns_inside_native_slot_then_audio_finishes(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        ticket = arbiter._current.ticket
        sequence = self.client._voice_handoff_input_sequence
        self.function()
        self.done('parent-different-from-function')
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.calls, ['tool-1'])
        self.assertEqual(self.outputs()[0]['item']['call_id'], 'tool-1')
        self.assertFalse(ticket.started.done())
        self.assertIs(arbiter._current.ticket, ticket)
        self.assertEqual(arbiter._queue.qsize(), 0)
        self.assertTrue(self.origins[0] is arbiter._current.native_tool_origin)
        self.assertFalse(any(event['type'] == 'response.create' for event in self.socket.sent))
        await self.complete()
        self.assertTrue(ticket.done.done())
        self.assertEqual(self.client._voice_handoff_response_input_sequence, sequence)
        self.assertFalse(self.client._voice_handoff_input_open)
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_parallel_actual_tool_tasks_each_write_once_without_second_response_ticket(self):
        await self.phrase()
        await self.finish_writer()
        self.function('parallel-1')
        self.function('parallel-2')
        self.done('parent-terminal')
        await self.settle(lambda: len(self.outputs()) == 2)
        self.assertEqual(sorted(self.calls), ['parallel-1', 'parallel-2'])
        self.assertEqual(sorted(event['item']['call_id'] for event in self.outputs()), self.calls)
        self.assertIs(self.origins[0], self.origins[1])
        self.assertEqual(self.client._response_arbiter._queue.qsize(), 0)
        await self.complete('parallel-audio')
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_expected_asr_scope_advance_preserves_captured_origin(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        origin = arbiter._current.native_tool_origin
        initial_scope = self.client._tool_scope_generation
        self.client._last_local_loud_time = time.time() - .1
        self.client._late_raw_transcript_at = 0
        self.function('before-asr')
        await self.settle(lambda: bool(getattr(self.client, '_late_raw_tool_pending', ())))
        self.assertFalse(self.outputs())
        self.socket.feed({'type': 'conversation.item.input_audio_transcription.completed', 'transcript': '出一道方向题'})
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.client._tool_scope_generation, initial_scope + 1)
        self.assertIs(self.origins[0], origin)
        await self.complete('after-asr-audio')

    async def test_unknown_or_already_written_call_output_is_not_joined_or_retried(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        self.function('actual')
        await self.settle(lambda: bool(self.outputs()))
        origin = self.origins[0]
        for call_id in ('unknown', 'actual'):
            with self.subTest(call_id=call_id), self.assertRaises(ValueError):
                await arbiter.join_native_tool_results(origin, ({'type': 'conversation.item.create',
                    'item': {'type': 'function_call_output', 'call_id': call_id, 'output': '{}'}},),
                    event_sender=lambda event: None, admission_check=lambda: True)
        self.assertEqual(len(self.outputs()), 1)
        await self.complete()

    async def test_real_tool_wait_beyond_five_seconds_does_not_expire_announcement(self):
        release = asyncio.Event()
        async def slow(call):
            self.calls.append(call.call_id)
            await release.wait()
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': 'fixture'})
        self.client.on_tool_call = slow
        await self.phrase()
        await self.finish_writer()
        ticket = self.client._response_arbiter._current.ticket
        self.function('slow-tool')
        await self.settle(lambda: bool(self.calls))
        await asyncio.sleep(5.05)
        self.assertFalse(ticket.started.done())
        self.assertFalse(ticket.done.done())
        self.assertFalse(self.client._fatal_error_occurred)
        release.set()
        await self.settle(lambda: bool(self.outputs()))
        await self.complete('slow-tool-audio')

    async def test_new_pcm_while_tool_runs_cannot_receive_old_result_or_boundary(self):
        release = asyncio.Event()
        async def slow(call):
            self.calls.append(call.call_id)
            await release.wait()
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': 'old'})
        self.client.on_tool_call = slow
        await self.phrase()
        await self.finish_writer()
        self.function()
        await self.settle(lambda: bool(self.calls))
        old = self.client._voice_handoff_input_sequence
        await self.frame(True, 81)
        self.assertGreater(self.client._voice_handoff_input_sequence, old)
        release.set()
        await asyncio.sleep(.04)
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertIsNotNone(self.client._native_phrase_uplink.buffer)

    async def test_tool_execution_waits_for_complete_original_pcm_submission(self):
        entered, release = asyncio.Event(), asyncio.Event()
        actual_send = self.socket.send
        async def held(payload):
            await actual_send(payload)
            if json.loads(payload)['type'] == 'input_audio_buffer.append' and not entered.is_set():
                entered.set()
                self.function('early-call')
                await release.wait()
        self.socket.send = held
        await self.phrase()
        await entered.wait()
        await self.settle(lambda: bool(self.tasks))
        await asyncio.sleep(.01)
        self.assertEqual(self.calls, [])
        release.set()
        await self.finish_writer()
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.calls, ['early-call'])
        await self.complete('after-full-input')

    async def test_partial_pcm_submission_never_executes_early_tool(self):
        self.client._WS_FRAME_LIMIT = 8192
        actual_send = self.socket.send
        count = 0
        async def partial(payload):
            nonlocal count
            if json.loads(payload)['type'] == 'input_audio_buffer.append':
                count += 1
                if count == 2:
                    raise ConnectionError('fixture partial PCM')
                await actual_send(payload)
                self.function('must-not-run')
                await self.settle(lambda: bool(self.tasks))
                return
            await actual_send(payload)
        self.socket.send = partial
        await self.phrase()
        await self.finish_writer()
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.calls, [])
        self.assertEqual(count, 2)

    async def test_output_write_refusal_is_failure_without_retry(self):
        actual_send = self.client.send_event
        async def refuse(event, **kwargs):
            if event['type'] == 'conversation.item.create':
                return False
            return await actual_send(event, **kwargs)
        self.client.send_event = refuse
        await self.phrase()
        await self.finish_writer()
        self.function()
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.calls, ['tool-1'])
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_early_audio_terminal_before_parallel_outputs_finish_is_not_success(self):
        actual_send = self.socket.send
        injected = False
        async def early(payload):
            nonlocal injected
            await actual_send(payload)
            if json.loads(payload)['type'] == 'conversation.item.create' and not injected:
                injected = True
                self.content('premature-audio')
                await self.settle(lambda: self.client._current_response_id == 'premature-audio')
                self.done('premature-audio')
                await asyncio.sleep(.02)
        self.socket.send = early
        await self.phrase()
        await self.finish_writer()
        self.function('first')
        self.function('second')
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertLessEqual(len(self.outputs()), 1)
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_waiting_join_lock_rechecks_new_pcm_before_any_output(self):
        await self.phrase()
        await self.finish_writer()
        owner = self.client._response_arbiter._current
        await owner.native_join_lock.acquire()
        self.function()
        await self.settle(lambda: bool(self.calls))
        await self.frame(True, 83)
        owner.native_join_lock.release()
        await asyncio.sleep(.03)
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_socket_replacement_while_output_waits_cannot_write_or_close_new_socket(self):
        await self.phrase()
        await self.finish_writer()
        self.client._send_semaphore = asyncio.Semaphore(0)
        self.function()
        await self.settle(lambda: bool(self.calls))
        await asyncio.sleep(.01)
        replacement = QueueSocket()
        self.client.ws = replacement
        self.client._on_connection_attached()
        self.client._send_semaphore.release()
        await asyncio.sleep(.03)
        self.assertEqual(self.outputs(), [])
        self.assertFalse(replacement.sent)
        self.assertFalse(replacement.closed)

    async def test_no_native_origin_keeps_ordinary_tool_result_lane(self):
        self.function('ordinary')
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.origins, [None])
        self.assertEqual(self.client._response_arbiter.current_source, 'tool_result')
        self.content('ordinary-audio')
        self.done('ordinary-audio')
        await self.client._response_arbiter.wait_until_idle(.5)

    async def test_direct_sdk_result_without_origin_cannot_join_native_slot(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        owner = arbiter._current
        task = asyncio.create_task(self.client._send_tool_results_openai_realtime([
            ToolResult(call_id='sdk-call', name='study_quiz', output={'question': 'unrelated'})]))
        try:
            await self.settle(lambda: arbiter._queue.qsize() == 1)
            self.assertEqual(self.outputs(), [])
            self.assertIs(arbiter._current, owner)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertFalse(owner.interrupted)

    async def test_absolute_tool_wait_deadline_is_not_reset_by_pending_tools(self):
        arbiter = self.client._response_arbiter
        arbiter._NATIVE_TOOL_RESPONSE_WAIT_SECONDS = .06
        enqueue = arbiter.enqueue
        async def short(**kwargs):
            return await enqueue(**kwargs, response_started_timeout=.02, cancel_timeout=.02)
        arbiter.enqueue = short
        never = asyncio.Event()
        async def slow(call):
            self.calls.append(call.call_id)
            await never.wait()
        self.client.on_tool_call = slow
        await self.phrase()
        await self.finish_writer()
        self.function()
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertFalse(any(json.loads(event['item']['output']).get('question') for event in self.outputs()))

    async def test_normalizer_does_not_accept_unreviewed_gate_edit(self):
        source = SOURCES['_tools.py']
        self.assertEqual(join.normalize_ordering_helpers(source), source)
        with self.assertRaises(RuntimeError):
            join.normalize_ordering_helpers(source.replace('_STUDY_SPEECH_GATE_SECONDS = 20.0',
                                                           '_STUDY_SPEECH_GATE_SECONDS = 999.0'))

    async def test_missing_wire_call_id_never_executes_or_writes_native_tool_output(self):
        await self.phrase()
        await self.finish_writer()
        owner = self.client._response_arbiter._current
        self.socket.feed({'type': 'response.function_call_arguments.done', 'name': 'study_quiz',
                          'response_id': 'missing-wire-id', 'arguments': '{}'})
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.outputs(), [])
        self.assertEqual(owner.native_tools_pending, set())
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_real_wire_call_id_with_glm_prefix_is_preserved(self):
        await self.phrase()
        await self.finish_writer()
        self.function('glm_real_provider_id')
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.calls, ['glm_real_provider_id'])
        self.assertEqual(self.outputs()[0]['item']['call_id'], 'glm_real_provider_id')
        await self.complete('real-glm-prefix-audio')

    async def test_native_registration_is_bounded_and_rejects_invalid_wire_identity(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        for wire in (None, '', 17, 'x' * 1001, 'different'):
            with self.subTest(wire_type=type(wire).__name__), self.assertRaises(ValueError):
                arbiter.capture_native_tool_origin('expected', wire_call_id=wire)
        for index in range(32):
            identity = 'registered-' + str(index)
            arbiter.capture_native_tool_origin(identity, wire_call_id=identity)
        with self.assertRaises(RuntimeError):
            arbiter.capture_native_tool_origin('excess', wire_call_id='excess')
        with self.assertRaises(RuntimeError):
            arbiter.capture_native_tool_origin('registered-0', wire_call_id='registered-0')
        self.assertEqual(len(arbiter._current.native_tools_pending), 32)
        self.assertFalse(self.calls)
        self.assertFalse(self.outputs())

    async def test_cancelled_parallel_member_cannot_produce_partial_successful_batch(self):
        release = asyncio.Event()
        async def held(call):
            self.calls.append(call.call_id)
            await release.wait()
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': 'must-not-pass'})
        self.client.on_tool_call = held
        await self.phrase()
        await self.finish_writer()
        self.function('fast-sibling')
        self.function('cancelled-sibling')
        await self.settle(lambda: len(self.calls) == 2)
        batch = next(iter(self.client._tool_batch_registry().values()))
        batch.entries[1].task.cancel()
        release.set()
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertFalse(any(json.loads(event['item']['output']).get('question') for event in self.outputs()))
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_mixed_origin_batch_is_rejected_without_successful_result(self):
        release = asyncio.Event()
        async def held(call):
            self.calls.append(call.call_id)
            await release.wait()
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': 'must-not-pass'})
        self.client.on_tool_call = held
        await self.phrase()
        await self.finish_writer()
        self.function('first-origin')
        self.function('second-origin')
        await self.settle(lambda: len(self.calls) == 2)
        batch = next(iter(self.client._tool_batch_registry().values()))
        batch.entries[1].owner = TOOLS.replace(batch.entries[1].owner, native_audio_origin=object())
        release.set()
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertFalse(any(json.loads(event['item']['output']).get('question') for event in self.outputs()))
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_actual_output_wait_has_eight_second_bound_without_replay(self):
        await self.phrase()
        await self.finish_writer()
        self.client._send_semaphore = asyncio.Semaphore(0)
        self.function('write-budget')
        await self.settle(lambda: bool(self.calls))
        await self.settle(lambda: self.client._fatal_error_occurred, timeout=9)
        self.client._send_semaphore.release()
        await asyncio.sleep(.02)
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_tool_arriving_after_native_content_start_is_rejected(self):
        await self.phrase()
        await self.finish_writer()
        ticket = self.client._response_arbiter._current.ticket
        self.content('already-speaking')
        await self.settle(lambda: ticket.started.done())
        self.function('late-during-content')
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertFalse(self.calls)
        self.assertFalse(self.outputs())
        self.assertEqual(self.client._response_arbiter._queue.qsize(), 0)

    async def test_tool_arriving_after_native_completion_cannot_fall_back_to_ordinary_lane(self):
        await self.phrase()
        await self.finish_writer()
        await self.complete('finished-before-tool')
        self.function('late-after-completion')
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertFalse(self.calls)
        self.assertFalse(self.outputs())
        self.assertEqual(self.client._response_arbiter._queue.qsize(), 0)

    async def test_new_complete_phrase_after_pending_tool_cancel_fails_closed_before_write_budget(self):
        never = asyncio.Event()
        async def held(call):
            self.calls.append(call.call_id)
            await never.wait()
        self.client.on_tool_call = held
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        old = arbiter._current
        original_pcm = self.written()
        old_sequence = self.client._voice_handoff_input_sequence
        self.function('held-across-new-phrase')
        await self.settle(lambda: bool(self.calls))
        started = time.monotonic()
        await self.phrase()
        self.assertGreater(self.client._voice_handoff_input_sequence, old_sequence)
        await self.settle(lambda: self.client._fatal_error_occurred, timeout=4)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 4)
        self.assertTrue(old.interrupted)
        self.assertTrue(old.escalated)
        await self.settle(lambda: self.socket.closed)
        await self.finish_writer()
        self.assertTrue(self.socket.closed)
        self.assertEqual(self.written(), original_pcm)
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertNotEqual(self.client._native_phrase_last_delivery.get('result'), 'written_waiting_provider_boundary')

    async def test_replacement_during_cancel_grace_is_not_closed_by_old_tool_slot(self):
        never = asyncio.Event()
        async def held(call):
            self.calls.append(call.call_id)
            await never.wait()
        self.client.on_tool_call = held
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        old = arbiter._current
        self.function('held-at-cancel')
        await self.settle(lambda: bool(self.calls))
        await self.frame(True, 87)
        await self.settle(lambda: sum(event['type'] == 'response.cancel' for event in self.socket.sent) >= 2)
        replacement = QueueSocket()
        self.client.ws = replacement
        self.client._on_connection_attached()
        await self.settle(lambda: old.ticket.done.done(), timeout=4)
        self.assertIsNotNone(old.ticket.done.exception())
        self.assertFalse(old.escalated)
        self.assertFalse(replacement.closed)
        self.assertFalse(replacement.sent)
        self.assertEqual(self.outputs(), [])


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.CRITICAL)
    # This class reuses fixture helpers, but selects only the new join scenarios.
    names = [name for name in NativeToolJoin.__dict__ if name.startswith('test_')]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(NativeToolJoin(name) for name in names))
    sys.exit(not result.wasSuccessful())
