"""Offline native handoff checks, reusing the existing queue socket/client fixture."""
import ast
import asyncio
import base64
import contextvars
from functools import partial, wraps
import inspect
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "benchmarks/raw/neko-product-host"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_neko_realtime_barge_in import QUIET_16K
from test_neko_tool_result_lifecycle import QueueSocket, LogRecorder
from main_logic.voice_input.activation.contracts import ActivationGeneration, OutputCommit
from main_logic.omni_realtime_client import OmniRealtimeClient
from main_logic.omni_realtime_client import _transport as transport
from websockets import exceptions as web_exceptions


def production_method(relative, name):
    tree = ast.parse((HOST / relative).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.returns = None
    node.decorator_list = []
    for arg in node.args.args + node.args.kwonlyargs:
        arg.annotation = None
    ns = dict(asyncio=asyncio, time=time, json=json, math=math, web_exceptions=web_exceptions,
              inspect=inspect, partial=partial, wraps=wraps,
              logger=LogRecorder(), OutputCommit=OutputCommit,
              _core_facade=SimpleNamespace(OmniRealtimeClient=OmniRealtimeClient),
              _start_context=contextvars.ContextVar("start", default=None),
              _ORPHAN_SESSION_REAPER_TASKS=set())
    exec(compile(ast.Module(body=[node], type_ignores=[]), relative, "exec"), ns)
    return ns[name]


class FrontendSocket:
    def __init__(self):
        self.messages = []
    async def send_json(self, message):
        self.messages.append(message)


class OfflineManager:
    def __init__(self, client):
        self.session = client
        self.is_active = True
        self.session_ready = True
        self._asr_route_mode = "native"
        self._voice_lease_owner = "core"
        self._takeover_active = False
        self.session_closed_by_server = False
        self.scope = ActivationGeneration("offline", 1, 1, 1, 1, "core")
        self.websocket = FrontendSocket()
        self.lock = asyncio.Lock()
        self._core_voice_session_swap_lock = asyncio.Lock()
        self._audio_frame_lock = asyncio.Lock()
        self._core_voice_session_swap_barrier_timeout_s = .05
        self._core_voice_listener_cancel_timeout_s = .05
        self._native_activation_reconnect_timeout_s = .15
        self.message_handler_task = None
        self.record = SimpleNamespace(retired=False, callbacks=set())
        self.statuses = []
        self.ended = 0
        self.connects = 0
        self.closes = 0
        self.replacement_socket = None
        self.connect_gate = None
        self.connect_error = False
        self.connect_entered = asyncio.Event()
        self._omni_mic_audio_bytes = 0
        self._native_ingress_token = object()
        self.use_tts = False
        self.current_speech_id = "reused-speech"
        self._voice_session_activation_has_speech = production_method(
            "main_logic/core/asr_runtime.py", "_voice_session_activation_has_speech")
        self.lanlan_name = "offline"
        for relative, names in (
            ("main_logic/core/turn.py", ("read_current_speech_id",)),
            ("main_logic/core/asr_runtime.py", ("note_native_speech_playback_state", "_begin_native_barge_in_handoff",
                "_recover_native_barge_in", "_route_microphone_audio_unfiltered")),
            ("main_logic/core/lifecycle.py", ("_restart_message_handler_after_session_reconnect",)),
            ("main_logic/core/session_lifecycle.py", ("_bind_owned_output_callbacks",
                "_native_phrase_input_authority", "_native_phrase_transport_written")),
            ("main_logic/core/tts_runtime.py", ("_audio_chunk_header",)),
        ):
            for name in names:
                setattr(self, name, MethodType(production_method(relative, name), self))
        client._resample_uplink = lambda chunk: chunk
        client._create_audio_processor = lambda: None
        client.get_host_turn_id = self.read_current_speech_id
        real_close, real_connect = client.close, client.connect

        async def close():
            self.closes += 1
            await real_close()
        async def connect(_instructions, *, native_audio):
            async def offline_connect(*_args, **_kwargs):
                self.connects += 1
                self.connect_entered.set()
                if self.connect_gate:
                    await self.connect_gate.wait()
                if self.connect_error:
                    raise ConnectionError("offline reconnect failure")
                self.replacement_socket = QueueSocket()
                return self.replacement_socket
            with patch.object(transport.websockets, "connect", offline_connect):
                await real_connect(_instructions, native_audio=native_audio)
        client.close = close
        client.connect = connect
        async def output(_bytes):
            async with self._audio_frame_lock:
                await self.websocket.send_json(self._audio_chunk_header("reused-speech"))
        client.on_audio_delta = output
        self._bind_owned_output_callbacks(client)
        self.note_native_speech_playback_state({"active": True,
            "sdk_speech_correlation_id": client._native_output_connection_token}, self.websocket)

    def _capture_voice_session_activation_generation(self): return self.scope
    def _voice_input_accepts_pcm(self): return self.is_active
    def _capture_native_ingress_token(self): return self._native_ingress_token
    def _record_omni_microphone_audio(self, count): self._omni_mic_audio_bytes += count
    def _connection_record(self, _): return self.record
    def _ensure_audio_frame_send_lock(self): return self._audio_frame_lock
    def _game_speech_correlation_for(self, _): return ""
    def speech_playback_gain(self, _): return 1
    async def send_status(self, payload): self.statuses.append(json.loads(payload))
    async def send_session_ended_by_server(self): self.ended += 1
    async def _close_owned_session(self, source): await source.close()
    async def _close_independent_asr(self, *, next_route_mode): self._asr_route_mode = next_route_mode
    async def disconnected_by_server(self, *, expected_session, announce_disconnect):
        if self.session is expected_session:
            self.is_active = False
            self.session = None
            self.record.retired = True
            self.ended += 1


class NativeHandoffTest(unittest.TestCase):
    async def fixture(self):
        client = OmniRealtimeClient("wss://lanlan.app/offline", "offline-key",
            model="free-model", api_type="free", on_tool_call=None)
        old_socket = QueueSocket()
        client.ws = old_socket
        client._on_connection_attached()
        client._ai_recent_activity_time = time.time()
        self.assertTrue(client._is_free_proxy)
        manager = OfflineManager(client)
        manager.message_handler_task = asyncio.create_task(client.handle_messages())
        await asyncio.sleep(0)
        return manager, client, old_socket

    async def feed(self, manager, count=20, *, offset=0, speech=True):
        frames = []
        for index in range(count):
            # Host VAD says speech even though PCM is below the old RMS threshold.
            frame = struct.pack("<h", index + offset + 1) * 512 if speech else QUIET_16K
            frames.append(frame)
            await manager._route_microphone_audio_unfiltered(frame, sample_rate_hz=16000,
                speech_probability=.9 if speech else .1, rnnoise_available=True,
                captured_at=100.0 + (index + offset) * .032)
        return frames

    async def dispose(self, manager, *extra):
        tasks = [manager.message_handler_task, *extra]
        tasks = [task for task in tasks if task is not None and not task.done()]
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)

    def test_production_manager_without_speech_id_enters_handoff_without_marking_session_closed(self):
        async def run():
            manager, client, old = await self.fixture()
            self.assertFalse(hasattr(manager, "speech_id"))
            self.assertEqual(client._read_host_turn_id(), manager.read_current_speech_id())
            manager.connect_gate = asyncio.Event()
            await self.feed(manager)
            self.assertFalse(manager.session_closed_by_server,
                "An onset callback error must not strand subsequent microphone PCM")
            task = client._native_barge_in_task
            await manager.connect_entered.wait()
            self.assertTrue(old.closed)
            tail = await self.feed(manager, 4, offset=20)
            manager.connect_gate.set()
            await task
            self.assertFalse(manager.session_closed_by_server)
            self.assertEqual(manager.ended, 0)
            self.assertEqual(manager.connects, 1)
            actual = [base64.b64decode(e["audio"]) for e in manager.replacement_socket.sent
                      if e["type"] == "input_audio_buffer.append"]
            self.assertEqual(actual[-4:], tail)
            await self.dispose(manager)
        asyncio.run(run())

    def test_old_connection_isolated_question_prefix_and_tail_replayed_once_new_answer_survives(self):
        async def run():
            manager, client, old = await self.fixture()
            old_token = client._native_output_connection_token
            manager.connect_gate = asyncio.Event()
            prefix = await self.feed(manager)
            task = client._native_barge_in_task
            await manager.connect_entered.wait()
            tail = await self.feed(manager, 8, offset=20)
            self.assertTrue(old.closed)
            old.feed({"type": "response.audio.delta", "delta": "AAAAAA=="})
            manager.connect_gate.set()
            await task
            new = manager.replacement_socket
            self.assertIsNotNone(new)
            actual = b"".join(base64.b64decode(event["audio"]) for event in new.sent
                              if event.get("type") == "input_audio_buffer.append")
            self.assertEqual(actual, b"".join(prefix + tail))
            stops = [m for m in manager.websocket.messages if m["type"] == "game_route_speech_cancel"]
            self.assertEqual(stops, [{"type": "game_route_speech_cancel", "sdk_speech_correlation_id": old_token}])
            self.assertNotEqual(old_token, client._native_output_connection_token)
            new.feed({"type": "response.audio.delta", "delta": "AAAAAA=="})
            for _ in range(10):
                await asyncio.sleep(0)
                if any(m["type"] == "audio_chunk" for m in manager.websocket.messages): break
            headers = [m for m in manager.websocket.messages if m["type"] == "audio_chunk"]
            self.assertEqual(len(headers), 1)
            self.assertEqual(headers[0]["speech_id"], "reused-speech")
            self.assertEqual(headers[0]["sdk_speech_correlation_id"], client._native_output_connection_token)
            self.assertEqual(manager.ended, 0)
            playback = subprocess.run(["node", str(ROOT / "scripts/test_neko_native_barge_in_playback.js"), "--handoff"],
                input=json.dumps({"stop": stops[0], "header": headers[0]}),
                text=True, capture_output=True, timeout=10)
            self.assertEqual(playback.returncode, 0, playback.stderr)
            self.assertIn("PASS: production host handoff events", playback.stdout)
            await self.dispose(manager)
        asyncio.run(run())

    def test_preroll_and_long_host_scored_question_survive_without_silence_clear_or_reconnect_storm(self):
        async def run():
            manager, client, _ = await self.fixture()
            manager.connect_gate = asyncio.Event()
            quiet = await self.feed(manager, 10, speech=False)
            prefix = await self.feed(manager, offset=10)
            task = client._native_barge_in_task
            await manager.connect_entered.wait()
            tail = await self.feed(manager, 100, offset=30)
            manager.connect_gate.set()
            await task
            # Existing buffer replay rule includes the one frame crossing the .3s boundary.
            pcm = b"".join(base64.b64decode(e["audio"]) for e in manager.replacement_socket.sent
                           if e["type"] == "input_audio_buffer.append")
            self.assertEqual(pcm, b"".join(quiet + prefix + tail))
            self.assertFalse(any(e["type"] == "input_audio_buffer.clear" for e in manager.replacement_socket.sent))
            manager.note_native_speech_playback_state({"active": True,
                "sdk_speech_correlation_id": client._native_output_connection_token}, manager.websocket)
            await self.feed(manager, 20, offset=130)
            self.assertEqual(manager.connects, 1, "same uninterrupted question must not cancel its new answer")
            await self.dispose(manager)
        asyncio.run(run())

    def test_new_physical_generation_while_waiting_for_swap_cannot_be_closed_by_old_handoff(self):
        async def run():
            manager, client, _ = await self.fixture()
            await manager._core_voice_session_swap_lock.acquire()
            await self.feed(manager)
            task = client._native_barge_in_task
            winner = QueueSocket()
            client.ws = winner
            client._on_connection_attached()
            manager._core_voice_session_swap_lock.release()
            await task
            self.assertIs(client.ws, winner)
            self.assertFalse(winner.closed)
            self.assertEqual(manager.ended, 0)
            self.assertEqual(manager.connects, 0)
            self.assertFalse(client._native_barge_in_pending)
            await self.dispose(manager)
        asyncio.run(run())

    def test_cancel_resistant_old_listener_retires_session_without_starting_a_competing_reader(self):
        async def run():
            manager, client, _ = await self.fixture()
            await self.dispose(manager)
            release = asyncio.Event()
            async def stuck():
                while not release.is_set():
                    try:
                        await release.wait()
                    except asyncio.CancelledError:
                        pass
            listener = asyncio.create_task(stuck())
            manager.message_handler_task = listener
            await asyncio.sleep(0)
            await self.feed(manager)
            await client._native_barge_in_task
            self.assertIsNone(manager.session)
            self.assertFalse(manager.is_active)
            self.assertEqual(manager.connects, 0)
            self.assertEqual(manager.ended, 1)
            self.assertFalse(client._native_barge_in_pending)
            release.set()
            await listener
            await self.dispose(manager)
        asyncio.run(run())

    def test_no_speech_or_drained_playback_never_starts_reconnect(self):
        async def run():
            manager, client, _ = await self.fixture()
            await self.feed(manager, speech=False)
            self.assertFalse(getattr(client, "_native_barge_in_pending", False))
            manager.note_native_speech_playback_state({"active": False,
                "sdk_speech_correlation_id": client._native_output_connection_token}, manager.websocket)
            await self.feed(manager, offset=20)
            self.assertEqual(manager.connects, 0)
            self.assertEqual(manager.websocket.messages, [])
            await self.dispose(manager)
        asyncio.run(run())

    def test_short_onset_and_existing_game_owner_are_not_cancelled(self):
        async def run():
            manager, client, _ = await self.fixture()
            await self.feed(manager, 5)
            self.assertFalse(getattr(client, "_native_barge_in_pending", False))
            self.assertEqual(manager.websocket.messages, [])
            manager._game_speech_correlation_for = lambda _: "game-owned"
            await self.feed(manager, offset=5)
            self.assertEqual(manager.connects, 0)
            self.assertEqual(manager.websocket.messages, [])
            await self.dispose(manager)
        asyncio.run(run())

    def test_replay_transport_error_is_explicit_failure_and_permission_change_never_replays(self):
        async def run():
            for failure in ("write", "permission"):
                manager, client, _ = await self.fixture()
                manager.connect_gate = asyncio.Event()
                await self.feed(manager)
                task = client._native_barge_in_task
                await manager.connect_entered.wait()
                if failure == "permission":
                    manager.scope = ActivationGeneration("offline", 1, 1, 1, 2, "core")
                else:
                    original_send = QueueSocket.send
                    async def reject_audio(socket, payload):
                        if json.loads(payload)["type"] == "input_audio_buffer.append":
                            raise ConnectionError("offline write failure")
                        await original_send(socket, payload)
                with patch.object(QueueSocket, "send", reject_audio if failure == "write" else QueueSocket.send):
                    manager.connect_gate.set()
                    await task
                self.assertEqual(manager.ended, 1)
                self.assertIn({"code": "ASR_INPUT_DELIVERY_FAILED"}, manager.statuses)
                self.assertFalse(client._native_barge_in_pending)
                self.assertFalse(any(e["type"] == "input_audio_buffer.append" for e in manager.replacement_socket.sent))
                await self.dispose(manager)
        asyncio.run(run())

    def test_playback_state_rejects_other_socket_and_retired_connection(self):
        async def run():
            manager, client, _ = await self.fixture()
            token = client._native_output_connection_token
            manager.note_native_speech_playback_state({"active": False,
                "sdk_speech_correlation_id": token}, object())
            manager.note_native_speech_playback_state({"active": False,
                "sdk_speech_correlation_id": "native_connection_retired"}, manager.websocket)
            self.assertTrue(client._native_playback_active)
            await self.dispose(manager)
        asyncio.run(run())

    def test_reconnect_failure_and_timeout_end_failed_voice_without_retry_loop(self):
        async def run():
            for failure in ("error", "timeout"):
                manager, client, _ = await self.fixture()
                manager.connect_error = failure == "error"
                if failure == "timeout": manager.connect_gate = asyncio.Event()
                await self.feed(manager)
                await client._native_barge_in_task
                self.assertEqual(manager.connects, 1)
                self.assertEqual(manager.ended, 1)
                self.assertIn({"code": "ASR_INPUT_DELIVERY_FAILED"}, manager.statuses)
                self.assertIsNone(manager.session)
                self.assertFalse(client._native_barge_in_pending)
                self.assertEqual(client._native_barge_in_buffer.total_bytes, 0)
                await self.dispose(manager)
            # A fresh normal session remains usable after the failures.
            manager, client, _ = await self.fixture()
            await self.feed(manager)
            await client._native_barge_in_task
            self.assertEqual(manager.ended, 0)
            self.assertEqual(manager.connects, 1)
            await self.dispose(manager)
        asyncio.run(run())

    def test_session_replaced_during_reconnect_cannot_replay_old_question_or_end_winner(self):
        async def run():
            manager, client, _ = await self.fixture()
            manager.connect_gate = asyncio.Event()
            await self.feed(manager)
            task = client._native_barge_in_task
            await manager.connect_entered.wait()
            winner = object()
            manager.session = winner
            manager.connect_gate.set()
            await task
            self.assertIs(manager.session, winner)
            self.assertEqual(manager.ended, 0)
            self.assertFalse(any(e['type'] == 'input_audio_buffer.append'
                                 for e in manager.replacement_socket.sent))
            self.assertTrue(manager.replacement_socket.closed)
            await self.dispose(manager)
        asyncio.run(run())

    def test_pcm_overflow_is_reported_not_partially_replayed(self):
        async def run():
            manager, client, _ = await self.fixture()
            manager.connect_gate = asyncio.Event()
            await self.feed(manager)
            task = client._native_barge_in_task
            await manager.connect_entered.wait()
            # The existing 8s buffer limit is enforced while the connection is unavailable.
            await self.feed(manager, 270, offset=20)
            manager.connect_gate.set()
            await task
            self.assertFalse(any(e['type'] == 'input_audio_buffer.append'
                                 for e in manager.replacement_socket.sent))
            self.assertEqual(manager.ended, 1)
            self.assertIn({"code": "ASR_INPUT_DELIVERY_FAILED"}, manager.statuses)
            await self.dispose(manager)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
