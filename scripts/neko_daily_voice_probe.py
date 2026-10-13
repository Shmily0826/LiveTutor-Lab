"""One bounded Study-picture -> native role voice attempt, no room microphone."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import subprocess
import socket as sockets
import time
import urllib.parse
import wave
import websockets
import numpy as np
import soxr
import psutil
from neko_learning_surface import LearningSurface, DEFAULT_MATERIALS
from neko_lab_client import LabClient
import neko_desktop_tutor_host as host
import neko_native_shell as avatar
from neko_native_telemetry import NativeTelemetry
from neko_tutor_start import plugin_server_ready

ROOT = Path(__file__).resolve().parents[1]


def stop_owned_host(process):
    if process.poll() is not None:
        return
    parent = psutil.Process(process.pid)
    children = parent.children(recursive=True)
    owned_pids = {process.pid, *(child.pid for child in children)}
    for child in reversed(children):
        try: child.terminate()
        except psutil.NoSuchProcess: pass
    process.terminate()
    psutil.wait_procs(children, timeout=5)
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
    pid_file = ROOT / "benchmarks/raw/neko-desktop-host.pid"
    if pid_file.is_file() and pid_file.read_text().strip().isdigit() and int(pid_file.read_text()) in owned_pids:
        pid_file.unlink()


async def main(args):
    if args.output.exists(): raise RuntimeError("do not overwrite or repeat a voice attempt")
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with sockets.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("an existing host owns the ports; leave it running")
    report = {"events": [], "room_microphone": False, "input": "text inside actual audio session",
              "volume_changed": False, "started_at": datetime.now(timezone.utc).isoformat()}
    ledger_path = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
    report["before"] = json.loads(ledger_path.read_text())
    assert report["before"]["round"] == "bargein-autocheck-20261012"
    surface = LearningSurface([path for path in DEFAULT_MATERIALS if path.is_file()], port=0)
    import threading
    surface_thread = threading.Thread(target=surface.serve_forever, daemon=True); surface_thread.start()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "NEKO_REALTIME_WIRE_TRACE": "1", "NEKO_LEARNING_SURFACE_URL": f"http://127.0.0.1:{surface.server_port}",
           "NEKO_LEARNING_SURFACE_TOKEN": surface.token}
    if args.manual_turn_probe:
        if not args.wav: raise ValueError("manual support probe requires fixed WAV")
        env["NEKO_FREE_MANUAL_TURN_PROBE"] = "1"
        report["manual_support_probe"] = True
    startup_log = args.output.with_suffix('.host.log')
    startup_handle = startup_log.open('wb')
    report['startup_log'] = str(startup_log)
    process = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8", str(ROOT / "scripts/neko_desktop_tutor_host.py"),
        "--source", "--voice", "--core-provider", "free", "--store", args.store,
        "--hold", "360", "--seconds", "100", "--api-budget", "30", "--egress-budget", "2000",
        "--allow-host", "www.lanlan.app:unlimited", "--allow-host", "www.lanlan.tech:0",
        "--budget-round", "bargein-autocheck-20261012"], cwd=ROOT, env=env,
        stdout=startup_handle, stderr=subprocess.STDOUT)
    shell, meter, observer, observer_task = None, None, None, None
    log_path = ROOT / "benchmarks/raw/neko-desktop-host.log"
    log_start = log_path.stat().st_size if log_path.exists() else 0
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        client = LabClient()
        ready, reason = await asyncio.to_thread(plugin_server_ready, 100, process)
        if not ready: raise RuntimeError("host not ready: " + reason)
        print("隔离 Study 宿主就绪；开始一场有超时的角色语音会话。", flush=True)
        report["host_ready"] = True
        save()
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:48911/api/characters/current_catgirl", timeout=10) as response:
            character = json.load(response)["current_catgirl"]
        silence = ROOT / "benchmarks/raw/voice-input/daily-silent-input-20261014.wav"
        if not silence.exists():
            with wave.open(str(silence), "wb") as wav:
                wav.setparams((1, 2, 48000, 0, "NONE", "not compressed")); wav.writeframes(b"\x00\x00" * 48000 * 180)
        report["surface_url"] = env["NEKO_LEARNING_SURFACE_URL"]
        async with websockets.connect("ws://127.0.0.1:48911/ws/" + urllib.parse.quote(character),
                                      proxy=None, max_size=5*1024*1024) as socket:
            started, ended, failed = asyncio.Event(), asyncio.Event(), asyncio.Event()
            first_audio = None
            origin = time.monotonic()
            report["origin_wall"] = time.time()
            async def receive():
                nonlocal first_audio
                async for frame in socket:
                    at = round(time.monotonic() - origin, 3)
                    if isinstance(frame, bytes):
                        report["socket_audio_bytes"] = report.get("socket_audio_bytes", 0) + len(frame)
                        if first_audio is None: first_audio = at
                        continue
                    event = json.loads(frame)
                    if event.get("type") != "audio_chunk": report["events"].append({"at": at, **event})
                    if event.get("type") == "session_started": started.set()
                    if event.get("type") in ("session_failed", "session_ended_by_server"):
                        failed.set(); started.set(); ended.set()
                    if event.get("type") == "system" and event.get("data") == "turn end": ended.set()
            receiver = asyncio.create_task(receive())
            async def send(value): await socket.send(json.dumps(value, ensure_ascii=False))
            async def heartbeat():
                while True:
                    await asyncio.sleep(5)
                    await send({"action": "ping"})
            pinger = asyncio.create_task(heartbeat())
            try:
                await send({"action": "start_session", "input_type": "audio", "language": "zh-CN",
                            "new_session": False, "independent_asr_enabled": False})
                await asyncio.wait_for(started.wait(), 45)
                if failed.is_set(): raise RuntimeError("voice provider/session refused; no retries")
                with sockets.socket() as debug_port_probe:
                    debug_port_probe.bind(("127.0.0.1", 0))
                    debug_port = debug_port_probe.getsockname()[1]
                shell = await asyncio.to_thread(avatar.launch, ROOT / "benchmarks/raw" / args.store, 100,
                                                "compact", debug_port, str(silence))
                report["native"] = {"pid": shell["pid"], "windows": len(shell.get("windows", [])), "fake_silent_input": True}
                await asyncio.sleep(4)
                observer = await NativeTelemetry.attach(debug_port)
                report["native_initial"] = await observer.snapshot()
                native_changed = time.monotonic()
                async def observe_native():
                    nonlocal native_changed
                    count = 0
                    while True:
                        snapshot = await observer.snapshot()
                        report["native_final"] = snapshot
                        events = (snapshot.get("trace") or {}).get("events", [])
                        if len(events) != count:
                            count = len(events); native_changed = time.monotonic()
                        if any(e.get("type") == "system" and e.get("data") == "turn end" and
                               e["wall"] >= report.get("input_wall", float("inf")) for e in events):
                            ended.set()
                        await asyncio.sleep(0.2)
                observer_task = asyncio.create_task(observe_native())
                meter = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8", str(ROOT / "scripts/neko_loopback_meter.py"),
                    "--seconds", "75", "--out", str(args.output.with_suffix(".loopback.wav"))],
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                report["input_submitted_at"] = round(time.monotonic() - origin, 3)
                report["input_wall"] = time.time()
                ended.clear()
                first_audio = None
                save()
                if args.wav:
                    with wave.open(str(args.wav)) as wav:
                        assert wav.getsampwidth() == 2
                        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
                        if wav.getnchannels() > 1: samples = samples.reshape(-1, wav.getnchannels()).mean(axis=1)
                        samples = soxr.resample(samples, wav.getframerate(), 48000).astype("<i2")
                    samples = np.concatenate((np.zeros(48000, dtype="<i2"), samples, np.zeros(144000, dtype="<i2")))
                    report["input_wav_sha256"] = hashlib.sha256(args.wav.read_bytes()).hexdigest()
                    speech_samples = np.flatnonzero(np.abs(samples.astype(np.int32)) > 300)
                    report["fixed_speech_end_offset"] = float(speech_samples[-1] / 48000) if speech_samples.size else None
                    if args.manual_turn_probe and speech_samples.size:
                        samples = samples[:int(speech_samples[-1]) + 57600]
                    report["input"] = "fixed WAV through actual RNNoise input; no live microphone"
                    began = time.monotonic()
                    report["input_audio_start_wall"] = time.time()
                    for offset in range(0, len(samples), 480):
                        await send({"action": "stream_data", "input_type": "audio", "data": samples[offset:offset+480].tolist()})
                        await asyncio.sleep(max(0, began + (offset+480)/48000 - time.monotonic()))
                    report["input_end_at"] = round(time.monotonic() - origin, 3)
                    report["input_end_wall"] = time.time()
                    report["fixed_speech_end_wall"] = report["input_audio_start_wall"] + report["fixed_speech_end_offset"] if speech_samples.size else None
                    if args.manual_turn_probe:
                        report["manual_end_sent_wall"] = time.time()
                        await send({"action": "end_audio_turn", "request_id": "manual-support-20261014-1"})
                else:
                    await send({"action": "stream_data", "input_type": "text",
                        "data": "请先调用 study_material 检查我刚交给 Study 的图片，再调用 study_explain，用中文两句话讲天气请求路线。不要用你自己的直接看图路线，不出题。",
                        "request_id": "daily-picture-voice-20261014"})
                deadline = time.monotonic() + 75
                while time.monotonic() < deadline:
                    if observer_task.done():
                        observer_task.result()
                    if failed.is_set(): break
                    # Observe delayed fragments too; a first turn end may be premature.
                    playback = (report.get("native_final") or {}).get("playback") or {}
                    if ended.is_set() and time.time() - report["input_wall"] > 35 and time.monotonic() - native_changed > 4 and not playback.get("active"):
                        break
                    await asyncio.sleep(0.25)
                else: report["turn_timeout"] = True
                await asyncio.sleep(3)
                report["first_socket_audio_at"] = first_audio
                report["reply"] = "".join(e.get("text", "") for e in report["events"]
                    if e.get("type") == "gemini_response" and e["at"] >= report["input_submitted_at"])
                report["native_reply"] = "".join(e.get("text", "") for e in (report.get("native_final", {}).get("trace") or {}).get("events", [])
                    if e.get("type") == "gemini_response" and e["wall"] >= report["input_wall"])
                await observer.screenshot(args.output.with_suffix(".native.png"))
                save()
                if failed.is_set(): raise RuntimeError("voice session ended abnormally")
                await send({"action": "end_session", "reason": "bounded_daily_voice_probe"})
            finally:
                pinger.cancel(); await asyncio.gather(pinger, return_exceptions=True)
                receiver.cancel(); await asyncio.gather(receiver, return_exceptions=True)
    except Exception as exc:
        report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if observer_task is not None:
            observer_task.cancel(); await asyncio.gather(observer_task, return_exceptions=True)
        if observer is not None:
            try: await observer.close()
            except Exception as exc: report["telemetry_cleanup_error"] = type(exc).__name__
        if meter is not None:
            try:
                out, err = await asyncio.to_thread(meter.communicate, timeout=85)
                report["loopback"] = json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-400:]}
            except Exception as exc:
                meter.terminate(); report["loopback_error"] = type(exc).__name__
        if shell is not None:
            avatar.shutdown(shell)
        await asyncio.to_thread(stop_owned_host, process)
        startup_handle.close()
        surface.shutdown(); surface.server_close(); surface_thread.join(timeout=3)
        report["after"] = json.loads(ledger_path.read_text())
        if log_path.exists():
            with log_path.open("rb") as handle:
                handle.seek(log_start)
                fresh_log = handle.read().decode("utf-8", errors="replace")
            # These bounded diagnostic lines contain event timestamps, not credentials.
            report["timing_log"] = [line for line in fresh_log.splitlines() if any(mark in line for mark in (
                "voice user_transcript", "TRIGGER entry='__llm_tool__study_", "首个 audio.delta", "/api/llm-tools/callback/study_companion/", "native-timing"))]
            wire_records = []
            for line in fresh_log.splitlines():
                if "[wire-trace] " in line:
                    try: wire_records.append(json.loads(line.split("[wire-trace] ", 1)[1]))
                    except ValueError: pass
            report["wire_trace"] = wire_records
        report["proof"] = "separate actual provider/native/loopback; fixed input proves this device route, human listening remains unverified"
        save()
        print(json.dumps({"report": str(args.output), "failure": report.get("failure"), "reply": report.get("reply"),
                          "audio_bytes": report.get("socket_audio_bytes"), "loopback_loud": (report.get("loopback") or {}).get("loud_chunks"),
                          "spent": report["after"]["spent"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="neko-daily-acceptance-20261014")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wav", type=Path, help="fixed PCM WAV; never opens a room microphone")
    parser.add_argument("--manual-turn-probe", action="store_true", help="one opt-in explicit-end support scene; no production VAD change")
    asyncio.run(main(parser.parse_args()))
