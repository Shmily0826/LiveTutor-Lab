"""One no-config AST regression: real playback receipt -> bounded native onset."""
import ast
import asyncio
from pathlib import Path
from types import MethodType, SimpleNamespace
import unittest
import tempfile

import neko_native_barge_in_patch as native_patch
import neko_voice_host_patch as patcher

HOST = Path(__file__).resolve().parents[1] / "benchmarks/raw/neko-product-host"


def load_method(relative, name, clock):
    tree = ast.parse((HOST / relative).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == name)
    node.decorator_list = []
    node.returns = None
    for arg in node.args.args + node.args.kwonlyargs:
        arg.annotation = None
    node.body = [n for n in node.body if not (isinstance(n, ast.Import)
                 and any(a.name == "time" for a in n.names))]
    ns = {"asyncio": asyncio, "time": clock, "logger": SimpleNamespace(info=lambda *_: None)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), relative, "exec"), ns)
    return ns[name]


class OverlapRegression(unittest.TestCase):
    def test_playback_feedback_replay_migrations_are_idempotent(self):
        relative = "static/app/app-audio-playback.js"
        anchor, legacy = native_patch.UPGRADES[relative][-1]
        final = legacy
        for before, after in native_patch.ELIGIBILITY_UPGRADES[relative]:
            final = final.replace(before, after)
        latest = native_patch.normalize_playback_feedback((HOST / relative).read_text(encoding="utf-8"))
        self.assertEqual(latest.count(final), 1)
        sender = legacy.removeprefix("        window.NekoSpeechPlaybackState = state;\n").removesuffix("        try {")
        variants = {
            "original_anchor": latest.replace(final, anchor),
            "legacy_receipt": latest.replace(final, legacy),
            "duplicate_receipt": latest.replace(final, final + sender.removeprefix("        try {") + "        try {"),
            "current": latest,
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / relative
            target.parent.mkdir(parents=True)
            for kind, source in variants.items():
                with self.subTest(kind=kind):
                    target.write_text(source, encoding="utf-8")
                    if kind == "duplicate_receipt":
                        self.assertNotEqual(patcher.state(target), "patched")
                    patcher.apply_to(target)
                    self.assertEqual(target.read_text(encoding="utf-8"), latest)
                    self.assertEqual(patcher.apply_to(target), "already patched")

    def test_cross_end_and_rejection_fences(self):
        async def scenario(kind):
            clock = SimpleNamespace(now=100.)
            clock.monotonic = lambda: clock.now
            clock.time = lambda: 1791861910. + clock.now - 100.
            client = SimpleNamespace(_is_free_proxy=True, _is_gemini=False, _has_server_vad=False,
                _connection_generation=1, _native_output_connection_token="native_connection_A",
                _LOCAL_TALKING_WINDOW_SECONDS=2., _LOCAL_BARGE_IN_SECONDS=.5,
                _LOCAL_BARGE_IN_GAP_SECONDS=.15, _ai_recent_activity_time=1791861892.9,
                _native_barge_in_generation="input_A", _native_barge_in_pending=False,
                _prepare_native_barge_in_replay=lambda: True,
                _trace_local_playback_owner=lambda: None, _note_barge_in_meter=lambda *_: None)
            declines, recovered = [], []
            client._note_local_onset_declined = declines.append
            manager = SimpleNamespace(session=client, is_active=True, _asr_route_mode="native",
                _voice_lease_owner="core", _takeover_active=False, current_speech_id="speech_A",
                websocket=object(), generation="input_A", _voice_input_accepts_pcm=lambda: True,
                _game_speech_correlation_for=lambda _: "")
            manager._capture_voice_session_activation_generation = lambda: manager.generation
            client.get_native_barge_in_generation = manager._capture_voice_session_activation_generation
            for name in ("note_native_speech_playback_state", "_begin_native_barge_in_handoff"):
                setattr(manager, name, MethodType(load_method("main_logic/core/asr_runtime.py", name, clock), manager))
            manager.read_current_speech_id = MethodType(load_method("main_logic/core/turn.py", "read_current_speech_id", clock), manager)

            async def recover(*args): recovered.append(args)
            manager._recover_native_barge_in = recover
            client.on_native_barge_in = lambda: manager._begin_native_barge_in_handoff(client)
            for name in ("_handle_local_speech_onset", "_remember_native_barge_in_overlap"):
                if name == "_remember_native_barge_in_overlap" and kind == "baseline":
                    continue
                setattr(client, name, MethodType(load_method("main_logic/omni_realtime_client/_transport.py", name, clock), client))
            tree = ast.parse((HOST / "main_logic/omni_realtime_client/_transport.py").read_text(encoding="utf-8"))
            stream = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "stream_audio")
            gate = next(n for n in ast.walk(stream) if isinstance(n, ast.If)
                        and "_speech_started_total" in ast.unparse(n.test) and "_speaking_now" in ast.unparse(n))
            wrapper = ast.parse("async def step(self, speech_active, audio_timeline_at): pass").body[0]
            wrapper.body = [gate]
            ns = dict(_native_barge_in_replay=False, _rnnoise_vad_live=False,
                      raw_loud=False, raw_samples=(), audio_processor=None)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), "sustain", "exec"), ns)

            def feedback(active, token="native_connection_A", socket=None):
                message = {"active": active, "sdk_speech_correlation_id": token}
                if kind != "legacy": message["audible"] = active and kind != "queued"
                manager.note_native_speech_playback_state(message, socket or manager.websocket)

            if kind != "missing":
                feedback(kind != "post_end", token="native_connection_X" if kind == "token" else "native_connection_A",
                         socket=object() if kind == "socket" else None)
            if kind == "stale": clock.now = 103.
            start = clock.now
            for i in range(18):
                clock.now = start + i * .032
                if i == 8:
                    if kind == "generation": manager.generation = "input_B"
                    if kind == "connection": client._native_output_connection_token = "native_connection_B"
                    if kind == "output_socket": manager.websocket = object()
                    if kind == "expired": clock.now = start + 1.
                    if kind == "gap":
                        await ns["step"](client, False, start + .5)
                    if kind not in ("missing", "stale", "token", "socket"):
                        feedback(False)
                if kind == "expired" and i >= 8: clock.now = start + 1. + i * .032
                at = start + i * .032 + (.5 if kind == "gap" and i >= 8 else 0.)
                await ns["step"](client, kind != "noise" and not (kind == "short" and i >= 8), at)
            await asyncio.sleep(0)
            self.assertFalse(hasattr(manager, "speech_id"), "Must exercise the real accessor")
            if kind in ("cross_end", "baseline"):
                self.assertEqual(len(recovered), 1, "same speech crossing playback end must hand off")
                self.assertEqual(recovered[0][2:4], (1, "native_connection_A"))
            else:
                self.assertEqual(recovered, [], kind)
            if kind in ("missing", "stale", "token", "socket", "post_end"):
                reason = " ".join(declines)
                self.assertIn("feedback=", reason)
                if kind in ("token", "socket"): self.assertIn("feedback_rejected=" + ("websocket" if kind == "socket" else "token"), reason)

        # Before deploying the new patch, only the confirmed crossing case is run.
        source = (HOST / "main_logic/omni_realtime_client/_transport.py").read_text(encoding="utf-8")
        kinds = ("baseline",) if "def _remember_native_barge_in_overlap" not in source else (
            "cross_end", "post_end", "missing", "stale", "token", "socket", "generation",
            "connection", "output_socket", "gap", "expired", "noise", "short", "queued", "legacy")
        for kind in kinds:
            with self.subTest(kind=kind): asyncio.run(scenario(kind))


if __name__ == "__main__":
    unittest.main()
