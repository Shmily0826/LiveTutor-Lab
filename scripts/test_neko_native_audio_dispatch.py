"""Canonical draft + actual queue-socket client, without deployment or devices."""
import ast
import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import test_neko_phrase_input_transport as fixture
import neko_voice_host_patch as canonical
from neko_native_audio_dispatch_patch import upgrade_targets
from main_logic.omni_realtime_client import _client, _responses, _transport
from main_logic.omni_realtime_client._protocol_capabilities import STRICT_REALTIME_PROTOCOL_CAPABILITIES
from main_logic.tool_calling import ToolResult

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'benchmarks/raw/neko-product-host'


def staged_sources():
    result = {}
    targets, replay = upgrade_targets(canonical.TARGETS, canonical._OWNER_TRACE_REPLAY)
    with tempfile.TemporaryDirectory() as directory, patch.object(canonical, 'TARGETS', targets), \
            patch.object(canonical, '_OWNER_TRACE_REPLAY', replay):
        for name in ('_response_arbiter.py', '_transport.py'):
            relative = Path('main_logic/omni_realtime_client') / name
            target = Path(directory) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((HOST / relative).read_bytes())
            canonical.apply_to(target)
            result[name] = target.read_text(encoding='utf-8')
            ast.parse(result[name])
            assert canonical.state(target) == 'patched'
            assert canonical.apply_to(target) == 'already patched'
    return result


SOURCES = staged_sources()
NAME = 'main_logic.omni_realtime_client._draft_native_audio_dispatch'
DRAFT = types.ModuleType(NAME)
sys.modules[NAME] = DRAFT
exec(compile(SOURCES['_response_arbiter.py'], NAME, 'exec'), DRAFT.__dict__)
tree = ast.parse(SOURCES['_transport.py'])
namespace = dict(_transport.__dict__)
METHODS = ('_begin_response_lifecycle', '_notify_turn_finished')
nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
         and node.name in METHODS]
exec(compile(ast.Module(body=nodes, type_ignores=[]), '_draft_transport', 'exec'), namespace)
spec = importlib.util.spec_from_file_location('_draft_phrase_input_transport', ROOT / 'scripts/drafts/neko_phrase_input_transport_phase40.py')
PRODUCER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PRODUCER)


