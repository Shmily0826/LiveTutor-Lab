"""Diagnostic transparency only: no host imports, audio, API, DB or device."""
import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from neko_native_delivery_diagnostics import (
    DeliveryCounters, install_native_delivery_diagnostics, safe_native_snapshot,
)


class Log:
    def __init__(self, fail=False):
        self.rows = []
        self.fail = fail

    def info(self, pattern, value):
        self.rows.append(pattern % value)
        if self.fail:
            raise RuntimeError('diagnostic logger failed')


def classes():
    class Core:
        def __init__(self):
            self.calls = []
            self.is_active = True
            self._asr_route_mode = 'native'
            self._voice_lease_owner = 'core'
            self._voice_session_activation_factory = None
            self._voice_session_activation_required = False
            self._voice_session_activation_degraded = False
            self.error = None
            self.result = object()

        async def _process_microphone_stream_data(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            if self.error is not None:
                raise self.error
            return self.result

        _route_microphone_audio = _process_microphone_stream_data
        _route_microphone_audio_unfiltered = _process_microphone_stream_data

    class Phrase:
        def __init__(self):
            self.calls = 0

        def accept(self, *args, **kwargs):
            self.calls += 1
            return False

        async def flush(self, *args, **kwargs):
            self.calls += 1
            return None

    class Transport:
        def __init__(self):
            self.calls = []

        async def stream_audio(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return None

        async def send_event(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return True
    return Core, Phrase, Transport


class DiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_off_preserves_class_and_method_identity(self):
        classes_ = classes()
        before = [dict(cls.__dict__) for cls in classes_]
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(install_native_delivery_diagnostics(*classes_))
        self.assertEqual(before, [dict(cls.__dict__) for cls in classes_])
        self.assertIsNone(install_native_delivery_diagnostics(*classes_, enabled=False))

    async def test_each_original_runs_once_with_same_arguments_and_return_identity(self):
        Core, Phrase, Transport = classes()
        counters = install_native_delivery_diagnostics(Core, Phrase, Transport, enabled=True, logger=Log())
        core = Core()
        token = object()
        value = await core._process_microphone_stream_data(b'PRIVATE_PCM', ingress_token=token)
        self.assertIs(value, core.result)
        self.assertEqual(core.calls, [((b'PRIVATE_PCM',), {'ingress_token': token})])
        await core._route_microphone_audio(b'PRIVATE_PCM')
        await core._route_microphone_audio_unfiltered(b'PRIVATE_PCM')
        phrase = Phrase()
        self.assertIs(phrase.accept(b'PRIVATE_PCM', True, 2.0), False)
        self.assertIsNone(await phrase.flush(object(), token, 1, 1))
        self.assertEqual(phrase.calls, 2)
        transport = Transport()
        self.assertIsNone(await transport.stream_audio(b'PRIVATE_PCM'))
        self.assertIs(await transport.send_event({'type': 'input_audio_buffer.append', 'audio': 'PRIVATE_AUDIO'}), True)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(len(counters.snapshot()['counts']), 7)

    async def test_same_exception_and_cancellation_propagate_without_second_call(self):
        for error in (RuntimeError('PRIVATE_FAILURE'), asyncio.CancelledError('PRIVATE_CANCEL')):
            Core, _, _ = classes()
            counters = install_native_delivery_diagnostics(Core, enabled=True, logger=Log(fail=True))
            core = Core(); core.error = error
            try:
                await core._process_microphone_stream_data('PRIVATE_ARGUMENT')
            except BaseException as observed:
                self.assertIs(observed, error)
            else:
                self.fail('business exception was hidden')
            self.assertEqual(len(core.calls), 1)
            outcome = 'cancelled' if isinstance(error, asyncio.CancelledError) else 'raised'
            self.assertEqual(counters.snapshot()['counts']['core_process'][outcome], 1)

    async def test_real_task_cancellation_is_transparent(self):
        Core, _, _ = classes()
        entered = asyncio.Event()
        async def wait(self):
            self.calls.append('entered'); entered.set()
            await asyncio.Event().wait()
        Core._process_microphone_stream_data = wait
        counters = install_native_delivery_diagnostics(Core, enabled=True, logger=Log())
        core = Core(); task = asyncio.create_task(core._process_microphone_stream_data())
        await entered.wait(); task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(core.calls, ['entered'])
        self.assertEqual(counters.snapshot()['counts']['core_process']['cancelled'], 1)

    async def test_installation_is_idempotent_and_non_audio_events_are_not_counted(self):
        Core, Phrase, Transport = classes()
        counters = install_native_delivery_diagnostics(Core, Phrase, Transport, enabled=True, logger=Log())
        method = Transport.send_event
        self.assertIs(install_native_delivery_diagnostics(Core, Phrase, Transport, enabled=True), counters)
        self.assertIs(Transport.send_event, method)
        transport = Transport()
        await transport.send_event({'type': 'session.update', 'PRIVATE_SETTING': 'PRIVATE_VALUE'})
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(counters.snapshot()['counts'], {})

    async def test_safe_projection_does_not_serialize_payload_or_identity(self):
        owner = SimpleNamespace(is_active=False, _asr_route_mode='native', _voice_lease_owner='core',
            _voice_session_activation_factory=SimpleNamespace(enforce=True, noise_reduction_enabled=True),
            _voice_input_noise_reduction_enabled=False, _voice_session_activation_required=True,
            _voice_session_activation_degraded=True, transcript='PRIVATE_TEXT', pcm=b'PRIVATE_PCM',
            path='PRIVATE_PATH', key='PRIVATE_KEY', owner_token='PRIVATE_OWNER')
        projection = safe_native_snapshot(owner)
        self.assertTrue(all(value is None or type(value) is bool for value in projection.values()))
        self.assertIs(projection['noise_contract_match'], False)
        log = Log(); clock = [0.0]
        counters = DeliveryCounters(logger=log, clock=lambda: clock[0], count_limit=3)
        for _ in range(30):
            counters.observe('core_route', 'entered', owner)
        snapshot = counters.snapshot()
        self.assertEqual(snapshot['counts']['core_route']['entered'], 3)
        self.assertEqual(len(log.rows), 1)
        clock[0] = 2.0; counters.observe('core_route', 'returned_none', owner)
        self.assertEqual(len(log.rows), 2)
        serial = json.dumps(snapshot) + ''.join(log.rows)
        self.assertNotIn('PRIVATE_', serial)
        with self.assertRaises(ValueError): counters.observe('PRIVATE_STAGE', 'entered', owner)
        snapshot['counts']['core_route']['entered'] = 99
        self.assertEqual(counters.snapshot()['counts']['core_route']['entered'], 3)

    async def test_diagnostic_failures_do_not_change_a_successful_result(self):
        Core, _, _ = classes()
        counters = install_native_delivery_diagnostics(Core, enabled=True, logger=Log(fail=True))
        core = Core()
        self.assertIs(await core._process_microphone_stream_data(), core.result)
        self.assertEqual(len(core.calls), 1)
        self.assertEqual(counters.snapshot()['diagnostic_errors'], 1)

    async def test_bad_projection_is_unknown_and_validation_has_no_partial_install(self):
        class Bad:
            @property
            def is_active(self): raise RuntimeError('PRIVATE_STATE')
        self.assertIsNone(safe_native_snapshot(Bad())['active'])
        Core, _, _ = classes(); original = Core._process_microphone_stream_data
        Core._route_microphone_audio = lambda self: None
        with self.assertRaises(ValueError):
            install_native_delivery_diagnostics(Core, enabled=True)
        self.assertIs(Core._process_microphone_stream_data, original)

    async def test_unknown_event_kind_cannot_break_the_original_send(self):
        class SecretKind:
            def __eq__(self, other): raise RuntimeError('PRIVATE_EVENT_KIND')
        Core, _, Transport = classes()
        counters = install_native_delivery_diagnostics(Core, transport_class=Transport, enabled=True, logger=Log())
        event = {'type': SecretKind(), 'audio': 'PRIVATE_AUDIO'}
        transport = Transport()
        self.assertIs(await transport.send_event(event), True)
        self.assertIs(transport.calls[0][0][0], event)
        self.assertEqual(counters.snapshot()['counts'], {})

    async def test_explicit_environment_enables_only_the_requested_classes(self):
        Core, Phrase, _ = classes()
        phrase_method = Phrase.accept
        with patch.dict(os.environ, {'NEKO_NATIVE_DELIVERY_DIAGNOSTICS': '1'}):
            counters = install_native_delivery_diagnostics(Core, logger=Log())
        self.assertIsNotNone(counters)
        self.assertIs(Phrase.accept, phrase_method)

    async def test_synchronous_phrase_exception_remains_the_same_once(self):
        Core, Phrase, _ = classes()
        error = RuntimeError('PRIVATE_PHRASE_FAILURE')
        def fail(self, value):
            self.calls += 1
            raise error
        Phrase.accept = fail
        counters = install_native_delivery_diagnostics(Core, Phrase, enabled=True, logger=Log(fail=True))
        phrase = Phrase()
        try:
            phrase.accept(b'PRIVATE_PCM')
        except RuntimeError as observed:
            self.assertIs(observed, error)
        else:
            self.fail('phrase error was hidden')
        self.assertEqual(phrase.calls, 1)
        self.assertEqual(counters.snapshot()['counts']['phrase_accept']['raised'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
