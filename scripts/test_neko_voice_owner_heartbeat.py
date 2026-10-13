"""Run the actual superseded-socket guard and ownership helpers, without a host."""
import ast
import asyncio
import copy
import json
import logging
from pathlib import Path
import sys
import time
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
HOSTS = (ROOT / "candidates/N.E.K.O", ROOT / "benchmarks/raw/neko-product-host")


class ExitGuard(ast.NodeTransformer):
    # The production guard lives inside the receive loop. Execute exactly one
    # message, returning at its continue/break sites instead of reading another.
    def visit_Continue(self, node):
        return ast.copy_location(ast.Return(), node)

    def visit_Break(self, node):
        return ast.copy_location(ast.Return(), node)


class Socket:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def close(self):
        self.closed = True


def execute_guard(source, action, lease="old"):
    tree = ast.parse(source)
    guard = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                 and "session_id.get(lanlan_name) != this_session_id" in ast.unparse(node.test))
    helpers = [copy.deepcopy(node) for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and node.name in
               {"_owns_voice_connection", "_voice_identity_vacated", "_is_voice_path_message"}]
    run = ast.parse("async def run():\n    pass").body[0]
    run.body = [ExitGuard().visit(copy.deepcopy(guard))]
    ws, winner = Socket(), object()
    manager = SimpleNamespace(_voice_lease_connection_id=lease, websocket=winner)
    sessions = {"YUI": "new"}
    ns = {"json": json, "voice_input_claimed": True, "session_manager": {"YUI": manager},
          "lanlan_name": "YUI", "this_session_id": "old", "session_id": sessions,
          "malformed": False, "websocket": ws, "message": {"action": action},
          "_is_music_playback_state_message": lambda _: False,
          "logger": SimpleNamespace(info=lambda *_: None, debug=lambda *_: None)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[*helpers, run], type_ignores=[])),
                 "production_voice_owner_guard", "exec"), ns)
    asyncio.run(ns["run"]())
    assert sessions == {"YUI": "new"} and manager.websocket is winner
    return ws


