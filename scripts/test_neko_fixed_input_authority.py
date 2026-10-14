"""Actual Core lease/registry/queue methods; no capture, provider or devices.

Reuse the Native tests' AST isolation pattern and deployed HOST location.
Only the ASR lifecycle boundary and worker startup are stubs. Authorization,
lease transitions, token capture, registry selection and queue insertion are
the actual production implementations.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys
import time
import types
from typing import Any, ClassVar
import unittest
from unittest.mock import AsyncMock, Mock

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from test_neko_native_barge_in import HOST, LogRecorder  # noqa: E402

sys.path.insert(0, str(HOST))
from main_logic.voice_input import (  # noqa: E402
    BuiltinVoiceInputConsumer, VoiceInputRegistry, VoiceInputConsumerCapabilities)
from main_logic.voice_input.consumers import (  # noqa: E402
    CoreChatVoiceInputConsumer, GameVoiceInputConsumer)
from main_logic.voice_input.preview import preview_isolation_registry  # noqa: E402
from main_logic.asr_client.runtime import AsrRuntimeCallbacks, IndependentAsrRuntime  # noqa: E402
from main_logic.voice_turn.audio_input import VoiceInputAudioPipeline  # noqa: E402
from utils.game_route_state import get_active_game_route_generation_identity  # noqa: E402

if "main_logic.core" in sys.modules or "memory.recent" in sys.modules:
    raise RuntimeError("fixed-input fixture must not import Core/Memory startup logging")

# Importing Core's package also initializes application Memory file logging.
# Use the established Native test AST isolation, retaining the actual methods,
# registry and duration queue without importing Core/Memory or starting a host.
source = HOST / "main_logic/core/asr_runtime.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
names = {"AsrRuntimeMixin", "_QueuedMicFrame", "_AudioDurationQueue", "_HotSwapAudioBuffer"}
module = types.ModuleType("fixed_input_actual_core")
sys.modules[module.__name__] = module
module.__dict__.update(globals(), __name__="fixed_input_actual_core", logger=LogRecorder())
nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
nodes += [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in names]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source), "exec"),
     module.__dict__)
AsrRuntimeMixin = module.AsrRuntimeMixin


class _Runtime(AsrRuntimeMixin):
    def __init__(self):
        self.lanlan_name = "fixed-input-offline"
        self.session = types.SimpleNamespace()
        self.send_status = AsyncMock()
        self._init_asr_runtime_state()


def fixed_frame():
    # Small fixed in-memory values; no WAV/device/capture or output playback.
    return {"input_type": "audio", "sample_rate_hz": 16_000, "data": [1] * 160}


class FixedInputAuthority(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = _Runtime()
        self.manager._asr_route_mode = "native"
        self.manager._asr_runtime.abort = AsyncMock()
        self.manager._asr_runtime.suspend = AsyncMock()
        self.manager._asr_runtime.resume = AsyncMock()
        # Stop at the real bounded ingress queue, before processing/provider.
        self.manager._ensure_audio_stream_worker = Mock()
        self.assertIs(self.manager._voice_input_accepts_pcm.__func__,
                      AsrRuntimeMixin._voice_input_accepts_pcm)
        self.assertIs(self.manager._apply_voice_lease_state.__func__,
                      AsrRuntimeMixin._apply_voice_lease_state)
        self.assertTrue(self.manager._begin_voice_input_connection("native-current"))

    async def asyncTearDown(self):
        self.manager._clear_audio_stream_queue("offline_test_cleanup")
        await self.manager._voice_input_registry.wait_idle()

    async def sync(self, generation, *, owner="core", muted=False, focus=False):
        return await self.manager._handle_voice_input_control(
            "lease_sync", generation, owner=owner,
            hard_muted=muted, focus_suppressed=focus)

    async def assert_rejected_frame(self):
        self.assertFalse(self.manager._voice_input_accepts_pcm())
        await self.manager._enqueue_audio_stream_data(fixed_frame())
        self.assertTrue(self.manager._audio_stream_queue.empty())
        self.manager._ensure_audio_stream_worker.assert_not_called()

    async def test_synchronized_none_authorizes_session_but_does_not_enqueue_pcm(self):
        self.assertTrue(await self.sync(1, owner="none"))
        self.assertTrue(await self.manager._ensure_voice_input_session_authorized("native-current"))
        self.assertEqual(self.manager._voice_lease_owner, "none")
        self.assertEqual(self.manager._voice_lease_generation, 1)
        await self.assert_rejected_frame()

    async def test_current_core_snapshot_and_real_registry_enqueue_owned_frame(self):
        self.assertTrue(await self.sync(1))
        self.assertTrue(await self.manager._ensure_voice_input_session_authorized("native-current"))
        identity = self.manager._voice_input_registry.active_identity
        self.assertEqual(identity.namespace, "builtin")
        self.assertEqual(identity.name, BuiltinVoiceInputConsumer.CORE_CHAT.value)
        self.assertTrue(self.manager._voice_input_accepts_pcm())
        await self.manager._enqueue_audio_stream_data(fixed_frame())
        self.assertEqual(self.manager._audio_stream_queue.qsize(), 1)
        frame = self.manager._audio_stream_queue.get_nowait()
        self.manager._audio_stream_queue.task_done()
        self.assertEqual(frame.message, fixed_frame())
        self.assertEqual(frame.token.connection_id, "native-current")
        self.assertEqual(frame.token.lease_generation, 1)
        self.assertTrue(self.manager._ingress_token_matches(frame.token))
        self.manager._complete_hot_swap_ingress_sequence(frame.ingress_sequence)
        self.manager._ensure_audio_stream_worker.assert_called_once()

    async def test_equal_or_lower_generation_cannot_override_newer_owner_none(self):
        self.assertTrue(await self.sync(4, owner="none"))
        before = (self.manager._voice_lease_owner, self.manager._voice_lease_generation,
                  self.manager._microphone_route_generation)
        for generation in (3, 4):
            with self.subTest(generation=generation):
                self.assertFalse(await self.sync(generation))
                self.assertEqual((self.manager._voice_lease_owner,
                    self.manager._voice_lease_generation,
                    self.manager._microphone_route_generation), before)
                await self.assert_rejected_frame()
        self.assertTrue(await self.sync(5))
        self.assertTrue(self.manager._voice_input_accepts_pcm())

    async def test_previous_connection_cannot_authorize_redirect_or_revoke_current_lease(self):
        self.assertTrue(await self.sync(1))
        old_token = self.manager._capture_ingress_token()
        self.assertTrue(self.manager._begin_voice_input_connection("native-replacement"))
        self.assertTrue(await self.sync(1))
        self.assertFalse(await self.manager._ensure_voice_input_session_authorized("native-current"))
        self.assertFalse(self.manager._set_voice_input_websocket("native-current", object()))
        self.assertFalse(await self.manager._revoke_voice_input_connection("native-current"))
        self.assertEqual(self.manager._voice_lease_connection_id, "native-replacement")
        self.assertEqual(self.manager._voice_lease_owner, "core")
        self.assertFalse(self.manager._ingress_token_matches(old_token))
        self.assertTrue(await self.manager._ensure_voice_input_session_authorized("native-replacement"))
        self.assertTrue(self.manager._voice_input_accepts_pcm())

    async def test_mute_and_focus_snapshot_block_pcm_despite_session_authorized(self):
        for generation, muted, focus in ((1, True, False), (2, False, True), (3, True, True)):
            with self.subTest(muted=muted, focus=focus):
                self.assertTrue(await self.sync(generation, muted=muted, focus=focus))
                self.assertTrue(await self.manager._ensure_voice_input_session_authorized("native-current"))
                await self.assert_rejected_frame()
        self.assertTrue(await self.sync(4))
        self.assertTrue(self.manager._voice_input_accepts_pcm())
        self.assertTrue(self.manager._audio_stream_queue.empty())

    async def test_core_owner_with_wrong_registry_consumer_cannot_enqueue(self):
        self.assertTrue(await self.sync(1))
        self.manager._voice_input_registry.activate(self.manager._game_voice_input_registration.handle)
        self.assertEqual(self.manager._voice_input_registry.active_identity.name,
                         BuiltinVoiceInputConsumer.GAME.value)
        self.assertEqual(self.manager._voice_lease_owner, "core")
        await self.assert_rejected_frame()

    async def test_game_owner_selects_game_consumer_and_blocks_when_game_has_no_route(self):
        self.assertTrue(await self.sync(1, owner="game"))
        self.assertEqual(self.manager._voice_input_registry.active_identity.name,
                         BuiltinVoiceInputConsumer.GAME.value)
        self.assertFalse(self.manager._voice_input_registry.active_accepts_input)
        await self.assert_rejected_frame()
        self.manager._asr_runtime.suspend.assert_awaited_once_with("lease_sync")
        self.assertTrue(await self.sync(2))
        self.assertEqual(self.manager._voice_input_registry.active_identity.name,
                         BuiltinVoiceInputConsumer.CORE_CHAT.value)
        self.assertTrue(self.manager._voice_input_accepts_pcm())

    async def test_end_none_clears_queued_input_and_disconnect_revokes_identity(self):
        self.assertTrue(await self.sync(1))
        await self.manager._enqueue_audio_stream_data(fixed_frame())
        self.assertEqual(self.manager._audio_stream_queue.qsize(), 1)
        self.manager._ensure_audio_stream_worker.reset_mock()
        old_token = self.manager._capture_ingress_token()
        self.assertTrue(await self.sync(2, owner="none"))
        self.assertFalse(self.manager._ingress_token_matches(old_token))
        await self.assert_rejected_frame()
        self.assertTrue(await self.manager._revoke_voice_input_connection("native-current"))
        self.assertEqual(self.manager._voice_lease_connection_id, "")
        self.assertFalse(self.manager._voice_lease_synchronized)
        self.assertEqual(self.manager._voice_lease_generation, -1)
        self.assertFalse(await self.manager._ensure_voice_input_session_authorized("native-current"))
        await self.assert_rejected_frame()


if __name__ == "__main__":
    unittest.main(verbosity=2)