class AutomaticAudio(unittest.IsolatedAsyncioTestCase):
    frame = fixture.PhraseTransport.frame
    phrase = fixture.PhraseTransport.phrase
    written = fixture.PhraseTransport.written
    finish_writer = fixture.PhraseTransport.finish_writer

    async def asyncSetUp(self):
        self.patches = [patch.object(_responses, 'RealtimeResponseArbiter', DRAFT.RealtimeResponseArbiter),
                        patch.object(_client, 'RealtimeResponseArbiter', DRAFT.RealtimeResponseArbiter),
                        patch.object(fixture, 'phrase_transport', PRODUCER),
                        patch.dict(sys.modules, {'neko_phrase_input_transport': PRODUCER})]
        for item in self.patches:
            item.start()
        await fixture.PhraseTransport.asyncSetUp(self)
        for name in METHODS:
            setattr(self.client, name, types.MethodType(namespace[name], self.client))

    async def asyncTearDown(self):
        driver = getattr(self.client, '_native_phrase_uplink', None)
        tasks = [] if driver is None else [driver.writer, driver.response_waiter, driver.watchdog]
        try:
            await fixture.PhraseTransport.asyncTearDown(self)
            await self.client._response_arbiter.shutdown()
            await asyncio.gather(*(task for task in tasks if task is not None), return_exceptions=True)
        finally:
            for item in reversed(self.patches):
                item.stop()

    async def settle(self, predicate, timeout=.5):
        async with asyncio.timeout(timeout):
            while not predicate():
                await asyncio.sleep(.001)

    def content(self, identity='auto-1'):
        self.socket.feed({'type': 'response.audio_transcript.delta', 'response_id': identity, 'delta': '方向'})

    def done(self, identity='auto-1', status='completed'):
        self.socket.feed({'type': 'response.done', 'response': {'id': identity, 'status': status}})

    async def test_complete_real_terminal_releases_waiting_and_does_not_create_or_ack(self):
        await self.phrase()
        await self.finish_writer()
        driver = self.client._native_phrase_uplink
        ticket = self.client._response_arbiter._current.ticket
        seq = driver.waiting[1]
        self.content()
        await self.settle(lambda: ticket.started.done())
        self.assertEqual(self.client._voice_handoff_response_input_sequence, seq)
        self.done()
        result = await asyncio.wait_for(asyncio.shield(ticket.done), .5)
        await self.settle(lambda: driver.waiting is None)
        self.assertFalse(self.client._voice_handoff_input_open)
        self.assertFalse(result.item_acknowledged)
        self.assertTrue(result.context_persistence_uncertain)
        self.assertEqual(self.client._native_phrase_last_delivery['written_samples'], len(self.written()) // 2)
        self.assertEqual({event['type'] for event in self.socket.sent}, {'input_audio_buffer.append'})
        await asyncio.sleep(.11)
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_content_and_terminal_inside_single_write_are_not_orphaned(self):
        original = self.socket.send
        async def early(payload):
            await original(payload)
            self.content('early')
            await self.settle(lambda: self.client._response_arbiter._current.ticket.started.done())
            self.done('early')
            await asyncio.sleep(.01)
        self.socket.send = early
        await self.phrase()
        await self.finish_writer()
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)
        self.assertFalse(self.client._fatal_error_occurred)
        self.assertFalse(self.client._voice_handoff_input_open)
        self.assertTrue(self.written())

    async def test_early_terminal_in_chunked_batch_is_partial_failure_without_replay(self):
        self.client._WS_FRAME_LIMIT = 8192
        original = self.socket.send
        async def early(payload):
            await original(payload)
            self.content('early-partial')
            await self.settle(lambda: self.client._response_arbiter._current.ticket.started.done())
            self.done('early-partial')
            await asyncio.sleep(.01)
        self.socket.send = early
        await self.phrase()
        await self.finish_writer()
        driver = self.client._native_phrase_uplink
        self.assertTrue(self.client._fatal_error_occurred)
        self.assertEqual(self.client._native_phrase_last_delivery['result'], 'failed_without_retry')
        self.assertIsNone(driver.waiting)
        self.assertLess(len(self.written()) // 2, self.client._native_phrase_last_delivery['output_samples'])
        self.assertEqual(len(self.socket.sent), 1)

    async def test_original_sequence_survives_new_input_before_content_and_old_terminal(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        ticket = arbiter._current.ticket
        original = self.client._voice_handoff_input_sequence
        # Real positive PCM opens a new input while the previous response is pending.
        await self.frame(True, 71)
        self.assertGreater(self.client._voice_handoff_input_sequence, original)
        self.content('old')
        self.done('old')
        await asyncio.sleep(.03)
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertIsNotNone(self.client._native_phrase_uplink.buffer)
        self.assertNotEqual(getattr(self.client, '_voice_handoff_response_input_sequence', None),
                            self.client._voice_handoff_input_sequence)
        self.assertTrue(ticket.done.done() or arbiter._current.interrupted)

    async def test_lifecycle_uses_original_sequence_during_onset_marker_before_collector(self):
        await self.phrase()
        await self.finish_writer()
        seq = self.client._voice_handoff_input_sequence
        successor = self.client._note_voice_handoff_input_open()
        self.content('late-original')
        await self.settle(lambda: self.client._current_response_id == 'late-original')
        self.assertEqual(self.client._voice_handoff_response_input_sequence, seq)
        self.done('late-original')
        await asyncio.sleep(.02)
        self.assertEqual(self.client._voice_handoff_input_sequence, successor)
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_failed_terminal_is_not_a_successful_input_boundary(self):
        await self.phrase()
        await self.finish_writer()
        self.content('failure')
        await self.settle(lambda: self.client._current_response_id == 'failure')
        self.done('failure', 'failed')
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.client._native_phrase_last_failure, 'phrase_response_failed')
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_statusless_terminal_is_not_a_successful_input_boundary(self):
        await self.phrase()
        await self.finish_writer()
        self.content('statusless')
        await self.settle(lambda: self.client._current_response_id == 'statusless')
        self.socket.feed({'type': 'response.done', 'response': {'id': 'statusless'}})
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.client._native_phrase_last_failure, 'phrase_response_failed')
        self.assertTrue(self.client._voice_handoff_input_open)

    async def test_terminal_only_idless_and_wrong_id_cannot_complete_ticket(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        ticket = arbiter._current.ticket
        self.done('terminal-only')
        await asyncio.sleep(.01)
        self.assertFalse(ticket.started.done())
        self.content('real-content')
        await self.settle(lambda: ticket.started.done())
        self.socket.feed({'type': 'response.done', 'response': {'status': 'completed'}})
        self.done('wrong-id')
        await asyncio.sleep(.01)
        self.assertFalse(ticket.done.done())
        self.assertIsNotNone(self.client._native_phrase_uplink.waiting)
        self.done('real-content')
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)

    async def test_real_partial_socket_failure_does_not_replay_or_close_successor(self):
        await fixture.PhraseTransport.test_partial_transport_failure_counts_only_successful_wire_and_never_retries(self)

    async def test_semaphore_permission_retirement_does_not_send_pcm(self):
        await fixture.PhraseTransport.test_semaphore_wait_rechecks_real_permission_and_never_promotes_old_pcm(self)

    async def test_physical_socket_replacement_does_not_send_on_new_socket(self):
        await fixture.PhraseTransport.test_physical_replacement_retires_waiting_writer_without_new_socket_write(self)

    async def test_frontend_replacement_does_not_promote_old_pcm(self):
        await fixture.PhraseTransport.test_frontend_socket_replacement_also_retires_blocked_owned_pcm(self)

    async def test_original_bypass_and_default_off_paths_are_preserved(self):
        await fixture.PhraseTransport.test_pending_then_replay_and_suffix_use_original_single_write_path(self)
        self.client._native_phrase_uplink.retire()
        self.socket.sent.clear()
        self.manager._omni_mic_audio_bytes = 0
        await fixture.PhraseTransport.test_default_off_retains_existing_streaming_receipt(self)

    async def test_host_turn_change_keeps_ui_hooks_but_owned_waiter_can_finish(self):
        await self.phrase()
        await self.finish_writer()
        self.content('host-guard')
        await self.settle(lambda: self.client._current_response_id == 'host-guard')
        self.manager.current_speech_id = 'new-host-turn'
        calls = []
        async def record(*args, **kwargs):
            calls.append(True)
        self.client.on_response_done = record
        self.done('host-guard')
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)
        self.assertEqual(calls, [])
        self.assertFalse(self.client._voice_handoff_input_open)

    async def test_second_unbound_response_cannot_become_a_new_input_boundary(self):
        await self.test_complete_real_terminal_releases_waiting_and_does_not_create_or_ack()
        await self.frame(True, 73)
        self.content('extra-unknown')
        self.done('extra-unknown')
        await asyncio.sleep(.03)
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertIsNotNone(self.client._native_phrase_uplink.buffer)

    async def test_invalid_automatic_requests_are_rejected_without_wire(self):
        arbiter = self.client._response_arbiter
        defaults = dict(source='native_phrase', automatic_audio=True, native_input_sequence=1,
                        events_before_response=({'type': 'input_audio_buffer.append', 'audio': 'AQI='},))
        for change in ({'source': 'text'}, {'native_input_sequence': True}, {'native_input_sequence': 0},
                       {'ack_expected': True}, {'response_event': {'type': 'response.create'}},
                       {'events_before_response': ({'type': 'conversation.item.create'},)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                await arbiter.enqueue(**(defaults | change))
        self.assertEqual(self.socket.sent, [])

    async def test_identity_filters_are_preserved_for_native_audio(self):
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        arbiter._remember_seen_response_id('seen')
        arbiter._server_response_ids['server'] = None
        for event in ({'type': 'response.audio_transcript.delta', 'delta': 'x'},
                      {'type': 'response.audio_transcript.delta', 'response_id': 'seen', 'delta': 'x'},
                      {'type': 'response.audio_transcript.delta', 'response_id': 'server', 'delta': 'x'},
                      {'type': 'response.output_item.added', 'response_id': 'new'},
                      {'type': 'response.function_call_arguments.delta', 'response_id': 'function', 'delta': '{}'}):
            self.assertFalse(arbiter.notify_response_content(event), event)
        self.assertFalse(arbiter._current.ticket.started.done())
        self.content('valid')
        await self.settle(lambda: arbiter._current.ticket.started.done())
        self.done('valid')
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)

    async def test_unknown_profile_cannot_enable_automatic_audio(self):
        arbiter = self.client._response_arbiter
        arbiter._protocol_capabilities = STRICT_REALTIME_PROTOCOL_CAPABILITIES
        with self.assertRaises(ValueError):
            await arbiter.enqueue(source='native_phrase', automatic_audio=True, native_input_sequence=1,
                events_before_response=({'type': 'input_audio_buffer.append', 'audio': 'AQI='},))
        self.assertEqual(self.socket.sent, [])

    async def test_local_fail_open_timeout_cannot_complete_input_successfully(self):
        arbiter = self.client._response_arbiter
        arbiter._fail_open = True
        recovered = []
        async def release(*args):
            recovered.append(args)
        arbiter._on_stuck_release = release
        enqueue = arbiter.enqueue
        async def brief(**kwargs):
            return await enqueue(**kwargs, response_started_timeout=.1, response_done_timeout=.02, cancel_timeout=.02)
        arbiter.enqueue = brief
        await self.phrase()
        await self.finish_writer()
        ticket = arbiter._current.ticket
        self.content('fail-open')
        await self.settle(lambda: ticket.done.done())
        with self.assertRaises(TimeoutError):
            await asyncio.shield(ticket.done)
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertTrue(self.client._voice_handoff_input_open)
        self.assertEqual(self.client._native_phrase_last_failure, 'phrase_response_failed')
        self.assertEqual(len(recovered), 1)

    async def test_retiring_phrase_queued_behind_text_cannot_cancel_unrelated_owner(self):
        arbiter = self.client._response_arbiter
        text = await arbiter.enqueue(source='text', events_before_response=({'type': 'conversation.item.create',
            'item': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'fixture'}]}},))
        await asyncio.wait_for(asyncio.shield(text.sent), .5)
        await self.phrase()
        driver = self.client._native_phrase_uplink
        writer = driver.writer
        await asyncio.sleep(.01)
        self.assertEqual(self.written(), b'')
        self.assertFalse(text.done.done())
        driver.retire()
        await asyncio.gather(writer, return_exceptions=True)
        self.assertFalse(any(event['type'] == 'response.cancel' for event in self.socket.sent))
        self.assertFalse(arbiter._current.interrupted)
        self.content('text-owner')
        self.done('text-owner')
        await asyncio.wait_for(asyncio.shield(text.done), .5)
        await arbiter.wait_until_idle(.5)
        self.assertEqual(self.written(), b'')

    async def test_known_blocker_tool_result_waits_for_native_owner_that_needs_its_result(self):
        """Quarantined draft: assert the independently found blocker, not a fix."""
        await self.phrase()
        await self.finish_writer()
        arbiter = self.client._response_arbiter
        native = arbiter._current.ticket
        self.assertFalse(arbiter.notify_response_content({'type': 'response.function_call_arguments.done',
            'name': 'study_quiz', 'call_id': 'fixture-call', 'response_id': 'function-id', 'arguments': '{}'}))
        self.done('parent-terminal')
        task = asyncio.create_task(self.client._send_tool_results_openai_realtime([
            ToolResult(call_id='fixture-call', name='study_quiz', output={'question': 'fixture-only'})]))
        try:
            await self.settle(lambda: arbiter._queue.qsize() == 1)
            self.assertFalse(task.done())
            self.assertFalse(native.started.done())
            self.assertFalse(native.done.done())
            self.assertEqual(arbiter.current_source, 'native_phrase')
            self.assertEqual({event['type'] for event in self.socket.sent}, {'input_audio_buffer.append'})
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


class ExistingPhraseRegression(fixture.PhraseTransport):
    asyncSetUp = AutomaticAudio.asyncSetUp
    asyncTearDown = AutomaticAudio.asyncTearDown


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.CRITICAL)
    unittest.main(verbosity=2)
