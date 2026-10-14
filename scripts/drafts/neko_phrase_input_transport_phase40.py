"""Opt-in unsent native PCM delivery, owned by the actual Core/client callbacks.

Only the collector timeline uses arrival-derived sample estimates. Existing
onset clocks and provider identities are never changed here.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid

from neko_phrase_input_buffer import PhraseInputBuffer, PhraseOwnership, PhraseState

logger = logging.getLogger(__name__)


class NativePhraseUplink:
    def __init__(self, client, *, quiet_seconds=1.2):
        self.client = client
        self.quiet_seconds = quiet_seconds
        self.buffer = None
        self.snapshot = None
        self.preroll = []
        self.writer = None
        self.response_waiter = None
        self.watchdog = None
        self.waiting = None
        self.failure_task = None
        self.epoch = 0
        self.activity = time.monotonic()
        self.bypass = False
        self.bypass_loud_at = None

    def read_snapshot(self):
        callback = getattr(self.client, 'get_native_phrase_input_authority', None)
        try:
            raw = callback() if callable(callback) else None
        except Exception:
            return None
        if not isinstance(raw, tuple) or len(raw) != 3 or self.client.ws is None:
            return None
        try:
            owner = PhraseOwnership(*raw)
        except (TypeError, ValueError):
            return None
        return owner, self.client.ws

    def current(self, snapshot):
        return snapshot is not None and self.read_snapshot() == snapshot

    def retire(self):
        self.epoch += 1
        if self.buffer:
            self.buffer.close()
        self.buffer = self.snapshot = self.waiting = None
        self.preroll.clear()
        for task in (self.writer, self.watchdog, self.response_waiter):
            if task is not None and not task.done() and task is not asyncio.current_task():
                task.cancel()
        self.writer = self.watchdog = None
        self.response_waiter = None

    def protect_clear(self):
        pending = self.buffer is not None or self.writer is not None or self.waiting is not None
        return bool(pending and self.current(self.snapshot))

    def note_boundary(self, sequence):
        if self.waiting is not None and sequence == self.waiting[1] and self.current(self.snapshot):
            self.waiting = None
            # The caller has already checked the current provider response owner.

    def bypass_frame(self, *, replay, single_frame, speech, arrival):
        if replay or not single_frame or getattr(self.client, '_native_barge_in_pending', False):
            self.retire()
            self.bypass = True
            self.bypass_loud_at = arrival
        if not self.bypass:
            return False
        if speech is True:
            self.bypass_loud_at = arrival
        elif speech is False and self.bypass_loud_at is not None and arrival - self.bypass_loud_at >= self.quiet_seconds:
            self.bypass = False  # This final tail still takes the original path.
        return True

    def fail(self, reason):
        client = self.client
        failed_ws = client.ws
        failed_generation = client._connection_generation
        self.client._native_phrase_last_failure = reason
        self.client._fatal_error_occurred = True
        self.retire()
        async def report_and_close():
            if client.ws is not failed_ws or client._connection_generation != failed_generation:
                return
            try:
                async with asyncio.timeout(2):
                    await client._close_failed_transport('native phrase input delivery failed')
            finally:
                callback = getattr(client, 'on_status_message', None)
                if callable(callback) and client._connection_generation == failed_generation:
                    async with asyncio.timeout(2):
                        await callback(json.dumps({'code': 'ASR_INPUT_DELIVERY_FAILED'}))
        task = asyncio.create_task(report_and_close())
        self.failure_task = task
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())

    def accept(self, pcm, speech, arrival):
        snapshot = self.read_snapshot()
        if snapshot is None or type(speech) is not bool:
            self.fail('phrase_authority_unavailable')
            return False
        if self.snapshot is not None and self.snapshot != snapshot:
            self.retire()  # Never promote an old collection to a new permission/connection.
        self.snapshot = snapshot
        self.activity = time.monotonic()
        if (speech and self.waiting is not None
                and getattr(self.client, '_voice_handoff_input_sequence', 0) != self.waiting[1]):
            self.waiting = None  # Retire the prior deadline, not a fake provider boundary.
            if self.response_waiter is not None:
                self.response_waiter.cancel()
                self.response_waiter = None
        if self.writer is not None and not self.writer.done():
            if speech:
                self.fail('phrase_input_during_incomplete_write')
                return False
            return True
        if self.buffer is None and not speech:
            self.preroll.append((pcm, arrival))
            size = sum(len(frame) for frame, _ in self.preroll)
            while self.preroll and size > 9600:
                frame, stamp = self.preroll[0]
                remove = min(len(frame), size - 9600)
                remove -= remove % 2
                if remove == len(frame):
                    self.preroll.pop(0)
                else:
                    self.preroll[0] = (frame[remove:], stamp)
                size -= remove
            return True
        try:
            if self.buffer is None:
                self.buffer = PhraseInputBuffer(snapshot[0], quiet_seconds=self.quiet_seconds)
                self.sample_end = None
                self.started_at = time.monotonic()
                if self.watchdog is None or self.watchdog.done():
                    self.watchdog = asyncio.create_task(self.watch(self.epoch))
                    self.watchdog.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                for frame, stamp in self.preroll:
                    self.feed(frame, False, stamp)
                self.preroll.clear()
            self.feed(pcm, speech, arrival)
            if self.buffer.state is PhraseState.SEALED:
                batch = self.buffer.take(ownership=snapshot[0])
                self.buffer = None
                sequence = getattr(self.client, '_voice_handoff_input_sequence', 0)
                self.writer = asyncio.create_task(self.flush(batch, snapshot, sequence, self.epoch,
                    sealed_wall=time.time(), sealed_monotonic=time.monotonic()))
            return True
        except (ValueError, TypeError):
            self.fail('phrase_input_invalid_or_over_limit')
            return False

    def feed(self, pcm, speech, arrival):
        # Arrival is an estimated chunk END, not the physical first sample.
        # A sample cursor prevents variable-size/backlogged chunks overlapping.
        start = arrival - len(pcm) / 32000
        if self.sample_end is not None:
            start = max(start, self.sample_end)
        self.sample_end = start + len(pcm) / 32000
        self.buffer.feed(pcm, speech_active=speech, ownership=self.snapshot[0], captured_at=start)

    async def watch(self, epoch):
        try:
            while epoch == self.epoch:
                await asyncio.sleep(.1)
                if not self.current(self.snapshot):
                    self.retire()
                    return
                if self.buffer is not None and time.monotonic() - self.started_at > 20:
                    self.fail('phrase_input_timeout')
                    return
                if self.waiting is not None and time.monotonic() - self.waiting[0] > 30:
                    self.fail('phrase_provider_boundary_timeout')
                    return
                if self.buffer is None and self.writer is None and self.waiting is None:
                    return
        except asyncio.CancelledError:
            raise

    async def flush(self, batch, snapshot, sequence, epoch, *, sealed_wall, sealed_monotonic):
        client = self.client
        started_monotonic = time.monotonic()
        report = {'connection_generation': snapshot[0].connection_generation,
                  'input_sequence': sequence,
                  'source_samples': batch.source_samples, 'output_samples': batch.output_samples,
                  'compressed_zero_samples': batch.compressed_zero_samples, 'written_samples': 0,
                  'input_timebase': 'arrival_derived_sample_estimate',
                  'speech_end_estimated_wall': batch.speech_end_at,
                  'sealed_estimated_wall': batch.sealed_at, 'sealed_wall': sealed_wall,
                  'queue_wait_ms': (started_monotonic - sealed_monotonic) * 1000,
                  'started_wall': time.time(), 'result': 'pending'}
        client._native_phrase_last_delivery = report
        ticket = None
        watching = False
        arbiter = client._ensure_response_arbiter()
        def current():
            return epoch == self.epoch and self.current(snapshot)
        def submission_current():
            return current() and getattr(client, '_voice_handoff_input_sequence', 0) == sequence
        try:
            # Audio JSON must stay below the existing 256KB-family frame limit.
            limit = max(2, ((client._WS_FRAME_LIMIT - 2048) * 3 // 4) // 2 * 2)
            events = []
            samples = {}
            for offset in range(0, len(batch.pcm16), limit):
                pcm = batch.pcm16[offset:offset + limit]
                event = {'type': 'input_audio_buffer.append', 'event_id': 'event_phrase_' + uuid.uuid4().hex,
                         'audio': base64.b64encode(pcm).decode('ascii')}
                events.append(event)
                samples[event['event_id']] = len(pcm) // 2

            async def send_owned(event):
                is_audio = event.get('type') == 'input_audio_buffer.append'
                sent = await client.send_event(event, send_guard=submission_current if is_audio else current)
                if sent is not True:
                    raise ConnectionError('phrase provider write refused')
                count = samples.get(event.get('event_id'))
                if event.get('type') != 'input_audio_buffer.append' or count is None:
                    return  # The lane may also send its own cancellation event.
                report['written_samples'] += count
                report.setdefault('first_write_wall', time.time())
                report.setdefault('first_write_completed_ms', (time.monotonic() - sealed_monotonic) * 1000)
                if not submission_current():
                    raise ConnectionError('phrase write owner retired')
                client._note_voice_handoff_audio_append(samples=count, input_sequence=sequence)
                callback = getattr(client, 'on_native_phrase_transport_written', None)
                authority = (snapshot[0].session_id, snapshot[0].owner_token, snapshot[0].connection_generation)
                if not callable(callback) or callback(count * 2, authority) is not True:
                    raise ConnectionError('phrase write accounting owner retired')

            async with asyncio.timeout(8):
                ticket = await arbiter.enqueue(source='native_phrase', events_before_response=tuple(events),
                    automatic_audio=True, native_input_sequence=sequence,
                    event_sender=send_owned, admission_check=submission_current)
                await asyncio.shield(ticket.sent)
            if submission_current() and report['written_samples'] == batch.output_samples:
                self.waiting = (time.monotonic(), sequence)
                client._native_phrase_last_flush_wall = time.time()
                report['result'] = 'written_waiting_provider_boundary'
                self.response_waiter = asyncio.create_task(
                    self.wait_response(arbiter, ticket, snapshot, sequence, epoch))
                self.response_waiter.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                watching = True
            else:
                report['result'] = 'written_then_retired'
        except asyncio.CancelledError:
            report['result'] = 'cancelled_without_retry'
            raise
        except Exception:
            report['result'] = 'failed_without_retry' if submission_current() else 'retired'
            if submission_current():
                self.fail('phrase_write_failed')
        finally:
            if ticket is not None and not watching:
                await self.cancel_response(arbiter, ticket)
            report['completed_wall'] = time.time()
            report['write_elapsed_ms'] = (time.monotonic() - started_monotonic) * 1000
            if self.writer is asyncio.current_task():
                self.writer = None
            # Counts and timings only: no PCM, transcript, owner token or wire payload.
            try:
                logger.info('native phrase delivery %s', json.dumps(report, sort_keys=True))
            except Exception:
                report['diagnostic_log_failed'] = True

    async def cancel_response(self, arbiter, ticket):
        try:
            async with asyncio.timeout(2):
                await arbiter.cancel_ticket(ticket, wait=False)
        except Exception:
            logger.warning('native phrase ticket cancellation did not complete')

    async def wait_response(self, arbiter, ticket, snapshot, sequence, epoch):
        def current():
            return (epoch == self.epoch and self.current(snapshot)
                    and getattr(self.client, '_voice_handoff_input_sequence', 0) == sequence)
        try:
            await asyncio.shield(ticket.done)
            if current() and self.waiting is not None and self.waiting[1] == sequence:
                # shortcut: only the first owned automatic response is associated;
                # a second provider response still needs unambiguous input evidence.
                self.client._note_voice_handoff_input_boundary(expected_sequence=sequence)
        except asyncio.CancelledError:
            await self.cancel_response(arbiter, ticket)
            raise
        except Exception:
            if current():
                self.fail('phrase_response_failed')
        finally:
            if self.response_waiter is asyncio.current_task():
                self.response_waiter = None
