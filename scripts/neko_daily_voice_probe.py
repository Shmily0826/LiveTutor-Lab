"""Bounded Study-picture -> native role voice, optional same-session follow-up, no room microphone."""
from __future__ import annotations
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import hashlib
import os
import re
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


class ObservedSurface(LearningSurface):
    def guide(self, command):
        record = {"wall": time.time(), "command": dict(command)}
        self.guide_attempts.append(record)
        try:
            result = super().guide(command)
            record["accepted"] = True
            return result
        except (LookupError, ValueError) as error:
            record.update(accepted=False, reason=str(error))
            raise


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
    if args.followup_wav and (not args.wav or args.manual_turn_probe or args.point_code):
        raise ValueError("same-session follow-up requires fixed WAV picture mode, no manual/point probe")
    if args.followup_wav and not (args.prepare_picture or args.verify_picture_state):
        raise ValueError("same-session follow-up requires isolated picture mode")
    for wav_path in (args.wav, args.followup_wav):
        if wav_path and not wav_path.is_file(): raise ValueError("fixed WAV missing; do not start host")
    store_path = (ROOT / 'benchmarks/raw' / args.store).resolve()
    if not store_path.is_relative_to((ROOT / 'benchmarks/raw').resolve()):
        raise ValueError('voice fixture store must stay under project raw directory')
    if args.prepare_picture and (not args.store.startswith('neko-daily-speech-acceptance-') or store_path.exists()):
        raise ValueError('picture preference preparation requires a new isolated speech-acceptance store')
    if args.verify_picture_state and not args.store.startswith('neko-daily-speech-acceptance-'):
        raise ValueError('picture constraint probe must use an isolated speech-acceptance store')
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with sockets.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("an existing host owns the ports; leave it running")
    report = {"events": [], "room_microphone": False, "input": "text inside actual audio session",
              "volume_changed": False, "started_at": datetime.now(timezone.utc).isoformat()}
    ledger_path = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
    report["before"] = json.loads(ledger_path.read_text())
    assert report["before"]["round"] == "bargein-autocheck-20261012"
    surface = ObservedSurface([path for path in DEFAULT_MATERIALS if path.is_file()], port=0)
    surface.guide_attempts = []
    import threading
    surface_thread = threading.Thread(target=surface.serve_forever, daemon=True); surface_thread.start()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "NEKO_REALTIME_WIRE_TRACE": "1", "NEKO_LEARNING_SURFACE_URL": f"http://127.0.0.1:{surface.server_port}",
           "NEKO_LEARNING_SURFACE_TOKEN": surface.token}
    if args.manual_turn_probe:
        if not args.wav: raise ValueError("manual support probe requires fixed WAV")
        env["NEKO_FREE_MANUAL_TURN_PROBE"] = "1"
        report["manual_support_probe"] = True
    if args.speech_gate:
        env['NEKO_STUDY_SPEECH_GATE'] = '1'
        env['NEKO_STUDY_SPEECH_GATE_TRACE'] = '1'
        report['study_speech_gate'] = 'opt-in exact free route; quiet + received ASR + host readiness, fixed owner'
    startup_log = args.output.with_suffix('.host.log')
    startup_handle = startup_log.open('wb')
    report['startup_log'] = str(startup_log)
    process = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8", str(ROOT / "scripts/neko_desktop_tutor_host.py"),
        "--source", "--voice", "--core-provider", "free", "--store", args.store,
        "--hold", "360", "--seconds", "100", "--api-budget", "30", "--egress-budget", "2000",
        "--allow-host", "www.lanlan.app:unlimited", "--allow-host", "www.lanlan.tech:0",
        "--budget-round", "bargein-autocheck-20261012"] + (["--study-vision"] if args.prepare_picture or args.verify_picture_state else []), cwd=ROOT, env=env,
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
        if args.prepare_picture:
            # A fresh isolated course, reusing an existing fixture. No new diagram
            # or quiz, and no alterations to the learner's normal daily course.
            from neko_native_avatar_toolchain import call
            image = ROOT / 'benchmarks/raw/evidence/diagram-input-sky-dark.png'
            if not image.is_file(): raise RuntimeError('existing picture fixture missing; no voice connection')
            report['prepared_picture_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
            report['prepared_course'] = 'daily-speech-constraints-20261014'
            for entry, fields in (
                ('study_session', {'action':'set_course','course_id':report['prepared_course']}),
                ('study_preferences', {'preferences':{'language':'zh-CN','length':'brief','proactive_quiz':False},'remember':True}),
            ):
                result = await asyncio.to_thread(call, entry, fields)
                if result.get('is_error') or not result.get('output',{}).get('ok'):
                    raise RuntimeError('fresh picture course setup refused; no voice connection')
            image_result = await asyncio.to_thread(client.call, 'study_submit_image', {
                'image_base64':base64.b64encode(image.read_bytes()).decode(),
                'text':'这张图作为本课材料，先简短确认主要天气请求路线，不出题。',
                'expected_course_id':report['prepared_course'],
            })
            report['picture_submission'] = image_result
            if image_result.get('error') or image_result.get('data',{}).get('degraded') or not image_result.get('data',{}).get('ok',True):
                raise RuntimeError('picture preparation failed; no voice connection')
        if args.prepare_picture or args.verify_picture_state:
            from neko_native_avatar_toolchain import call
            report['material_before_voice'] = await asyncio.to_thread(call, 'study_material', {})
            if not report['material_before_voice'].get('output',{}).get('picture_available'):
                raise RuntimeError('current Study picture unavailable; no voice connection')
            report['preferences_before_voice'] = await asyncio.to_thread(call, 'study_preferences', {})
            report['study_before_voice'] = await asyncio.to_thread(client.call, 'study_status')
        if args.point_code:
            from neko_native_avatar_toolchain import call
            from neko_role_point_browser import RolePointHandler
            code = await asyncio.to_thread(call, 'study_code', {'mode':'explore','query':'WeatherService fetchWeather in weather_service.dart: show the actual function declaration and request construction'})
            report['prepared_code'] = code
            output = code.get('output', {})
            publication = output.get('learning_surface') or {}
            if code.get('is_error') or not output.get('ok') or not publication.get('available'):
                raise RuntimeError('authorized code material not available; no voice connection')
            # Represents the learner selecting this returned snapshot, not a role action.
            surface.select(publication['material_id'])
            source_targets = surface.materials[publication['material_id']]['targets_for_pointing']
            declarations = [t for t in source_targets if t.get('source_line') == 13 and 'fetchWeather' in t.get('label', '')]
            if len(declarations) != 1:
                raise RuntimeError('current source locator metadata is missing or ambiguous; no voice connection')
            report['prepared_source_target'] = declarations[0]
            surface.RequestHandlerClass = RolePointHandler
            surface.role_point_done = threading.Event()
            surface.role_point_checks = None
            report['learner_selected_code'] = publication['material_id']
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
                    "--seconds", "195" if args.followup_wav else "75", "--out", str(args.output.with_suffix(".loopback.wav"))],
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                report["turns"] = []
                for input_wav in ([args.wav, args.followup_wav] if args.followup_wav else [args.wav]):
                    if failed.is_set(): break
                    frames_before = (report.get("native_final") or {}).get("trace", {}).get("binaryFrames", 0)
                    report["input_submitted_at"] = round(time.monotonic() - origin, 3)
                    report["input_wall"] = time.time()
                    ended.clear()
                    first_audio = None
                    save()
                    if input_wav:
                        with wave.open(str(input_wav)) as wav:
                            assert wav.getsampwidth() == 2
                            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
                            if wav.getnchannels() > 1: samples = samples.reshape(-1, wav.getnchannels()).mean(axis=1)
                            samples = soxr.resample(samples, wav.getframerate(), 48000).astype("<i2")
                        samples = np.concatenate((np.zeros(48000, dtype="<i2"), samples, np.zeros(144000, dtype="<i2")))
                        report["input_wav_sha256"] = hashlib.sha256(input_wav.read_bytes()).hexdigest()
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
                        min_observation = 55 if args.prepare_picture or args.verify_picture_state else 35
                        if ended.is_set() and time.time() - report["input_wall"] > min_observation and time.monotonic() - native_changed > 6 and not playback.get("active"):
                            break
                        await asyncio.sleep(0.25)
                    else: report["turn_timeout"] = True
                    await asyncio.sleep(3)
                    report["first_socket_audio_at"] = first_audio
                    report["reply"] = "".join(e.get("text", "") for e in report["events"]
                        if e.get("type") == "gemini_response" and e["at"] >= report["input_submitted_at"])
                    report["native_reply"] = "".join(e.get("text", "") for e in (report.get("native_final", {}).get("trace") or {}).get("events", [])
                        if e.get("type") == "gemini_response" and e["wall"] >= report["input_wall"])
                    turn_fields = ("input_submitted_at", "input_wall", "input_wav_sha256", "fixed_speech_end_offset",
                                   "input_audio_start_wall", "input_end_at", "input_end_wall", "fixed_speech_end_wall",
                                   "first_socket_audio_at", "reply", "native_reply", "turn_timeout")
                    turn = {key: report[key] for key in turn_fields if key in report}
                    turn["observation_end_wall"] = time.time()
                    turn["native_pcm_frames"] = (report.get("native_final") or {}).get("trace", {}).get("binaryFrames", 0) - frames_before
                    turn_events = [event for event in (report.get("native_final") or {}).get("trace", {}).get("events", [])
                                   if event.get("wall", 0) >= turn["input_wall"]]
                    turn["native_first_pcm_wall"] = next((event["wall"] for event in turn_events if event.get("type") == "audio_frame"), None)
                    turn["playback_first_scheduled_wall"] = next((event["wall"] for event in turn_events
                        if event.get("type") == "native_speech_playback_state" and event.get("active")), None)
                    report["turns"].append(turn)
                    save()
                    if failed.is_set() or report.get("turn_timeout"): break
                if args.followup_wav:
                    report["native_reply"] = "\n".join(turn.get("native_reply", "") for turn in report["turns"])
                if args.point_code:
                    report['role_point_command'] = surface.command
                    if surface.command:
                        run = await asyncio.to_thread(subprocess.run, ['node',r'D:\AI\tools\web-inspector\cli.mjs',env['NEKO_LEARNING_SURFACE_URL']+'/', '--desktop','--screenshot','--json'],capture_output=True,text=True,encoding='utf-8',timeout=25)
                        report['role_point_inspector'] = json.loads(run.stdout)
                        report['role_point_browser_checks'] = surface.role_point_checks
                    else:
                        report['role_point_unverified'] = 'role produced no pointer; fixture submits no commands'
                await observer.screenshot(args.output.with_suffix(".native.png"))
                if args.prepare_picture or args.verify_picture_state:
                    from neko_native_avatar_toolchain import call
                    report['preferences_after_voice'] = await asyncio.to_thread(call, 'study_preferences', {})
                    report['study_after_voice'] = await asyncio.to_thread(client.call, 'study_status')
                    report['material_after_voice'] = await asyncio.to_thread(call, 'study_material', {})
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
                out, err = await asyncio.to_thread(meter.communicate, timeout=205 if args.followup_wav else 85)
                report["loopback"] = json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-400:]}
            except Exception as exc:
                meter.terminate(); report["loopback_error"] = type(exc).__name__
        if shell is not None:
            avatar.shutdown(shell)
        await asyncio.to_thread(stop_owned_host, process)
        startup_handle.close()
        surface.shutdown(); surface.server_close(); surface_thread.join(timeout=3)
        report["after"] = json.loads(ledger_path.read_text())
        report['surface_guide_attempts'] = surface.guide_attempts
        if log_path.exists():
            with log_path.open("rb") as handle:
                handle.seek(log_start)
                fresh_log = handle.read().decode("utf-8", errors="replace")
            # These bounded diagnostic lines contain event timestamps, not credentials.
            report["timing_log"] = [line for line in fresh_log.splitlines() if any(mark in line for mark in (
                "voice user_transcript", "TRIGGER entry='__llm_tool__study_", "首个 audio.delta", "/api/llm-tools/callback/study_companion/", "native-timing", "study voice admission", "study voice identical"))]
            wire_records = []
            for line in fresh_log.splitlines():
                if "[wire-trace] " in line:
                    try: wire_records.append(json.loads(line.split("[wire-trace] ", 1)[1]))
                    except ValueError: pass
            report["wire_trace"] = wire_records
        report["proof"] = "separate actual provider/native/loopback; fixed input proves this device route, human listening remains unverified"
        if (args.prepare_picture or args.verify_picture_state) and not args.followup_wav:
            speech_end = report.get('fixed_speech_end_wall')
            audio = [e['t'] for e in report.get('wire_trace',[]) if e.get('dir') == 'recv' and e.get('type') == 'response.audio.delta']
            calls = [line for line in report.get('timing_log',[]) if "TRIGGER entry='__llm_tool__study_explain'" in line]
            before_p = report.get('preferences_before_voice',{}).get('output',{}).get('preferences',{})
            after_p = report.get('preferences_after_voice',{}).get('output',{}).get('preferences',{})
            before_m = report.get('material_before_voice',{}).get('output',{})
            after_m = report.get('material_after_voice',{}).get('output',{})
            wording = report.get('native_reply','').strip()
            checks = {
                'one_teaching_tool_execution':len(calls)==1,
                'no_early_provider_audio':bool(speech_end) and bool(audio) and min(audio)>=speech_end,
                'same_current_picture':bool(before_m.get('material_id')) and before_m.get('material_id')==after_m.get('material_id'),
                'temporary_english_does_not_change_preferences':before_p==after_p and after_p.get('language')=='zh-CN',
                'native_pcm_frames':report.get('native_final',{}).get('trace',{}).get('binaryFrames',0)>0,
                'device_loopback_loud':report.get('loopback',{}).get('loud_chunks',0)>0,
                'english_reply_shape':bool(re.search('[A-Za-z]',wording)) and not re.search('[\u4e00-\u9fff]',wording),
                'two_sentence_shape':len(re.findall(r'[.!?](?:\s|$)',wording))==2,
                'session_normal':not report.get('failure') and not report.get('turn_timeout'),
            }
            report['picture_constraint_acceptance']={'checks':checks,
                'result':'CANDIDATE_CHECKS_PASS_REQUIRES_SEMANTIC_REVIEW' if all(checks.values()) else 'FAIL_OR_PARTIAL',
                'scope':'automatic timing/shape/device checks only; final question/no-quiz/database/diagram facts must be reviewed, human pending'}
        if args.followup_wav:
            turns = report.get('turns', [])
            for turn in turns:
                audio = [event['t'] for event in report.get('wire_trace', [])
                         if event.get('dir') == 'recv' and event.get('type') == 'response.audio.delta'
                         and turn['input_wall'] <= event.get('t', 0) <= turn['observation_end_wall']]
                turn['no_early_provider_audio'] = bool(audio) and bool(turn.get('fixed_speech_end_wall')) and min(audio) >= turn['fixed_speech_end_wall']
                turn['provider_first_audio_wall'] = min(audio) if audio else None
            before_p = report.get('preferences_before_voice', {}).get('output', {}).get('preferences', {})
            after_p = report.get('preferences_after_voice', {}).get('output', {}).get('preferences', {})
            before_m = report.get('material_before_voice', {}).get('output', {})
            after_m = report.get('material_after_voice', {}).get('output', {})
            checks = {
                'two_completed_turns': len(turns) == 2 and not any(turn.get('turn_timeout') for turn in turns),
                'no_early_provider_audio_each_turn': len(turns) == 2 and all(turn['no_early_provider_audio'] for turn in turns),
                'native_pcm_each_turn': len(turns) == 2 and all(turn['native_pcm_frames'] > 0 for turn in turns),
                'preferences_still_chinese': before_p == after_p and after_p.get('language') == 'zh-CN',
                'same_current_picture': bool(before_m.get('material_id')) and before_m.get('material_id') == after_m.get('material_id'),
                'session_normal': not report.get('failure') and not report.get('turn_timeout'),
            }
            report['continuity_acceptance'] = {'checks': checks,
                'result': 'CANDIDATE_CHECKS_PASS_REQUIRES_SEMANTIC_REVIEW' if all(checks.values()) else 'FAIL_OR_PARTIAL',
                'scope': 'same bounded audio session, per-turn provider timing and native PCM; language/facts and per-turn loopback need review; human pending'}
        if args.point_code:
            browser = report.get('role_point_browser_checks') or []
            inspector = (report.get('role_point_inspector') or {}).get('results') or []
            trace = (report.get('native_final') or {}).get('trace') or {}
            checks = {
                'actual_role_command': bool(report.get('role_point_command')),
                'actual_source_target_and_visible_pointer': len(browser) >= 3 and all(c.get('pass') for c in browser),
                'browser_without_page_errors': bool(inspector) and all(not r.get('pageErrors') for r in inspector),
                'native_spoken_confirmation_text': bool(report.get('native_reply', '').strip()),
                'device_loopback_loud': (report.get('loopback') or {}).get('loud_chunks', 0) > 0,
                'session_finished_normally': not report.get('failure') and not report.get('turn_timeout'),
            }
            report['acceptance'] = {'checks': checks, 'result': 'PASS_FIXED_INPUT_DEVICE_ROUTE' if all(checks.values()) else 'FAIL_OR_PARTIAL',
                                    'human_experience': 'PENDING', 'complete_utterance_and_brief_ack': 'requires trace review; not inferred from audio presence'}
            if args.speech_gate:
                speech_end = report.get('fixed_speech_end_wall')
                accepted = [a for a in surface.guide_attempts if a.get('accepted')]
                audio = [e['t'] for e in report.get('wire_trace', []) if e.get('dir') == 'recv'
                         and e.get('type') == 'response.audio.delta' and e.get('t', 0) >= report.get('input_wall', 0)]
                wording = report.get('native_reply', '').strip()
                gate_checks = {
                    'one_pointer_action': len(accepted) == 1,
                    'pointer_after_complete_fixed_input': bool(speech_end) and bool(accepted) and all(a['wall'] >= speech_end for a in accepted),
                    'no_early_provider_audio': bool(speech_end) and bool(audio) and min(audio) >= speech_end,
                    'brief_confirmation_without_cursor_claim': bool(wording) and len(wording) <= 70 and '光标' not in wording and 'cursor' not in wording.lower(),
                }
                report['speech_gate_acceptance'] = {'checks': gate_checks,
                    'result': 'PASS_THIS_SINGLE_UTTERANCE' if all(gate_checks.values()) and all(checks.values()) else 'FAIL_OR_PARTIAL',
                    'scope': 'this fixed source pointing utterance only; paid teaching constraints and human listening remain separate'}
        save()
        print(json.dumps({"report": str(args.output), "failure": report.get("failure"), "reply": report.get("reply"),
                          "audio_bytes": report.get("socket_audio_bytes"), "loopback_loud": (report.get("loopback") or {}).get("loud_chunks"),
                          "spent": report["after"]["spent"], "acceptance": report.get('acceptance')}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="neko-daily-acceptance-20261014")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wav", type=Path, help="fixed PCM WAV; never opens a room microphone")
    parser.add_argument("--followup-wav", type=Path, help="one fixed WAV follow-up in the same bounded audio session; isolated picture mode only")
    parser.add_argument("--manual-turn-probe", action="store_true", help="one opt-in explicit-end support scene; no production VAD change")
    parser.add_argument("--point-code", action="store_true", help="prepare authorized source selected by learner; require actual role to point")
    parser.add_argument("--speech-gate", action="store_true", help="one opt-in Study execution-admission scene; never changes onset/cancel")
    parser.add_argument("--prepare-picture", action="store_true", help="fresh isolated course with an existing image, Chinese preference and no proactive quiz")
    parser.add_argument("--verify-picture-state", action="store_true", help="reuse the existing isolated picture course, read before/after; no extra image model preparation")
    asyncio.run(main(parser.parse_args()))
