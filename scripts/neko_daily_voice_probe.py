"""Bounded Study-picture -> native role voice, optional same-session follow-up, no room microphone."""
from __future__ import annotations
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import hashlib
import math
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
from neko_native_telemetry import NativeTelemetry, NativeTraceHistory
from neko_tutor_start import plugin_server_ready, cleanup_resources, process_creation_time, CoreProviderOverride

ROOT = Path(__file__).resolve().parents[1]


def native_response_progress(snapshot, previous=None):
    """Response activity, excluding periodic heartbeat/playback receipts."""
    trace = snapshot.get('trace') or {}
    prior_frames, prior_wall = previous or (0, 0.0)
    walls = [event['wall'] for event in trace.get('events', [])
             if event.get('type') not in ('pong', 'native_speech_playback_state', 'speech_playback_state')
             and isinstance(event.get('wall'), (int, float))]
    # The bounded trace can evict old response events as heartbeats arrive.
    return (max(prior_frames, trace.get('binaryFrames', 0)), max([prior_wall, *walls]))


async def checked_native_snapshot(observer, history, task):
    def check_task():
        if task is not None and task.done():
            if task.cancelled():raise RuntimeError('Native observer cancelled before evidence freeze')
            task.result()
            raise RuntimeError('Native observer stopped before evidence freeze')
    check_task()
    snapshot=history.capture(await observer.snapshot())
    check_task()
    return snapshot


def teaching_defaults_unchanged(report):
    before = report.get('preferences_before_voice', {}).get('output', {})
    after = report.get('preferences_after_voice', {}).get('output', {})
    before_language = report.get('study_before_voice', {}).get('data', {}).get('config', {}).get('language')
    after_language = report.get('study_after_voice', {}).get('data', {}).get('config', {}).get('language')
    return (before.get('ok') is True and after.get('ok') is True
            and isinstance(before.get('preferences'), dict) and isinstance(after.get('preferences'), dict)
            and before.get('preferences') == after.get('preferences')
            and bool(before_language) and before_language == after_language)


def grade_quiz_prepared(result):
    output = result.get('output') or {}
    return (result.get('is_error') is False and output.get('tool') == 'study_quiz'
            and output.get('ok') is not False and output.get('degraded') is False
            and all(isinstance(output.get(key), str) and output[key].strip()
                    for key in ('question', 'question_id', 'attempt_id')))


def grade_baseline_matches(snapshot, pin, *, correction=False):
    if not isinstance(snapshot, dict) or not isinstance(pin, dict):
        return False
    question = snapshot.get('question') or {}
    held = {**{key:snapshot.get(key) for key in ('course_id','session_id')},
        **{key:question.get(key) for key in ('question_id','attempt_id','attempt_evaluated')}}
    return (snapshot.get('ok') is True and held == pin
            and pin.get('attempt_evaluated') is correction
            and (not correction or (snapshot.get('last_answer_evaluation') or {}).get('verdict') in ('wrong','partial')))


def teaching_capture_seconds(paths):
    duration = 0.0
    for path in paths:
        with wave.open(str(path)) as wav:
            duration += wav.getnframes() / wav.getframerate()
    if duration > 120:
        raise ValueError('three fixed teaching inputs must total at most 120 seconds')
    # Each input gets 4s padding, 75s response deadline, 3s tail and a bounded
    # SQLite read; include all three, plus capture/scheduling headroom.
    return math.ceil(duration + 3*(4+75+3+5) + 20)


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


def material_retirement_observed(replacement, snapshot):
    """A replaced first answer is deliberately retired, not a completed reply.

    This lets the next *fresh* fixed user input follow a confirmed cancellation
    instead of waiting 55s for text/turn-end from the intentionally retired
    answer. Never accept SDK submission alone or a different token's stop.
    """
    if not replacement or not replacement.get('submission_completed_wall'):
        return False
    old = replacement.get('old_native_token')
    if not old or not (replacement.get('before') or {}).get('playback', {}).get('active'):
        return False
    events = (snapshot.get('trace') or {}).get('events', [])
    cancel = any(event.get('type') == 'game_route_speech_cancel' and event.get('correlation_id') == old for event in events)
    stopped = any(event.get('type') == 'speech_playback_state' and event.get('reason') == 'native_connection_cancel'
                  and event.get('correlationId') == old and event.get('active') is False for event in events)
    return bool(cancel and stopped and not (snapshot.get('playback') or {}).get('active'))


