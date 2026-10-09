"""Exercise the patched upstream methods and real gate without starting providers."""
import ast
import asyncio
import importlib.util
import json
import os
import queue
import sys
import threading
import types
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "benchmarks/raw/neko-product-host"
os.environ["NEKO_DEV_TEXT_ONLY"] = "1"
os.environ.pop("NEKO_DEV_AUDIO_AUDIT", None)
spec = importlib.util.spec_from_file_location("dev_text_only", HOST / "utils/dev_text_only.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
utils = types.ModuleType("utils")
utils.dev_text_only = gate
sys.modules["utils"] = utils


def upstream(path, name, class_name=None, **values):
    tree = ast.parse((HOST / path).read_text(encoding="utf-8"))
    body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body if class_name else tree.body
    node = next(n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    namespace = {"dev_text_only": gate, "Optional": Optional, **values}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, "exec"), namespace)
    return namespace[name]


downstream = {"provider": 0, "websocket": 0, "telemetry": 0}


def provider(*args, **kwargs):
    downstream["provider"] += 1
    raise AssertionError("provider reached")


class Logger:
    def warning(self, *args): pass
    def error(self, *args): pass


def telemetry(*args):
    downstream["telemetry"] += 1


dummy = upstream("main_logic/tts_client/workers/dummy.py", "dummy_tts_worker",
                 logger=Logger(), TTS_SHUTDOWN_SENTINEL="shutdown", _record_tts_telemetry=telemetry)
selector = upstream("main_logic/tts_client/__init__.py", "get_tts_worker", dummy_tts_worker=dummy,
                    get_config_manager=provider)
assert selector("free", True, "remote-voice") == (dummy, None, None)
runtime = "main_logic/core/tts_runtime.py"
resolve = upstream(runtime, "_resolve_tts_worker_spec", "TtsRuntimeMixin",
                   dummy_tts_worker=dummy, _core_facade=types.SimpleNamespace(get_tts_worker=provider))
host = types.SimpleNamespace(voice_id="remote-voice")
assert resolve(host) == (dummy, "", "remote-voice", None, True, {})
request, response = queue.Queue(), queue.Queue()
thread = threading.Thread(target=dummy, args=(request, response, "", ""))
thread.start()
assert response.get(timeout=2) == ("__ready__", True)
request.put(("synthetic-speech", "This is synthetic teaching text."))
request.put(("shutdown", None))
thread.join(timeout=2)
assert not thread.is_alive() and response.empty()


class Socket:
    async def send_json(self, *args): downstream["websocket"] += 1
    async def send_bytes(self, *args): downstream["websocket"] += 1


async def check_audio():
    socket = Socket()
    host.websocket = socket
    send = upstream(runtime, "send_speech", "TtsRuntimeMixin")
    assert await send(host, b"synthetic-pcm16") is False
    write = upstream(runtime, "_write_audio_frame", "TtsRuntimeMixin")
    await write(host, socket, {"type": "audio"}, b"synthetic-cached-pcm16")
    native = upstream("main_logic/core/turn.py", "handle_audio_data", "TurnMixin")
    await native(host, b"synthetic-native-pcm16")
    connect = upstream("main_logic/omni_realtime_client/_transport.py", "connect", "_TransportMixin")
    try:
        await connect(host, "synthetic instruction", native_audio=True)
    except RuntimeError as error:
        assert "development text-only host" in str(error)
    else:
        raise AssertionError("realtime connect was allowed")
    assert host._native_audio is False
    capabilities = []
    ping = upstream("app/agent_server/capabilities.py", "_fire_agent_llm_connectivity_check",
                    _set_capability=lambda *args: capabilities.append(args))
    await ping()
    assert capabilities == [("computer_use", False, "development_text_only"),
                            ("browser_use", False, "development_text_only")]


asyncio.run(check_audio())
expected = {"tts_provider_selection_blocked", "tts_worker_selection_blocked", "ordinary_tts_request_blocked",
            "speech_output_blocked", "audio_frame_blocked", "native_audio_callback_blocked",
            "native_realtime_connect_blocked", "agent_connectivity_probe_blocked"}
assert all(gate.COUNTS[event] == 1 for event in expected), gate.COUNTS
assert downstream == {"provider": 0, "websocket": 0, "telemetry": 0}, downstream
result = {"status": "PASS_PATCHED_SOURCE_AUDIO_BOUNDARIES", "counts": dict(gate.COUNTS),
          "downstream": downstream, "real_host_booted": False,
          "scope": "Patched upstream method bodies and real dev gate; no injected mute guard, network, devices, keys, or database."}
print(json.dumps(result, indent=2))
