"""Offline guards for the opt-in probe; no host, provider, audio or room mic."""
from __future__ import annotations

import ast
import asyncio
from enum import Enum
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from neko_manual_turn_probe_patch import patch_router, patch_transport, remove_router_probe, ROUTER_HELPER

ROOT = Path(__file__).resolve().parents[1] / "candidates/N.E.K.O"


class TurnDetectionMode(Enum):
    MANUAL = "manual"
    SERVER_VAD = "server_vad"


def extract(source, wanted, namespace):
    nodes = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
            nodes.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "probe-product-methods", "exec"), namespace)
    return namespace


class ManualProbeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.transport = (ROOT / "main_logic/omni_realtime_client/_transport.py").read_text(encoding="utf-8")
        self.router = remove_router_probe((ROOT / "main_routers/websocket_router.py").read_text(encoding="utf-8"))
        self.mode = extract(patch_transport(self.transport), {"_select_free_manual_turn_probe"}, {"TurnDetectionMode": TurnDetectionMode})["_select_free_manual_turn_probe"]
        self.router_ns = extract(patch_router(self.router), {"_manual_turn_probe_enabled", "_dispatch_manual_turn_probe", "_is_voice_path_message"},
                                 {"asyncio": asyncio, "json": json, "time": time})
        self.session = SimpleNamespace(_is_free_proxy=True, _free_manual_turn_probe_enabled=True, _fatal_error_occurred=False,
            _connection_generation=1, _realtime_protocol_capabilities=SimpleNamespace(route_key="lanlan_app_gemini"),
            signal_user_activity_end=AsyncMock(), turn_detection_mode=TurnDetectionMode.SERVER_VAD)
        self.manager = SimpleNamespace(session=self.session, input_mode="audio", _asr_route_mode="native", websocket="display_socket")
        self.socket = SimpleNamespace(send_text=AsyncMock())

    def test_mode_default_off_exact_route_only_and_restore(self):
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "0"}):
            self.mode(self.session)
            self.assertEqual(self.session.turn_detection_mode, TurnDetectionMode.SERVER_VAD)
            self.assertFalse(self.router_ns["_is_voice_path_message"]({"action": "end_audio_turn"}))
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "1"}):
            for route, is_proxy in (("lanlan_tech_stepfun", False), ("strict_default", False), ("lanlan_app_gemini", False)):
                self.session._realtime_protocol_capabilities.route_key = route
                self.session._is_free_proxy = is_proxy
                self.mode(self.session)
                self.assertEqual(self.session.turn_detection_mode, TurnDetectionMode.SERVER_VAD)
            self.session._realtime_protocol_capabilities.route_key = "lanlan_app_gemini"
            self.session._is_free_proxy = True
            self.mode(self.session)
            self.assertEqual(self.session.turn_detection_mode, TurnDetectionMode.MANUAL)
            self.assertTrue(self.router_ns["_is_voice_path_message"]({"action": "end_audio_turn"}))
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "0"}):
            self.mode(self.session)
            self.assertEqual(self.session.turn_detection_mode, TurnDetectionMode.SERVER_VAD)

    async def test_actual_voice_owner_can_dispatch_despite_different_display_socket(self):
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "1"}):
            await self.router_ns["_dispatch_manual_turn_probe"](self.manager, self.socket,
                {"action": "end_audio_turn", "request_id": "fixed-1"}, owns_voice=lambda: True)
        self.session.signal_user_activity_end.assert_awaited_once()
        ack = json.loads(self.socket.send_text.call_args.args[0])
        self.assertTrue(ack["dispatched"])
        self.assertIn("local dispatch only", ack["proof"])

    async def test_disabled_stale_wrong_route_and_duplicate_do_not_commit(self):
        dispatch = self.router_ns["_dispatch_manual_turn_probe"]
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "0"}):
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: True)
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "1"}):
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: False)
            self.manager._asr_route_mode = "independent"
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: True)
            self.manager._asr_route_mode = "native"
            self.session._realtime_protocol_capabilities.route_key = "lanlan_tech_stepfun"
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: True)
            self.session._realtime_protocol_capabilities.route_key = "lanlan_app_gemini"
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: True)
            await dispatch(self.manager, self.socket, {"request_id": "x"}, owns_voice=lambda: True)
        self.session.signal_user_activity_end.assert_awaited_once()
        self.assertEqual(json.loads(self.socket.send_text.call_args.args[0])["reason"], "duplicate_request")

    async def test_existing_manual_commit_uses_original_arbiter_and_order(self):
        gemini = (ROOT / "main_logic/omni_realtime_client/_gemini_support.py").read_text(encoding="utf-8")
        method = extract(gemini, {"signal_user_activity_end"}, {"TurnDetectionMode": TurnDetectionMode, "time": time})["signal_user_activity_end"]
        async def enqueue(**kwargs):
            self.assertEqual(kwargs["source"], "manual_audio_commit")
            self.assertEqual(kwargs["events_before_response"][0]["type"], "input_audio_buffer.commit")
            self.assertEqual(kwargs["response_event"]["type"], "response.create")
            future = asyncio.get_running_loop().create_future(); future.set_result(None)
            return SimpleNamespace(sent=future)
        self.session.turn_detection_mode = TurnDetectionMode.MANUAL
        self.session._is_gemini = False
        self.session.note_user_turn_started = lambda: None
        self.session._pending_input_route_identity_commit = lambda: "voice_owner"
        self.session._clear_uplink_resampler = lambda: None
        self.session._response_arbiter = SimpleNamespace(enqueue=enqueue)
        self.session._apply_input_route_identity_commit = lambda owner: self.assertEqual(owner, "voice_owner")
        self.session._note_voice_handoff_input_boundary = lambda **kwargs: None
        await method(self.session)

    async def test_session_replacement_during_await_is_reported_and_errors_do_not_leak(self):
        async def replace_session():
            self.manager.session = SimpleNamespace()
        self.session.signal_user_activity_end = replace_session
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "1"}):
            await self.router_ns["_dispatch_manual_turn_probe"](self.manager, self.socket,
                {"request_id": "first"}, owns_voice=lambda: True)
        self.assertEqual(json.loads(self.socket.send_text.call_args.args[0])["reason"], "owner_or_session_changed_during_dispatch")
        self.manager.session = self.session
        self.session.signal_user_activity_end = AsyncMock(side_effect=RuntimeError("PRIVATE PROVIDER DETAILS"))
        with patch.dict(os.environ, {"NEKO_FREE_MANUAL_TURN_PROBE": "1"}):
            await self.router_ns["_dispatch_manual_turn_probe"](self.manager, self.socket,
                {"request_id": "second"}, owns_voice=lambda: True)
        self.assertNotIn("PRIVATE", self.socket.send_text.call_args.args[0])
        self.assertFalse(json.loads(self.socket.send_text.call_args.args[0])["dispatched"])

    def test_replay_idempotent_unknown_source_refused_and_both_dispatch_sites_present(self):
        self.assertEqual(patch_transport(patch_transport(self.transport)), patch_transport(self.transport))
        result = patch_router(self.router)
        self.assertEqual(patch_router(result), result)
        self.assertEqual(remove_router_probe(result), self.router)
        self.assertEqual(remove_router_probe(remove_router_probe(result)), self.router)
        # Losing any of the four exact blocks must fail closed.
        partials = (
            result.replace(ROUTER_HELPER, "", 1),
            result.replace('    if action == "end_audio_turn" and _manual_turn_probe_enabled():\n        return True\n', "", 1),
            result.replace('            await _dispatch_manual_turn_probe(voice_mgr, websocket, message, owns_voice=_owns_voice_connection)\n', "", 1),
            result.replace('                await _dispatch_manual_turn_probe(session_manager[lanlan_name], websocket, message, owns_voice=_owns_voice_connection)\n', "", 1),
            result + "\n# _dispatch_manual_turn_probe unexpected extra content\n",
        )
        for partial in partials:
            with self.assertRaises(ValueError):
                remove_router_probe(partial)
        self.assertEqual(result.count("await _dispatch_manual_turn_probe("), 2)
        with self.assertRaises(ValueError):
            patch_transport("# unknown source\n")
        with self.assertRaises(ValueError):
            patch_router("# unknown source\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
