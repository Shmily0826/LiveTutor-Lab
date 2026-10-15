"""Actual Core/Omni methods with a local queue socket; no provider/audio device."""
import asyncio
import base64
import hashlib
import json
import os
import struct
import time
import unittest
from unittest.mock import patch

import test_neko_native_barge_in as native
import neko_phrase_input_transport as phrase_transport
from test_neko_native_barge_in import ActivationGeneration, OutputCommit, QueueSocket


class PhraseTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {'NEKO_EXPERIMENTAL_PHRASE_INPUT': '1'})
        self.env.start()
        self.original = native.NativeHandoffTest()
        self.manager, self.client, self.socket = await self.original.fixture()
        self.client._ai_recent_activity_time = 0
        self.manager.note_native_speech_playback_state({'active': False,
            'sdk_speech_correlation_id': self.client._native_output_connection_token}, self.manager.websocket)
        self.at = time.time()
        self.offset = 0

    async def asyncTearDown(self):
        driver = getattr(self.client, '_native_phrase_uplink', None)
        if driver:
            driver.retire()
            if driver.failure_task is not None:
                await asyncio.gather(driver.failure_task, return_exceptions=True)
        await self.original.dispose(self.manager)
        self.env.stop()

    async def frame(self, speech, value=0):
        pcm = struct.pack('<h', value) * 512
        stamp = self.at + self.offset * .032
        self.offset += 1
        result = await self.manager._route_microphone_audio_unfiltered(pcm,
            sample_rate_hz=16000, speech_probability=.9 if speech else .1,
            rnnoise_available=True, captured_at=stamp)
        return result, pcm

    async def phrase(self):
        original = []
        for speech, count, value in ((True, 8, 11), (False, 28, 0), (True, 8, 23), (False, 38, 0)):
            for _ in range(count):
                result, pcm = await self.frame(speech, value)
                self.assertEqual(result, OutputCommit.LOCAL_ACCEPTED)
                original.append(pcm)
        return b''.join(original)

    def written(self, socket=None):
        return b''.join(base64.b64decode(item['audio']) for item in (socket or self.socket).sent
                        if item['type'] == 'input_audio_buffer.append')

    async def finish_writer(self):
        task = self.client._native_phrase_uplink.writer
        if task:
            await task
        await asyncio.sleep(0)

    async def test_pause_keeps_prefix_unsent_and_actual_core_counts_only_final_wire(self):
        for _ in range(8):
            self.assertEqual((await self.frame(True, 11))[0], OutputCommit.LOCAL_ACCEPTED)
        for _ in range(28):
            await self.frame(False)
        self.assertEqual(self.written(), b'')
        self.assertEqual(self.manager._omni_mic_audio_bytes, 0)
        for _ in range(8):
            await self.frame(True, 23)
        for _ in range(38):
            await self.frame(False)
        await self.finish_writer()
        actual = self.written()
        self.assertEqual(actual, struct.pack('<h', 11) * (8 * 512) + bytes(3200)
                         + struct.pack('<h', 23) * (8 * 512) + bytes(38 * 1024))
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(actual))
        self.assertLess(len(actual), 82 * 1024)
        self.assertEqual(self.client._native_phrase_last_delivery['written_samples'], len(actual) // 2)

    async def test_original_silence_clear_and_handoff_cannot_consume_pending_phrase(self):
        await self.frame(True, 11)
        await self.client.clear_audio_buffer()
        self.assertFalse(any(item['type'] == 'input_audio_buffer.clear' for item in self.socket.sent))
        self.assertFalse(self.client.can_handoff_voice_input())
        # A mismatched older owned response cannot release this input marker.
        self.client._note_voice_handoff_input_boundary(expected_sequence=0)
        self.assertTrue(self.client._native_phrase_protects_input())

    async def test_write_is_bounded_chunked_and_owned_response_boundary_releases_clear(self):
        self.client._WS_FRAME_LIMIT = 4096
        await self.phrase()
        await self.finish_writer()
        chunks = [item for item in self.socket.sent if item['type'] == 'input_audio_buffer.append']
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(json.dumps(item)) < 4096 for item in chunks))
        report = self.client._native_phrase_last_delivery
        self.assertGreater(report['local_append_count'], 32)
        self.assertEqual(len(report['local_append_writes']), 32)
        self.assertTrue(report['local_append_writes_truncated'])
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(self.written()))
        self.assertTrue(self.client._native_phrase_protects_input())
        sequence = self.client._voice_handoff_input_sequence
        self.client._note_voice_handoff_input_boundary(expected_sequence=sequence - 1)
        self.assertTrue(self.client._native_phrase_protects_input())
        self.client._note_voice_handoff_input_boundary(expected_sequence=sequence)
        self.assertFalse(self.client._native_phrase_protects_input())
        await self.client.clear_audio_buffer()
        self.assertTrue(any(item['type'] == 'input_audio_buffer.clear' for item in self.socket.sent))

    async def test_burst_wire_ids_are_unique_even_when_wall_clock_is_frozen(self):
        self.client._WS_FRAME_LIMIT = 8192
        with patch.object(phrase_transport.time, 'time', return_value=self.at):
            await self.phrase()
            await self.finish_writer()
            self.socket.feed({'type': 'response.audio_transcript.delta', 'response_id': 'burst-one', 'delta': 'ok'})
            self.socket.feed({'type': 'response.done', 'response': {'id': 'burst-one', 'status': 'completed'}})
            await asyncio.sleep(.02)
            await self.client._response_arbiter.wait_until_idle(.5)
            self.client._note_voice_handoff_input_boundary(
                expected_sequence=self.client._voice_handoff_input_sequence)
            await self.phrase()
            await self.finish_writer()
        chunks = [item for item in self.socket.sent if item['type'] == 'input_audio_buffer.append']
        self.assertGreater(len(chunks), 2)
        ids = [item['event_id'] for item in chunks]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith('event_phrase_') for value in ids))
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(self.written()))

    async def test_delivery_logs_seal_queue_and_successful_write_without_audio_or_owner(self):
        with self.assertLogs(phrase_transport.logger, level='INFO') as logs:
            await self.phrase()
            await self.finish_writer()
        report = self.client._native_phrase_last_delivery
        self.assertEqual(report['input_timebase'], 'arrival_derived_sample_estimate')
        self.assertGreaterEqual(report['sealed_estimated_wall'] - report['speech_end_estimated_wall'], 1.2 - 1e-6)
        self.assertGreaterEqual(report['queue_wait_ms'], 0)
        self.assertGreaterEqual(report['first_write_completed_ms'], report['queue_wait_ms'])
        self.assertGreaterEqual(report['write_elapsed_ms'], 0)
        self.assertLessEqual(report['sealed_wall'], report['started_wall'])
        self.assertLessEqual(report['first_write_wall'], report['completed_wall'])
        self.assertEqual(report['output_pcm_sha256'], hashlib.sha256(self.written()).hexdigest())
        self.assertLessEqual(report['captured_start_estimated_wall'], report['speech_end_estimated_wall'])
        self.assertEqual(report['local_append_count'], len(report['local_append_writes']))
        self.assertEqual(sum(w['samples'] for w in report['local_append_writes']), report['written_samples'])
        self.assertFalse(report['local_append_writes_truncated'])
        self.assertEqual(sorted(w['written_wall'] for w in report['local_append_writes']),
                         [w['written_wall'] for w in report['local_append_writes']])
        logged = json.loads(logs.records[0].getMessage().split('native phrase delivery ', 1)[1])
        self.assertEqual(logged, json.loads(json.dumps(report)))
        from neko_spoken_turn_analysis import parse_phrase_deliveries
        parsed = parse_phrase_deliveries(logs.records[0].getMessage())
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['output_pcm_sha256'], report['output_pcm_sha256'])
        self.assertEqual(parsed[0]['local_append_writes'], report['local_append_writes'])
        for private in ('audio', 'pcm16', 'owner_token', 'session_id', 'event_id', 'transcript'):
            self.assertNotIn(private, logged)

    async def test_logging_failure_does_not_keep_writer_or_retry_successful_pcm(self):
        with patch.object(phrase_transport.logger, 'info', side_effect=RuntimeError('broken log sink')):
            await self.phrase()
            await self.finish_writer()
        driver = self.client._native_phrase_uplink
        before = self.written()
        self.assertTrue(before)
        self.assertIsNone(driver.writer)
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(before))
        self.assertTrue(self.client._native_phrase_last_delivery['diagnostic_log_failed'])
        self.assertFalse(self.client._fatal_error_occurred)
        self.client._note_voice_handoff_input_boundary(expected_sequence=self.client._voice_handoff_input_sequence)
        self.assertFalse(driver.protect_clear())
        await asyncio.sleep(.11)
        self.assertTrue(driver.watchdog.done())
        self.assertEqual(self.written(), before)

    async def test_route_exit_with_only_nonzero_preroll_fails_and_never_reuses_it(self):
        self.assertEqual((await self.frame(False, 51))[0], OutputCommit.LOCAL_ACCEPTED)
        driver = self.client._native_phrase_uplink
        self.assertTrue(driver.preroll)
        self.client._has_server_vad = True
        self.assertEqual((await self.frame(True, 52))[0], OutputCommit.NOT_SENT)
        await driver.failure_task
        self.assertEqual(driver.preroll, [])
        self.assertEqual(self.written(), b'')
        self.assertEqual(self.manager._omni_mic_audio_bytes, 0)
        self.assertTrue(self.socket.closed)
        self.client._has_server_vad = False
        self.assertEqual((await self.frame(True, 53))[0], OutputCommit.NOT_SENT)
        self.assertEqual(self.written(), b'')

    async def test_route_exit_after_delivery_retires_waiting_state_without_replaying(self):
        await self.phrase()
        await self.finish_writer()
        driver = self.client._native_phrase_uplink
        before = self.written()
        self.assertIsNotNone(driver.waiting)
        self.client._has_server_vad = True
        result, pcm = await self.frame(True, 54)
        self.assertEqual(result, OutputCommit.TRANSPORT_WRITTEN)
        self.assertIsNone(driver.waiting)
        self.assertEqual(driver.preroll, [])
        self.assertEqual(self.written(), before + pcm)
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_semaphore_wait_rechecks_real_permission_and_never_promotes_old_pcm(self):
        self.client._send_semaphore = asyncio.Semaphore(0)
        await self.phrase()
        task = self.client._native_phrase_uplink.writer
        await asyncio.sleep(0)
        self.manager.scope = ActivationGeneration('offline', 1, 1, 1, 2, 'core')
        self.client._send_semaphore.release()
        await task
        self.assertEqual(self.written(), b'')
        self.assertEqual(self.manager._omni_mic_audio_bytes, 0)
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_physical_replacement_retires_waiting_writer_without_new_socket_write(self):
        self.client._send_semaphore = asyncio.Semaphore(0)
        await self.phrase()
        task = self.client._native_phrase_uplink.writer
        await asyncio.sleep(0)
        replacement = QueueSocket()
        self.client.ws = replacement
        self.client._on_connection_attached()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(self.written(), b'')
        self.assertEqual(self.written(replacement), b'')
        self.assertIsNone(self.client._native_phrase_uplink.buffer)

    async def test_native_authority_is_current_core_not_game_route_or_unknown_record(self):
        self.assertIsNotNone(self.client.get_native_phrase_input_authority())
        self.client.get_input_route_identity = lambda: ('unrelated-game', 'session', 'route')
        authority = self.client.get_native_phrase_input_authority()
        self.assertEqual(authority, self.client.get_native_phrase_input_authority())
        for name, value in (('is_active', False), ('_takeover_active', True),
                            ('_asr_route_mode', 'game'), ('_voice_lease_owner', 'game'),
                            ('session_closed_by_server', True)):
            previous = getattr(self.manager, name)
            setattr(self.manager, name, value)
            self.assertIsNone(self.client.get_native_phrase_input_authority(), name)
            setattr(self.manager, name, previous)
        self.manager.record.retired = True
        self.assertIsNone(self.client.get_native_phrase_input_authority())
        self.manager.record.retired = False
        self.manager.session = object()
        self.assertIsNone(self.client.get_native_phrase_input_authority())

    async def test_overflow_is_explicit_unsent_failure_without_truncation_or_retry(self):
        await self.frame(True, 11)
        self.client._native_phrase_uplink.buffer.max_bytes = 2048
        await self.frame(True, 12)
        self.assertEqual((await self.frame(True, 13))[0], OutputCommit.NOT_SENT)
        await asyncio.sleep(0)
        self.assertEqual(self.written(), b'')
        self.assertTrue(self.client._fatal_error_occurred)
        self.assertEqual(self.client._native_phrase_last_failure, 'phrase_input_invalid_or_over_limit')

    async def test_pending_then_replay_and_suffix_use_original_single_write_path(self):
        await self.frame(True, 11)
        self.assertTrue(self.client._prepare_native_barge_in_replay())
        self.client._native_barge_in_pending = True
        self.assertEqual((await self.frame(True, 12))[0], OutputCommit.LOCAL_ACCEPTED)
        driver = self.client._native_phrase_uplink
        self.assertIsNone(driver.buffer)
        self.assertTrue(driver.bypass)
        self.client._native_barge_in_pending = False
        replay = struct.pack('<h', 11) * 512
        self.assertIs(await self.client.stream_audio(replay, speech_active=True,
            captured_at=self.at + .064, require_output_commit=True, _native_barge_in_replay=True), True)
        suffix_result, suffix = await self.frame(True, 14)
        self.assertEqual(suffix_result, OutputCommit.TRANSPORT_WRITTEN)
        self.assertEqual(self.written(), replay + suffix)
        self.assertIsNone(driver.buffer)

    async def test_default_off_retains_existing_streaming_receipt(self):
        self.client._native_phrase_input_enabled = False
        result, pcm = await self.frame(True, 17)
        self.assertEqual(result, OutputCommit.TRANSPORT_WRITTEN)
        self.assertEqual(self.written(), pcm)
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(pcm))

    async def test_frontend_socket_replacement_also_retires_blocked_owned_pcm(self):
        self.client._send_semaphore = asyncio.Semaphore(0)
        await self.phrase()
        task = self.client._native_phrase_uplink.writer
        await asyncio.sleep(0)
        self.manager.websocket = native.FrontendSocket()
        self.client._send_semaphore.release()
        await task
        self.assertEqual(self.written(), b'')
        self.assertEqual(self.manager._omni_mic_audio_bytes, 0)

    async def test_legacy_batch_flag_bypasses_entire_phrase_and_keeps_original_write(self):
        self.manager.is_flushing_hot_swap_cache = True
        batch = struct.pack('<h', 19) * (5 * 512)
        result = await self.manager._route_microphone_audio_unfiltered(batch, sample_rate_hz=16000,
            speech_probability=.9, rnnoise_available=True, captured_at=self.at + .16)
        self.assertEqual(result, OutputCommit.TRANSPORT_WRITTEN)
        self.assertEqual(self.written(), batch)
        self.assertIsNone(self.client._native_phrase_uplink.buffer)
        self.manager.is_flushing_hot_swap_cache = False
        result, suffix = await self.frame(True, 20)
        self.assertEqual(result, OutputCommit.TRANSPORT_WRITTEN)
        self.assertEqual(self.written(), batch + suffix)

    async def test_new_real_input_retires_prior_timeout_without_fake_provider_boundary(self):
        await self.phrase()
        await self.finish_writer()
        driver = self.client._native_phrase_uplink
        older = self.client._voice_handoff_input_sequence
        driver.waiting = (time.monotonic() - 31, older)
        self.assertEqual((await self.frame(True, 31))[0], OutputCommit.LOCAL_ACCEPTED)
        self.assertIsNone(driver.waiting)
        self.assertIsNotNone(driver.buffer)
        self.assertTrue(self.client._voice_handoff_input_open)
        self.client._note_voice_handoff_input_boundary(expected_sequence=older)
        await asyncio.sleep(.11)
        self.assertFalse(self.client._fatal_error_occurred)
        self.assertIsNotNone(driver.buffer)

    async def test_normal_close_retires_preroll_and_writer_before_first_await(self):
        await self.frame(False)
        driver = self.client._native_phrase_uplink
        self.assertTrue(driver.preroll)
        entered, release = asyncio.Event(), asyncio.Event()
        async def slow_frame_copy_cleanup():
            entered.set()
            await release.wait()
        self.client._cancel_frame_copies = slow_frame_copy_cleanup
        close = asyncio.create_task(self.client.close())
        await entered.wait()
        self.assertEqual(driver.preroll, [])
        self.assertEqual(self.written(), b'')
        release.set()
        await close

    async def test_route_capability_change_with_unsent_input_fails_explicitly_and_closes(self):
        await self.frame(True, 11)
        self.client._has_server_vad = True
        self.assertEqual((await self.frame(True, 12))[0], OutputCommit.NOT_SENT)
        driver = self.client._native_phrase_uplink
        await driver.failure_task
        self.assertEqual(self.written(), b'')
        self.assertTrue(self.socket.closed)
        self.assertEqual(self.client._native_phrase_last_failure, 'phrase_route_changed_with_unsent_input')

    async def test_partial_transport_failure_counts_only_successful_wire_and_never_retries(self):
        self.client._WS_FRAME_LIMIT = 8192
        actual_send = self.socket.send
        sends = 0
        async def fail_second(payload):
            nonlocal sends
            sends += 1
            if sends == 2:
                raise RuntimeError('offline partial send failure')
            await actual_send(payload)
        self.socket.send = fail_second
        await self.phrase()
        await self.finish_writer()
        driver = self.client._native_phrase_uplink
        await driver.failure_task
        self.assertEqual(sends, 2)
        self.assertEqual(self.manager._omni_mic_audio_bytes, len(self.written()))
        self.assertEqual(self.client._native_phrase_last_delivery['result'], 'failed_without_retry')
        self.assertTrue(self.socket.closed)
        self.assertEqual((await self.frame(True, 32))[0], OutputCommit.NOT_SENT)
        self.assertEqual(sends, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