class HeartbeatTest(unittest.TestCase):
    def test_voice_owner_survives_heartbeat_without_gaining_text_authority(self):
        for host in HOSTS:
            source = (host / "main_routers/websocket_router.py").read_text(encoding="utf8")
            with self.subTest(host=str(host)):
                alive = execute_guard(source, "ping")
                self.assertFalse(alive.closed)
                self.assertEqual(alive.sent, [{"type": "pong"}])
                for action, lease in (("ping", "new"), ("ping", ""), ("chat", "old")):
                    retired = execute_guard(source, action, lease)
                    self.assertTrue(retired.closed)
                    self.assertEqual(json.loads(retired.sent[0]["message"])["code"],
                                     "CHARACTER_SWITCHING_TERMINAL")

    def test_original_guard_reproduces_the_observed_failure(self):
        tree = ast.parse((HOSTS[0] / "main_routers/websocket_router.py").read_text(encoding="utf8"))
        guard = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                     and "session_id.get(lanlan_name) != this_session_id" in ast.unparse(node.test))
        guard.body = [node for node in guard.body if not (isinstance(node, ast.If)
                      and 'message.get(\'action\') == \'ping\'' in ast.unparse(node.test))]
        self.assertTrue(execute_guard(ast.unparse(tree), "ping").closed)

    def test_two_asgi_clients_keep_voice_until_an_actual_takeover(self):
        """Unchanged full endpoint, ASGI frames; provider/manager boundary is a fixture."""
        async def no_external_audio(*args):
            return False

        class Manager:
            pending_agent_callbacks = ()
            input_mode = "audio"
            _voice_lease_connection_id = ""

            def __init__(self):
                self.frames = []
                self.cleaned = []

            def _begin_voice_input_connection(self, connection_id):
                self._voice_lease_connection_id = connection_id

            async def _handle_voice_input_control(self, *args, **kwargs):
                return True

            async def stream_data(self, message):
                self.frames.append(message)

            async def cleanup(self, **kwargs):
                self.cleaned.append(kwargs)

            async def _revoke_voice_input_connection(self, connection_id):
                if self._voice_lease_connection_id == connection_id:
                    self._voice_lease_connection_id = ""

            async def send_status(self, message):
                await self.websocket.send_text(json.dumps({"type": "status", "message": message}))

        # Block telemetry/capture/preview side effects at external boundaries.
        modules = {}
        for name in ("utils.instrument", "utils.capture_bridge", "main_logic.voice_input.preview"):
            module = ModuleType(name)
            for attr in ("counter", "histogram", "unmark_capture_client"):
                setattr(module, attr, lambda *args, **kwargs: None)
            module.preview_isolation_registry = SimpleNamespace(release_connection=lambda *args: None)
            modules[name] = module

        for host in HOSTS:
            with self.subTest(host=str(host)), patch.dict("sys.modules", modules):
                manager, sessions = Manager(), {}
                tree = ast.parse((host / "main_routers/websocket_router.py").read_text(encoding="utf8"))
                body = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        node.decorator_list = []
                        body.append(node)
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        if any(isinstance(t, ast.Name) and t.id.startswith("_") for t in targets):
                            body.append(node)
                ns = {"__name__": __name__, "asyncio": asyncio, "json": json, "time": time,
                      "uuid": uuid, "WebSocket": WebSocket, "WebSocketDisconnect": WebSocketDisconnect,
                      "logger": logging.getLogger("router_fixture"), "re": __import__("re"),
                      "array": __import__("array"), "struct": __import__("struct"), "sys": sys,
                      "get_config_manager": lambda: None, "get_session_manager": lambda: {"YUI": manager},
                      "get_session_id": lambda: sessions, "is_theater_active": lambda *args: False,
                      "route_external_microphone_audio": no_external_audio,
                      "is_supported_language_code": lambda value: False,
                      "get_active_icebreaker_route_session_id": lambda *args: ""}
                exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                             str(host / "main_routers/websocket_router.py"), "exec"), ns)
                app = FastAPI()
                app.websocket("/ws/{lanlan_name}")(ns["websocket_endpoint"])
                with TestClient(app) as client, client.websocket_connect("/ws/YUI") as voice:
                    voice.send_json({"action": "voice_input_control", "engaged": True,
                                     "event": "lease_sync", "owner": "core", "lease_generation": 1})
                    voice.send_json({"action": "ping"})
                    self.assertEqual(voice.receive_json(), {"type": "pong"})
                    voice_id = manager._voice_lease_connection_id
                    with client.websocket_connect("/ws/YUI") as display:
                        display.send_json({"action": "ping"})
                        self.assertEqual(display.receive_json(), {"type": "pong"})
                        display_id = str(sessions["YUI"])
                        self.assertNotEqual(voice_id, display_id)
                        for _ in range(3):
                            voice.send_json({"action": "ping"})
                            self.assertEqual(voice.receive_json(), {"type": "pong"})
                        voice.send_bytes(b"NEKO" + (16000).to_bytes(4, "little") + b"\0\0" * 512)
                        voice.send_json({"action": "ping"})
                        self.assertEqual(voice.receive_json(), {"type": "pong"})
                        self.assertEqual(len(manager.frames), 1)
                        self.assertEqual(manager.frames[0]["input_type"], "audio")
                        self.assertEqual(str(sessions["YUI"]), display_id)
                        self.assertEqual(manager._voice_lease_connection_id, voice_id)
                        self.assertEqual(manager.cleaned, [])
                        # Only actual voice engagement takes over; opening a display did not.
                        display.send_json({"action": "voice_input_control", "engaged": True,
                                           "event": "lease_sync", "owner": "core", "lease_generation": 2})
                        display.send_json({"action": "ping"})
                        self.assertEqual(display.receive_json(), {"type": "pong"})
                        self.assertEqual(manager._voice_lease_connection_id, display_id)
                        voice.send_json({"action": "ping"})
                        retired = voice.receive_json()
                        self.assertEqual(json.loads(retired["message"])["code"], "CHARACTER_SWITCHING_TERMINAL")
                        with self.assertRaises(WebSocketDisconnect):
                            voice.receive_json()
                        display.send_json({"action": "ping"})
                        self.assertEqual(display.receive_json(), {"type": "pong"})
                        self.assertEqual(manager._voice_lease_connection_id, display_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