async def main(args):
    output_only = getattr(args, 'output_only', False)
    grade_current = getattr(args, 'grade_current', False)
    grade_chain = getattr(args, 'grade_chain', False)
    grade_enabled = grade_current or grade_chain
    grade_correction = getattr(args, 'grade_correction', False)
    prepare_grade_quiz = getattr(args, 'prepare_grade_quiz', False)
    if output_only:
        host.require_task_speaker_output_allowed("output-only voice acceptance probe")
    else:
        host.require_task_audio_allowed("voice acceptance probe")
    if args.output.exists(): raise RuntimeError("do not overwrite or repeat a voice attempt")
    if args.teaching_text_chain:
        raise ValueError('fixed text on a superseded controller is intentionally unauthorized; use --teaching-wav')
    teaching_chain = bool(args.teaching_wav)
    if grade_chain and (grade_current or not output_only or not teaching_chain
            or not args.verify_picture_state or prepare_grade_quiz or grade_correction):
        raise ValueError('continuous grade scene requires output-only three WAV teaching chain, no prepared quiz')
    if prepare_grade_quiz and not grade_current:
        raise ValueError('quiz preparation belongs only to the explicit grade scene')
    if grade_correction and (not grade_current or prepare_grade_quiz):
        raise ValueError('correction requires the current graded question; no quiz preparation')
    if grade_current and (not output_only or not args.wav or not args.verify_picture_state
            or teaching_chain or args.followup_wav or args.prepare_picture or args.point_code
            or args.manual_turn_probe or args.replace_picture_on_playback):
        raise ValueError('grade scene requires one fixed WAV, existing task picture and output-only mode')
    if teaching_chain and (not args.verify_picture_state or args.wav or args.followup_wav
            or args.manual_turn_probe or args.point_code or args.replace_picture_on_playback):
        raise ValueError('teaching WAV chain requires existing isolated picture only; no mixed probe modes')
    if args.replace_picture_on_playback:
        if not args.verify_picture_state or not args.followup_wav:
            raise ValueError("replacement scene requires existing isolated picture state and fixed follow-up")
        allowed_pictures = {(ROOT / ('benchmarks/raw/evidence/diagram-input-' + direction + '.png')).resolve()
                            for direction in ('forward', 'reverse')}
        if args.replace_picture_on_playback.resolve() not in allowed_pictures or not args.replace_picture_on_playback.is_file():
            raise ValueError("replacement scene reuses only the existing direction comparison pictures")
    if args.followup_wav and (not args.wav or args.manual_turn_probe or args.point_code):
        raise ValueError("same-session follow-up requires fixed WAV picture mode, no manual/point probe")
    if args.followup_wav and not (args.prepare_picture or args.verify_picture_state):
        raise ValueError("same-session follow-up requires isolated picture mode")
    for wav_path in (args.wav, args.followup_wav, *(args.teaching_wav or [])):
        if wav_path and not wav_path.is_file(): raise ValueError("fixed WAV missing; do not start host")
    capture_seconds = teaching_capture_seconds(args.teaching_wav) if teaching_chain else (195 if args.followup_wav else 75)
    store_path = (ROOT / 'benchmarks/raw' / args.store).resolve()
    if not store_path.is_relative_to((ROOT / 'benchmarks/raw').resolve()):
        raise ValueError('voice fixture store must stay under project raw directory')
    if args.prepare_picture and (not args.store.startswith('neko-daily-speech-acceptance-') or store_path.exists()):
        raise ValueError('picture preference preparation requires a new isolated speech-acceptance store')
    if args.verify_picture_state and not (args.store.startswith(('neko-daily-speech-acceptance-','neko-daily-silent-vision-'))
            or (grade_enabled and args.store.startswith('neko-daily-continuous-text-'))):
        raise ValueError('picture constraint probe must use an isolated speech-acceptance store')
    if grade_enabled and not (grade_chain and args.prepare_picture):
        provenance = json.loads((store_path/'task-provenance.json').read_text(encoding='utf-8'))
        if provenance.get('fresh') is not True:
            raise ValueError('grade scene needs an existing task-owned fixture; preserve user history')
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with sockets.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("an existing host owns the ports; leave it running")
    report = {"events": [], "room_microphone": False, "input": "text inside actual audio session",
              "volume_changed": False, "started_at": datetime.now(timezone.utc).isoformat()}
    report['store'] = args.store
    report.update(output_only=output_only, capture_devices=False if output_only else 'fake input',
                  loopback_enabled=not output_only)
    if teaching_chain:
        report['teaching_wav_chain'] = True
        report['loopback_deadline_seconds'] = capture_seconds
        report['input_scope'] = ('three fixed WAVs through RNNoise/native ASR; no capture devices'
                                 if output_only else 'three fixed WAVs through RNNoise/native ASR; fake silent input device, no room mic')
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
    if getattr(args, 'phrase_input', False):
        env['NEKO_EXPERIMENTAL_PHRASE_INPUT'] = '1'
        report['experimental_phrase_input'] = True
    if grade_enabled:
        env['NEKO_STUDY_AUTO_GRADE'] = '1'
        report['native_grade_opt_in'] = True
        report['grade_intent'] = 'correction' if grade_correction else 'answer'
        if grade_chain:
            report['native_grade_chain'] = True
    if grade_chain and args.prepare_picture:
        store_path.mkdir(parents=True, exist_ok=False)
        with (store_path/'task-provenance.json').open('x', encoding='utf-8') as provenance:
            json.dump({'fresh':True,'purpose':'actual no-question Native quiz, answer and non-answer follow-up',
                'created':time.time()}, provenance)
    startup_log = args.output.with_suffix('.host.log')
    startup_handle = startup_log.open('xb')
    report['startup_log'] = str(startup_log)
    provider_override = CoreProviderOverride(store_path, 'free')
    process = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8", str(ROOT / "scripts/neko_desktop_tutor_host.py"),
        "--source", "--voice", "--core-provider", "free", "--store", args.store,
        "--hold", str(max(360,capture_seconds+120)), "--seconds", "100", "--api-budget", "30", "--egress-budget", "2000",
        "--allow-host", "www.lanlan.app:unlimited", "--allow-host", "www.lanlan.tech:0",
        "--budget-round", "bargein-autocheck-20261012"] + (["--output-only"] if output_only else []) + (["--study-vision"] if args.prepare_picture or args.verify_picture_state else []), cwd=ROOT, env=env,
        stdout=startup_handle, stderr=subprocess.STDOUT)
    report['host_launcher_pid'] = process.pid
    host_owner = [{'pid':process.pid, 'created_at':process_creation_time(process.pid)}]
    shell, meter, observer, observer_task, replacement_task = None, None, None, None, None
    native_history = NativeTraceHistory()
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
        surface.attach_study_store(store_path)
        if args.prepare_picture:
            # A fresh isolated course, reusing an existing fixture. No new diagram
            # or quiz, and no alterations to the learner's normal daily course.
            from neko_native_avatar_toolchain import call
            image = ROOT / 'benchmarks/raw/evidence' / ('diagram-input-forward.png' if grade_chain else 'diagram-input-sky-dark.png')
            if not image.is_file(): raise RuntimeError('existing picture fixture missing; no voice connection')
            report['prepared_picture_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
            report['prepared_course'] = args.store if grade_chain else 'daily-speech-constraints-20261014'
            for entry, fields in (
                ('study_session', {'action':'set_course','course_id':report['prepared_course']}),
                ('study_preferences', {'preferences':{'language':'zh-CN','length':'brief','proactive_quiz':False},'remember':True}),
            ):
                result = await asyncio.to_thread(call, entry, fields)
                if result.get('is_error') or not result.get('output',{}).get('ok'):
                    raise RuntimeError('fresh picture course setup refused; no voice connection')
            image_result = await asyncio.to_thread(client.call, 'study_submit_image', {
                'image_base64':base64.b64encode(image.read_bytes()).decode(),
                'text':('这张图作为本课材料，先简短确认主要箭头方向，不出题。' if grade_chain
                    else '这张图作为本课材料，先简短确认主要天气请求路线，不出题。'),
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
            if grade_current:
                from neko_native_grade_acceptance import grade_snapshot
                if prepare_grade_quiz:
                    report['grade_quiz_preparation'] = await asyncio.to_thread(call, 'study_quiz', {
                        'request':'只出一道当前图片中某一条箭头的方向题，答案只需一条连接的起点和终点；不要公布答案。'})
                    result = report['grade_quiz_preparation']
                    if not grade_quiz_prepared(result):
                        raise RuntimeError('formal grade quiz preparation failed; no Native connection')
                report['grade_before'] = await asyncio.to_thread(grade_snapshot,
                    store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
                from neko_study_answer_intent import read_question_pin
                pin = read_question_pin((store_path/'N.E.K.O').resolve())
                baseline = report['grade_before']
                question = baseline.get('question') or {}
                if not grade_baseline_matches(baseline, pin, correction=grade_correction):
                    raise RuntimeError('no matching question/grade input pin; do not start Native or fabricate a quiz')
                if prepare_grade_quiz and any(question.get(key) != result['output'].get(key)
                        for key in ('question_id','attempt_id')):
                    raise RuntimeError('prepared question replaced before input; do not adopt a new question')
                report['grade_input_pin'] = pin
            if teaching_chain:
                from neko_daily_failure_probe import database_snapshot
                report['teaching_db_before'] = await asyncio.to_thread(database_snapshot,
                    store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
            if grade_chain:
                from neko_native_grade_acceptance import grade_snapshot
                from neko_study_answer_intent import read_question_pin
                report['chain_before'] = await asyncio.to_thread(grade_snapshot,
                    store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
                empty = read_question_pin((store_path/'N.E.K.O').resolve(), include_empty=True)
                if (not report['chain_before'].get('ok') or not empty or empty.get('_question_empty') is not True
                        or any(empty.get(key) != report['chain_before'].get(key) for key in ('course_id','session_id'))):
                    raise RuntimeError('continuous scene requires healthy empty question; do not clear or fabricate pending')
                report['chain_empty_pin'] = empty
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
        if not output_only and not silence.exists():
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
                    if event.get("type") in ("session_failed", "session_ended_by_server") or (
                            event.get('type')=='status' and 'CHARACTER_SWITCHING_TERMINAL' in str(event.get('message',''))):
                        failed.set(); started.set(); ended.set()
                    if event.get("type") == "system" and event.get("data") == "turn end": ended.set()
            receiver = asyncio.create_task(receive())
            async def send(value):
                if output_only:
                    if value.get('action')=='ping' and (observer is None or observer.fixed_input_id is None):return
                    if observer is None:
                        if value.get('action')=='ping':return
                        raise RuntimeError('Native controller not verified; input refused')
                    await observer.send_current(value)
                else:
                    await socket.send(json.dumps(value, ensure_ascii=False))
            async def heartbeat():
                while True:
                    await asyncio.sleep(5)
                    await send({"action": "ping"})
            pinger = asyncio.create_task(heartbeat())
            async def prepare_renderer():
                nonlocal shell, observer
                with sockets.socket() as debug_port_probe:
                    debug_port_probe.bind(("127.0.0.1", 0))
                    debug_port = debug_port_probe.getsockname()[1]
                shell = await asyncio.to_thread(avatar.launch, ROOT / "benchmarks/raw" / args.store, 100,
                                                "compact", debug_port, None if output_only else str(silence), output_only)
                report["native"] = {"pid": shell["pid"], "windows": len(shell.get("windows", [])), "fake_silent_input": not output_only}
                if output_only:
                    observer = await NativeTelemetry.attach_when_ready(debug_port)
                else:
                    await asyncio.sleep(4)
                    observer = await NativeTelemetry.attach(debug_port)
                if output_only:
                    report['capture_policy'] = await observer.evaluate("({receipt:globalThis.NekoCapturePolicy?.getResult(),flag:globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true,readonly:!Object.getOwnPropertyDescriptor(navigator.mediaDevices,'getUserMedia')?.writable})")
                    proof=report['capture_policy']
                    if not (proof.get('flag') and proof.get('readonly') and (proof.get('receipt') or {}).get('status')=='installed'):
                        raise RuntimeError('Native renderer capture policy not installed; no input submitted')
                report["native_initial"] = native_history.capture(await observer.snapshot())
            try:
                if output_only:
                    await prepare_renderer()
                    report['fixed_input_control'] = await observer.begin_fixed_input()
                await send({"action": "start_session", "input_type": "audio", "language": "zh-CN",
                            "new_session": False, "independent_asr_enabled": False})
                if output_only:
                    deadline=time.monotonic()+45
                    while time.monotonic()<deadline:
                        snapshot=native_history.capture(await observer.snapshot())
                        events=(snapshot.get('trace') or {}).get('events',[])
                        report['native_final']=snapshot
                        if output_only and any(e.get('code') in ('VOICE_INPUT_CONTROL_REJECTED','VOICE_INPUT_LEASE_RESYNC_REQUIRED','ASR_INPUT_DELIVERY_FAILED') for e in events):
                            report['fixed_input_rejected']=[e for e in events if e.get('code')]
                            raise RuntimeError('Native fixed input control rejected; no retries')
                        if any(e.get('type') in ('session_failed','session_ended_by_server') for e in events):
                            raise RuntimeError('Native voice provider/session refused; no retries')
                        if any(e.get('type')=='session_started' for e in events):
                            started.set();break
                        await asyncio.sleep(0.2)
                    if not started.is_set():raise TimeoutError('Native session start timed out; no retries')
                else:
                    await asyncio.wait_for(started.wait(), 45)
                if failed.is_set(): raise RuntimeError("voice provider/session refused; no retries")
                if not output_only:
                    await prepare_renderer()
                native_changed = time.monotonic()
                async def observe_native():
                    nonlocal native_changed
                    progress = None
                    try:
                        while True:
                            snapshot = native_history.capture(await observer.snapshot())
                            report["native_final"] = snapshot
                            events = (snapshot.get("trace") or {}).get("events", [])
                            if output_only and observer.fixed_input_id is not None and (snapshot.get('fixed_input') or {}).get('active') is not True:
                                report['fixed_input_revoked'] = snapshot.get('fixed_input')
                                failed.set();ended.set()
                            if output_only and any(e.get('type') in ('session_failed','session_ended_by_server') for e in events):
                                failed.set();ended.set()
                            if output_only and any(e.get('code') in ('VOICE_INPUT_CONTROL_REJECTED','VOICE_INPUT_LEASE_RESYNC_REQUIRED','ASR_INPUT_DELIVERY_FAILED') for e in events):
                                report['fixed_input_rejected']=[e for e in events if e.get('code')]
                                failed.set();ended.set()
                            current_progress = native_response_progress(snapshot, progress)
                            if current_progress != progress:
                                progress = current_progress; native_changed = time.monotonic()
                            if any(e.get("type") == "system" and e.get("data") == "turn end" and
                                   e["wall"] >= report.get("input_wall", float("inf")) for e in events):
                                ended.set()
                            await asyncio.sleep(0.2)
                    except Exception as error:
                        report['native_observation_error']=type(error).__name__+': '+str(error)
                        failed.set();ended.set()
                        raise
                observer_task = asyncio.create_task(observe_native())
                async def replace_picture_when_playing():
                    deadline = time.monotonic() + 100
                    while time.monotonic() < deadline:
                        if failed.is_set(): raise RuntimeError("session failed before material replacement; no retries")
                        snapshot = report.get('native_final') or {}
                        trace = snapshot.get('trace') or {}
                        playback = snapshot.get('playback') or {}
                        recent = trace.get('events') or []
                        audible = playback.get('audible') is True or any(event.get('type') == 'native_speech_playback_state'
                            and event.get('audible') is True and event.get('wall', 0) >= report.get('input_wall', float('inf')) for event in recent)
                        chunks = [event for event in recent if event.get('type') == 'audio_chunk'
                                  and str(event.get('correlation_id') or '').startswith('native_connection_')]
                        if trace.get('binaryFrames', 0) > 0 and playback.get('active') and audible and chunks:
                            old_token = chunks[-1]['correlation_id']
                            report['material_replacement'] = {'requested_wall': time.time(), 'old_native_token': old_token,
                                'before': {'native_pcm_frames': trace['binaryFrames'], 'playback': playback},
                                'image_sha256': hashlib.sha256(args.replace_picture_on_playback.read_bytes()).hexdigest(),
                                'old_native_reply': ''.join(event.get('text', '') for event in recent if event.get('type') == 'gemini_response')}
                            save()
                            from neko_native_avatar_toolchain import call
                            status = report['study_before_voice'].get('data') or {}
                            current_course = status.get('study_course_id') or status.get('course_id')
                            if not current_course:
                                raise RuntimeError('current course receipt missing; do not guess target course')
                            result = await asyncio.to_thread(client.call, 'study_submit_image', {
                                'image_base64': base64.b64encode(args.replace_picture_on_playback.read_bytes()).decode(),
                                'text': '这张图是新的当前材料，简短说明主要箭头关系，不出题。',
                                'expected_course_id': current_course})
                            report['material_replacement'].update(submission_result=result, submission_completed_wall=time.time())
                            if result.get('error') or result.get('data', {}).get('degraded'):
                                raise RuntimeError('replacement submission refused or degraded; preserve evidence and stop')
                            report['material_replacement']['material_after_submission'] = await asyncio.to_thread(call, 'study_material', {})
                            # Represents the learner selecting the same already-existing
                            # picture in the controlled surface; no role pointer fabricated.
                            digest = report['material_replacement']['image_sha256']
                            selected = next((item['id'] for item in surface.materials.values() if item.get('sha256') == digest), None)
                            if selected: surface.select(selected)
                            report['material_replacement']['selected_surface_material'] = selected
                            save()
                            return
                        await asyncio.sleep(.1)
                    raise RuntimeError('no confirmed audible old-material playback within bounded replacement window')
                if args.replace_picture_on_playback:
                    replacement_task = asyncio.create_task(replace_picture_when_playing())
                if not output_only:
                    meter = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8", str(ROOT / "scripts/neko_loopback_meter.py"),
                        "--seconds", str(capture_seconds), "--out", str(args.output.with_suffix(".loopback.wav"))],
                        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                report["turns"] = []
                input_wavs = args.teaching_wav if teaching_chain else ([args.wav, args.followup_wav] if args.followup_wav else [args.wav])
                for turn_index, input_wav in enumerate(input_wavs):
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
                            if failed.is_set():raise RuntimeError('Fixed input refused or source revoked; stop remaining WAV')
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
                            "request_id": "daily-picture-voice-20261014-"+str(turn_index)})
                    deadline = time.monotonic() + 75
                    while time.monotonic() < deadline:
                        if observer_task.done():
                            observer_task.result()
                        if failed.is_set(): break
                        # Observe delayed fragments too; a first turn end may be premature.
                        playback = (report.get("native_final") or {}).get("playback") or {}
                        if (turn_index == 0 and args.replace_picture_on_playback
                                and replacement_task is not None and replacement_task.done()
                                and material_retirement_observed(report.get('material_replacement'),report.get('native_final') or {})):
                            replacement_task.result()
                            report['first_turn_ending'] = 'material_retired_not_complete_answer'
                            break
                        min_observation = 55 if args.prepare_picture or args.verify_picture_state else 35
                        if ended.is_set() and time.time() - report["input_wall"] > min_observation and time.monotonic() - native_changed > 6 and not playback.get("active"):
                            break
                        await asyncio.sleep(0.25)
                    else: report["turn_timeout"] = True
                    await asyncio.sleep(3)
                    report['native_final']=await checked_native_snapshot(observer,native_history,observer_task)
                    report["first_socket_audio_at"] = first_audio
                    report["reply"] = "".join(e.get("text", "") for e in report["events"]
                        if e.get("type") == "gemini_response" and e["at"] >= report["input_submitted_at"])
                    report["native_reply"] = "".join(e.get("text", "") for e in (report.get("native_final", {}).get("trace") or {}).get("events", [])
                        if e.get("type") == "gemini_response" and e["wall"] >= report["input_wall"])
                    turn_fields = ("input_submitted_at", "input_wall", "input_wav_sha256", "fixed_speech_end_offset",
                                   "input_audio_start_wall", "input_end_at", "input_end_wall", "fixed_speech_end_wall",
                                   "first_socket_audio_at", "reply", "native_reply", "turn_timeout")
                    turn = {key: report[key] for key in turn_fields if key in report}
                    if turn_index == 0 and report.get('first_turn_ending'):
                        turn['ending'] = report['first_turn_ending']
                    turn["observation_end_wall"] = time.time()
                    turn["native_pcm_frames"] = (report.get("native_final") or {}).get("trace", {}).get("binaryFrames", 0) - frames_before
                    turn_events = [event for event in (report.get("native_final") or {}).get("trace", {}).get("events", [])
                                   if event.get("wall", 0) >= turn["input_wall"]]
                    turn["native_first_pcm_wall"] = next((event["wall"] for event in turn_events if event.get("type") == "audio_frame"), None)
                    turn["playback_first_scheduled_wall"] = next((event["wall"] for event in turn_events
                        if event.get("type") == "native_speech_playback_state" and event.get("active")), None)
                    report["turns"].append(turn)
                    if grade_chain:
                        from neko_native_grade_acceptance import grade_snapshot
                        from neko_study_answer_intent import read_question_pin
                        turn['grade_after_turn'] = await asyncio.to_thread(grade_snapshot,
                            store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
                        turn['native_snapshot'] = report.get('native_final')
                        if turn_index == 0:
                            turn['grade_next_input_pin'] = read_question_pin((store_path/'N.E.K.O').resolve())
                            if not grade_baseline_matches(turn['grade_after_turn'], turn['grade_next_input_pin']):
                                raise RuntimeError('role quiz has no valid pending pin; stop before answer input')
                    if teaching_chain:
                        from neko_daily_failure_probe import database_snapshot
                        turn['study_database'] = await asyncio.to_thread(database_snapshot,
                            store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
                        question = turn['study_database']['current_question']
                        previous_question=(report.get('teaching_db_before') or {}).get('current_question',{})
                        if turn_index == 0 and (not question.get('question_id') or not question.get('attempt_id') or question.get('attempt_evaluated')
                                or question.get('question_id')==previous_question.get('question_id')):
                            raise RuntimeError('role did not create a new pending quiz; do not grade a missing or consumed question')
                    if turn_index == 0 and replacement_task is not None:
                        await replacement_task
                        report['material_replacement']['first_turn_trace'] = (report.get('native_final') or {}).get('trace', {}).get('events', [])
                    save()
                    if failed.is_set() or report.get("turn_timeout"): break
                if args.followup_wav or teaching_chain:
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
                report['native_final']=await checked_native_snapshot(observer,native_history,observer_task)
                if failed.is_set(): raise RuntimeError("voice session ended abnormally")
                observer_task.cancel();await asyncio.gather(observer_task,return_exceptions=True)
                observer_task=None
                await send({"action": "end_session", "reason": "bounded_daily_voice_probe"})
                if output_only:
                    report['fixed_input_release'] = 'end_session_and_release_same_validated_source'
            finally:
                pinger.cancel(); await asyncio.gather(pinger, return_exceptions=True)
                receiver.cancel(); await asyncio.gather(receiver, return_exceptions=True)
    except Exception as exc:
        report["failure"] = type(exc).__name__ + ": " + str(exc)
        if output_only and observer is not None:
            try:
                report['native_failure_snapshot']=await observer.snapshot()
                await observer.screenshot(args.output.with_suffix('.failure.native.png'))
            except Exception as diagnostic_exc:
                report['native_failure_snapshot_error']=type(diagnostic_exc).__name__
    finally:
        if grade_current and report.get('grade_before'):
            try:
                from neko_native_grade_acceptance import grade_snapshot
                report['grade_after'] = await asyncio.to_thread(grade_snapshot,
                    store_path/'N.E.K.O/plugins/study_companion/data/study_companion.db')
            except Exception as error:
                report['grade_after_error'] = type(error).__name__
        if replacement_task is not None and not replacement_task.done():
            replacement_task.cancel(); await asyncio.gather(replacement_task, return_exceptions=True)
        if observer_task is not None:
            observer_task.cancel(); await asyncio.gather(observer_task, return_exceptions=True)
        if observer is not None:
            if output_only:
                try: report['fixed_input_cleanup_release'] = await observer.end_fixed_input()
                except Exception as exc: report['fixed_input_cleanup_error'] = type(exc).__name__
            try: await observer.close()
            except Exception as exc: report["telemetry_cleanup_error"] = type(exc).__name__
        if meter is not None:
            try:
                if report.get('failure'):
                    meter.terminate()
                    report['loopback_incomplete'] = True
                out, err = await asyncio.to_thread(meter.communicate, timeout=capture_seconds+10)
                report["loopback"] = json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-400:]}
                if teaching_chain and not report.get('loopback_incomplete') and report['loopback'].get('wav'):
                    with wave.open(report['loopback']['wav']) as captured:
                        report['loopback_end_wall'] = report['loopback']['device']['capture_start_wall'] + captured.getnframes()/captured.getframerate()
                    report['loopback_covers_last_turn'] = bool(report.get('turns')) and report['loopback_end_wall'] >= report['turns'][-1]['observation_end_wall']
            except Exception as exc:
                meter.terminate(); report["loopback_error"] = type(exc).__name__
        if output_only:
            report['cleanup_errors'] = await asyncio.to_thread(cleanup_resources,
                surface, shell, process, host_owner, None, [], None)
        else:
            if shell is not None:
                avatar.shutdown(shell)
            await asyncio.to_thread(stop_owned_host, process)
            surface.shutdown(); surface.server_close()
        if not report.get('cleanup_errors') and process.poll() is not None:
            try:
                provider_override.restore()
            except (OSError, ValueError, RuntimeError) as error:
                report.setdefault('cleanup_errors', []).append(
                    f'provider settings: {type(error).__name__}: {error}')
        startup_handle.close(); surface_thread.join(timeout=3)
        report["after"] = json.loads(ledger_path.read_text())
        report['surface_guide_attempts'] = surface.guide_attempts
        if log_path.exists():
            with log_path.open("rb") as handle:
                handle.seek(log_start)
                fresh_log = handle.read().decode("utf-8", errors="replace")
            # These bounded diagnostic lines contain event timestamps, not credentials.
            report["timing_log"] = [line for line in fresh_log.splitlines() if any(mark in line for mark in (
                "voice user_transcript", "TRIGGER entry='__llm_tool__study_", "首个 audio.delta", "/api/llm-tools/callback/study_companion/", "native-timing", "study voice admission", "study voice identical", "study-material-audio", "[study-grade-event]", "[study-grade-tail]"))]
            if grade_enabled:
                from neko_spoken_turn_analysis import parse_phrase_deliveries
                report['phrase_deliveries'] = parse_phrase_deliveries(fresh_log)
                report['grade_markers'] = []
                for line in fresh_log.splitlines():
                    if '[study-grade-event] ' in line:
                        try: report['grade_markers'].append(json.loads(line.split('[study-grade-event] ', 1)[1]))
                        except ValueError: pass
                profiles = {m.get('profile') for m in report['grade_markers'] if m.get('profile')}
                report['grade_protocol_profile'] = next(iter(profiles)) if len(profiles) == 1 else None
            wire_records = []
            for line in fresh_log.splitlines():
                if "[wire-trace] " in line:
                    try: wire_records.append(json.loads(line.split("[wire-trace] ", 1)[1]))
                    except ValueError: pass
            report["wire_trace"] = wire_records
            from neko_spoken_turn_analysis import parse_study_text_records
            report['study_text_trace'] = parse_study_text_records(fresh_log)
        report["proof"] = ("actual provider and Native renderer only; no capture devices or loopback; physical output and human listening remain unverified"
                           if output_only else "separate actual provider/native/loopback; fixed input proves this device route, human listening remains unverified")
        if (args.prepare_picture or args.verify_picture_state) and not args.followup_wav and not teaching_chain and not grade_current:
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
                'temporary_english_does_not_change_preferences':teaching_defaults_unchanged(report),
                'native_pcm_frames':report.get('native_final',{}).get('trace',{}).get('binaryFrames',0)>0,
                'device_loopback_loud':report.get('loopback',{}).get('loud_chunks',0)>0,
                'english_reply_shape':bool(re.search('[A-Za-z]',wording)) and not re.search('[\u4e00-\u9fff]',wording),
                'two_sentence_shape':len(re.findall(r'[.!?](?:\s|$)',wording))==2,
                'session_normal':not report.get('failure') and not report.get('turn_timeout'),
            }
            report['picture_constraint_acceptance']={'checks':checks,
                'result':'CANDIDATE_CHECKS_PASS_REQUIRES_SEMANTIC_REVIEW' if all(checks.values()) else 'FAIL_OR_PARTIAL',
                'scope':'automatic timing/shape/device checks only; final question/no-quiz/database/diagram facts must be reviewed, human pending'}
            if output_only:
                native_checks={key:value for key,value in checks.items() if key!='device_loopback_loud'}
                report['output_only_native_acceptance']={
                    'checks':native_checks,
                    'result':'CANDIDATE_NATIVE_CHECKS_PASS_REQUIRES_SEMANTIC_REVIEW' if all(native_checks.values()) else 'FAIL_OR_PARTIAL',
                    'scope':'provider timing and Native renderer PCM only; no loopback device proof',
                    'physical_output':'UNVERIFIED_NO_LOOPBACK', 'human_experience':'PENDING'}
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
            if args.replace_picture_on_playback:
                replacement = report.get('material_replacement') or {}
                trace_events = (replacement.get('first_turn_trace') or []) + (report.get('native_final') or {}).get('trace', {}).get('events', [])
                old_token = replacement.get('old_native_token')
                cancels = [event for event in trace_events if event.get('type') == 'game_route_speech_cancel' and event.get('correlation_id') == old_token]
                stops = [event for event in trace_events if event.get('type') == 'speech_playback_state' and event.get('reason') == 'native_connection_cancel'
                         and event.get('correlationId') == old_token and event.get('active') is False]
                followup_frames = [event for event in trace_events if event.get('type') == 'audio_frame'
                                   and len(turns) == 2 and event.get('wall', 0) >= turns[1]['input_wall']]
                checks.pop('same_current_picture')
                checks['two_observed_input_turns'] = checks.pop('two_completed_turns')
                checks.update({'current_picture_replaced':bool(before_m.get('material_id')) and bool(after_m.get('material_id')) and before_m['material_id'] != after_m['material_id'],
                    'old_token_cancel_received':bool(old_token) and bool(cancels),
                    'native_queue_stop_receipt':bool(stops),
                    'followup_uses_new_native_token':bool(followup_frames) and all(str(event.get('correlation_id') or '').startswith('native_connection_') and event['correlation_id'] != old_token for event in followup_frames)})
                replacement['cancel_received_wall'] = min((event['wall'] for event in cancels), default=None)
                replacement['native_stop_receipt_wall'] = min((event['wall'] for event in stops), default=None)
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
        if output_only and report.get('turn_timeout') and not report.get('failure'):
            report['failure'] = 'TimeoutError: fixed input produced no completed response before the deadline'
        report['finalized'] = True
        if grade_current:
            from neko_native_grade_acceptance import grade_acceptance
            report['grade_acceptance'] = grade_acceptance(report)
            from neko_spoken_turn_analysis import analyze_grade_latency
            report['grade_latency'] = analyze_grade_latency(report)
        if grade_chain:
            from neko_native_grade_acceptance import grade_chain_acceptance
            report['grade_chain_acceptance'] = grade_chain_acceptance(report)
        save()
        print(json.dumps({"report": str(args.output), "failure": report.get("failure"), "reply": report.get("reply"),
                          "audio_bytes": report.get("socket_audio_bytes"), "loopback_loud": (report.get("loopback") or {}).get("loud_chunks"),
                          "spent": report["after"]["spent"], "acceptance": report.get('acceptance')}, ensure_ascii=False), flush=True)
        if output_only and (report.get('failure') or report.get('cleanup_errors')):
            raise SystemExit(1)
        if grade_current and not all(report['grade_acceptance']['checks'].values()):
            raise SystemExit(1)
        if grade_chain and not all(report['grade_chain_acceptance']['checks'].values()):
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="neko-daily-acceptance-20261014")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wav", type=Path, help="fixed PCM WAV; never opens a room microphone")
    parser.add_argument("--followup-wav", type=Path, help="one fixed WAV follow-up in the same bounded audio session; isolated picture mode only")
    parser.add_argument("--replace-picture-on-playback", type=Path, help="once old native playback is audible, submit the existing forward diagram; no retries")
    parser.add_argument("--manual-turn-probe", action="store_true", help="one opt-in explicit-end support scene; no production VAD change")
    parser.add_argument("--point-code", action="store_true", help="prepare authorized source selected by learner; require actual role to point")
    parser.add_argument("--speech-gate", action="store_true", help="one opt-in Study execution-admission scene; never changes onset/cancel")
    parser.add_argument("--output-only", action="store_true", help="speaker output with guarded capture APIs; no fake microphone or loopback")
    parser.add_argument("--phrase-input", action="store_true", help="one opt-in real phrase collector scene; default off")
    parser.add_argument("--grade-current", action="store_true", help="one actual ASR -> formal current-question grade; output-only task fixture required")
    parser.add_argument("--grade-chain", action="store_true", help="output-only three WAVs: no-question request, own answer, non-answer follow-up; no pre-generated quiz")
    parser.add_argument("--grade-correction", action="store_true", help="explicit same-question correction; requires --grade-current and an evaluated wrong/partial attempt")
    parser.add_argument("--prepare-grade-quiz", action="store_true", help="prepare one formal quiz from this task's existing picture before the grade scene")
    parser.add_argument("--prepare-picture", action="store_true", help="fresh isolated course with an existing image, Chinese preference and no proactive quiz")
    parser.add_argument("--verify-picture-state", action="store_true", help="reuse the existing isolated picture course, read before/after; no extra image model preparation")
    parser.add_argument("--teaching-text-chain", action="store_true", help="disabled: a superseded controller must not gain text authority")
    parser.add_argument("--teaching-wav", type=Path, nargs=3, help="three fixed WAVs: picture quiz, wrong answer, history summary; existing isolated picture only")
    asyncio.run(main(parser.parse_args()))
