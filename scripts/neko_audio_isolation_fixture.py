#!/usr/bin/env python
"""Candidate selector/callback offline-stub probe; not host-wide isolation.

This does not import or start the N.E.K.O host and does not establish OS-level
network or audio isolation. It compiles selected methods from pinned candidate
source and supplies inert queues, a counted fake provider worker, a fake
websocket, and fixture-only output guards. The harness itself invokes no real
provider, microphone, playback device, or socket.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "candidates" / "N.E.K.O"
RUNTIME = CANDIDATE / "main_logic" / "core" / "tts_runtime.py"
TURN = CANDIDATE / "main_logic" / "core" / "turn.py"
DUMMY = CANDIDATE / "main_logic" / "tts_client" / "workers" / "dummy.py"
DEFAULT_EVIDENCE = ROOT / "benchmarks" / "raw" / "evidence" / "neko-audio-isolation-fixture.json"
SHUTDOWN = "__lab_shutdown__"


def _method(path: Path, class_name: str, method_name: str, global_values=None):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            method = next(
                (item for item in node.body
                 if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and item.name == method_name),
                None,
            )
            if method is None:
                break
            isolated_class = ast.ClassDef(
                name=f"{class_name}Fixture",
                bases=[], keywords=[], body=[method], decorator_list=[],
            )
            module = ast.fix_missing_locations(ast.Module(body=[isolated_class], type_ignores=[]))
            namespace = {"Optional": Optional, "WebSocketDisconnect": type("WebSocketDisconnect", (Exception,), {})}
            namespace.update(global_values or {})
            exec(compile(module, str(path), "exec"), namespace)
            return getattr(namespace[f"{class_name}Fixture"], method_name)
    raise RuntimeError(f"{class_name}.{method_name} missing from {path}")


def _dummy_worker():
    tree = ast.parse(DUMMY.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "dummy_tts_worker"
    )

    class NullLogger:
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass

    namespace = {
        "TTS_SHUTDOWN_SENTINEL": SHUTDOWN,
        "logger": NullLogger(),
        "_record_tts_telemetry": lambda *args: None,
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(DUMMY), "exec"), namespace)
    return namespace["dummy_tts_worker"]


class _FakeArray:
    def astype(self, _dtype): return self
    def __truediv__(self, _other): return self
    def __mul__(self, _other): return self
    def clip(self, *_args): return self
    def tobytes(self): return b"synthetic-pcm16"


class _FakeNumpy:
    int16 = float32 = object()
    @staticmethod
    def frombuffer(_data, dtype=None): return _FakeArray()


class _ConnectedState:
    CONNECTED = object()
    def __eq__(self, other): return other is self.CONNECTED


class _Socket:
    def __init__(self):
        self.client_state = _ConnectedState()
        self.send_count = 0
    async def send_bytes(self, _data): self.send_count += 1
    async def send_json(self, _data): self.send_count += 1


class _Config:
    def get_core_config(self): return {"DISABLE_TTS": False}
    def get_model_api_config(self, _name): return {}


class AudioGate:
    """Fixture-only guard installed on every fixture host construction."""
    def __init__(self):
        self.counts = {
            "normal_tts_request_attempted": 0,
            "normal_tts_request_blocked": 0,
            "provider_selection_attempted": 0,
            "provider_worker_dispatch_attempted": 0,
            "provider_worker_dispatch_blocked": 0,
            "fake_provider_worker_calls": 0,
            "send_speech_calls": 0,
            "realtime_audio_blocked": 0,
            "websocket_sink_calls": 0,
        }
        self.provider_worker = self.fake_provider_worker

    def select_worker(self, **_kwargs):
        # Candidate _resolve_tts_worker_spec calls this host facade seam.
        self.counts["provider_selection_attempted"] += 1
        return self.provider_worker, None, "fixture-counted-provider"

    def fake_provider_worker(self, *_args):
        self.counts["fake_provider_worker_calls"] += 1


def _one_probe():
    dummy = _dummy_worker()
    global _dummy_worker_cache
    _dummy_worker_cache = dummy
    gate = AudioGate()
    resolve = _method(RUNTIME, "TtsRuntimeMixin", "_resolve_tts_worker_spec", {
        "dummy_tts_worker": dummy,
        "_core_facade": type("CoreFacade", (), {"get_tts_worker": staticmethod(gate.select_worker)})(),
    })
    send_speech = _method(RUNTIME, "TtsRuntimeMixin", "send_speech", {
        "logger": type("NullLogger", (), {"debug": lambda *a, **k: None, "warning": lambda *a, **k: None,
                                            "error": lambda *a, **k: None})(),
    })
    class RequestQueue:
        def __init__(self): self.inner = queue.Queue()
        def put(self, item):
            sid, text = item
            if sid != SHUTDOWN and sid is not None and text:
                gate.counts["normal_tts_request_attempted"] += 1
                gate.counts["normal_tts_request_blocked"] += 1
            return self.inner.put(item)
        def get(self): return self.inner.get()

    class FakeThread:
        def __init__(self, target, args=(), daemon=None): self.target, self.args, self.daemon = target, args, daemon
        def start(self):
            # The real candidate selector chose this counted fake worker. Block
            # before its body; its counter must remain zero to catch leakage.
            if self.target is gate.provider_worker:
                gate.counts["provider_worker_dispatch_attempted"] += 1
                gate.counts["provider_worker_dispatch_blocked"] += 1

    runtime_globals = {
        "dummy_tts_worker": dummy,
        "_core_facade": type("CoreFacade", (), {"get_tts_worker": staticmethod(gate.select_worker)})(),
        "Queue": lambda: RequestQueue() if not hasattr(_queue_factory_state, "made") else queue.Queue(),
        "Thread": FakeThread,
        "MAX_LIVE_TTS_RUNTIMES": 2,
        "TtsCapacityError": RuntimeError,
        "TTS_PROVIDER_REGISTRY": {},
        "TtsRuntimeRecord": lambda *args, **kwargs: type("Runtime", (), {"retired": False})(),
        "logger": type("NullLogger", (), {"info": lambda *a, **k: None})(),
    }
    class _FactoryState: made = False
    _queue_factory_state = _FactoryState()
    def queue_factory():
        if not _queue_factory_state.made:
            _queue_factory_state.made = True
            return RequestQueue()
        return queue.Queue()
    runtime_globals["Queue"] = queue_factory
    start_tts_thread = _method(RUNTIME, "TtsRuntimeMixin", "_start_tts_thread", runtime_globals)
    handle_audio = _method(TURN, "TurnMixin", "handle_audio_data")

    class Host:
        _resolve_tts_worker_spec = resolve
        _start_tts_thread = start_tts_thread
        handle_audio_data = handle_audio
        _config_manager = _Config()
        voice_id = "synthetic"
        core_api_type = "fixture"
        websocket = None
        current_speech_id = "synthetic-speech"
        def _effective_tts_route(self): return ("synthetic", False)
        def resolve_tts_api_key(self, *_args): return ""
        def _live_tts_runtime_count(self): return 0
        def _snapshot_tts_runtime(self): return None
        def _tts_capacity_limit(self, _worker): return 1
        def _tts_worker_supports_completion(self, *_args): return False
        def _cancel_tts_soft_flush(self): pass
        def _build_tts_runtime_key(self): return "fixture-runtime"
        def _tts_output_is_current(self):
            gate.counts["send_speech_calls"] += 1
            gate.counts["realtime_audio_blocked"] += 1
            return False
        def _audio_chunk_header(self, _speech_id): return b"fixture-header"
        def _ensure_audio_frame_send_lock(self): return _FakeLock()
        async def _write_audio_frame(self, websocket, _header, audio): await websocket.send_bytes(audio)

    class _FakeLock:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return False

    host = Host()
    Host.send_speech = send_speech
    # Candidate's real worker startup calls its worker selector and queue path.
    host._tts_runtimes = []
    host._start_tts_thread()
    assert host.tts_thread.target is gate.provider_worker
    requests, responses = host.tts_request_queue, host.tts_response_queue
    # Run the candidate dummy worker separately with a synthetic queued request
    # to verify its offline path remains usable without invoking a provider.
    worker_thread = threading.Thread(target=dummy, args=(requests, responses, "", ""), daemon=True)
    worker_thread.start()
    assert responses.get(timeout=2) == ("__ready__", True)
    requests.put(("synthetic-speech", "Synthetic TTS request"))
    requests.put((SHUTDOWN, None))
    worker_thread.join(timeout=2)
    assert not worker_thread.is_alive()

    # Candidate handle_audio_data reaches candidate send_speech. Its existing
    # output-current guard is supplied by the fixture as an always-block seam.
    host._takeover_active = False
    host.use_tts = False
    host.websocket = _Socket()
    host.audio_resampler = type("Resampler", (), {"resample_chunk": lambda self, value: value})()
    host.websocket = _Socket()
    globals_for_turn = handle_audio.__globals__
    previous_numpy = globals_for_turn.get("np")
    globals_for_turn["np"] = _FakeNumpy
    try:
        import asyncio
        asyncio.run(host.handle_audio_data(b"synthetic-native-audio"))
    finally:
        if previous_numpy is None:
            globals_for_turn.pop("np", None)
        else:
            globals_for_turn["np"] = previous_numpy

    gate.counts["websocket_sink_calls"] = host.websocket.send_count
    assert gate.counts["provider_selection_attempted"] == 1
    assert gate.counts["provider_worker_dispatch_attempted"] == gate.counts["provider_worker_dispatch_blocked"] == 1
    assert gate.counts["normal_tts_request_attempted"] == gate.counts["normal_tts_request_blocked"] == 1
    assert gate.counts["send_speech_calls"] == gate.counts["realtime_audio_blocked"] == 1
    assert gate.counts["fake_provider_worker_calls"] == gate.counts["websocket_sink_calls"] == 0
    return gate.counts


def _child_probe():
    print(json.dumps({"phase": "restart", "counts": _one_probe()}, sort_keys=True))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--child-probe":
        _child_probe()
        return

    first = _one_probe()
    reloaded = _one_probe()  # Reparse candidate source and reinstall the fixture gate.
    child = subprocess.run(
        [sys.executable, "-I", "-S", str(Path(__file__).resolve()), "--child-probe"],
        check=True, capture_output=True, text=True, timeout=15,
    )
    restarted = json.loads(child.stdout.strip())
    assert restarted["counts"]["normal_tts_request_blocked"] == 1
    assert restarted["counts"]["realtime_audio_blocked"] == 1
    assert restarted["counts"]["provider_worker_dispatch_attempted"] == restarted["counts"]["provider_worker_dispatch_blocked"] == 1
    assert restarted["counts"]["fake_provider_worker_calls"] == 0
    assert restarted["counts"]["websocket_sink_calls"] == 0

    source_hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (RUNTIME, TURN, DUMMY)
    }
    evidence = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS_CANDIDATE_SELECTOR_AND_CALLBACK_OFFLINE_STUB",
        "candidate_revision": "1d814cf32fba8c02b5727d2890710e4e7b8ece24",
        "candidate_source_hashes": source_hashes,
        "installed_frozen_host_tested": False,
        "live_app_or_audio_started": False,
        "python_execution": "CPython 3.11 -I -S; import isolation only, not OS network/audio isolation",
        "os_network_isolation_proven": False,
        "os_audio_isolation_proven": False,
        "reload": {"counts": reloaded},
        "restart": restarted,
        "initial": {"counts": first},
        "scope": "Candidate _resolve_tts_worker_spec and _start_tts_thread select a counted fake provider worker; the fixture thread seam records an attempted dispatch and blocks before its body (provider calls remain zero). Candidate dummy_tts_worker is separately exercised with a synthetic request. Candidate TurnMixin.handle_audio_data reaches the actual TtsRuntimeMixin.send_speech method; the fixture supplies the always-false _tts_output_is_current call-site guard and a counting socket fake. This is not a full host boot, OS isolation, or packaged-host safety proof.",
    }
    target = Path(os.environ.get("NEKO_AUDIO_GATE_EVIDENCE", str(DEFAULT_EVIDENCE)))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(f"Evidence: {target}")


if __name__ == "__main__":
    main()
