r"""Launch the real N.E.K.O host for the desktop Study tutor, text-only.

Usage (isolated source-host Python, including psutil):
  python scripts/neko_desktop_tutor_host.py            # start, health-check, leave running
  python scripts/neko_desktop_tutor_host.py --probe    # same, then stop the host again
  python scripts/neko_desktop_tutor_host.py --stop     # stop the host this script started

Safety boundary, three independent layers, because a talking host is not acceptable
until audio is proven blocked:

1. Disposable storage root. The host reads `NEKO_STORAGE_SELECTED_ROOT`; nothing here
   touches the user's real config, characters or learning database.
2. Text-only configuration written into that store before launch: DISABLE_TTS=true, no
   speech/native-realtime provider credentials, proactive and wake word disabled.
   `DISABLE_TTS` alone is only a worker-selection gate in the source, so it is not the
   whole boundary.
3. Loopback egress sink. HTTP(S)_PROXY point at a local sink that tunnels only
   api.deepseek.com and denies plus records every other destination. A netstat poll runs
   beside it for independent runtime evidence. This sampling may miss short-lived
   connections; it is observation, not an operating-system network restriction.

The DeepSeek credential is read from the local key file the user left for this project,
is never printed, and is refused if it ever appears in an output artefact.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "benchmarks/raw/neko-app/resources/bin"
SERVER = APP / "projectneko_server.exe"
EVIDENCE = ROOT / "benchmarks/raw/evidence"
KEY_FILE = Path(r"D:\CODE\API\new api.txt")
ALLOWED_HOST = "api.deepseek.com"
# Named exceptions the development mute makes for the product's own native realtime
# audio, so a voice test does not have to switch NEKO_DEV_TEXT_ONLY off.
#
# `audio_frame_blocked` belongs here too, and did not for a whole night: the frame
# writer (tts_runtime.py:2300) is the transport for BOTH external TTS and the native
# realtime audio, because `handle_audio_data` -> `send_speech` -> `_write_audio_frame`
# (turn.py:1517, tts_runtime.py:2414). Refusing it silently dropped every realtime
# frame after the host had counted it, so a turn could log `audio_deltas=32` while no
# sample ever reached the page. Measured, not inferred: the same renderer playing a
# WebAudio tone registers 0.42 on the WASAPI loopback tap, the reply registered 0.0001.
# External TTS still cannot be born: provider selection (tts_client/__init__.py:306),
# worker selection (tts_runtime.py:768) and the dummy worker's queued speech
# (workers/dummy.py:52) stay refused, and DISABLE_TTS / ttsProvider are untouched.
VOICE_GATE_EXCEPTIONS = ",".join((
    "native_realtime_connect_blocked",
    "native_audio_callback_blocked",
    "speech_output_blocked",
    "audio_frame_blocked",
))
MODEL = "deepseek-flash"
# Measurement rig only: a local provider double can be pointed at with LIVETUTOR_MODEL_URL so a
# test can record what the outbound request actually carries. The product default is untouched
# unless someone sets that variable, and a local address bypasses the egress gate via NO_PROXY,
# which is exactly why it must never be the shipped configuration.
MODEL_URL = os.environ.get("LIVETUTOR_MODEL_URL", "").strip() or f"https://{ALLOWED_HOST}/v1"
SOURCE_APP = ROOT / "benchmarks/raw/neko-product-host"
SOURCE_PYTHON = SOURCE_APP / ".venv/Scripts/python.exe"


def require_task_audio_allowed(action: str) -> None:
    """Task-local silence overrides fake inputs, muted output and saved preferences."""
    policy = ROOT / "benchmarks/raw/daily-companion-audio-policy.json"
    silent = os.environ.get("NEKO_TASK_SILENT") == "1"
    if policy.exists():
        try:
            data = json.loads(policy.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or type(data.get("audio_allowed")) is not bool:
                raise ValueError("audio_allowed must be an explicit boolean")
            silent = silent or not data["audio_allowed"]
        except (OSError, ValueError):
            raise RuntimeError("任务音频策略无法确认；拒绝启动声音设备路径。") from None
    if silent:
        raise RuntimeError(f"严格静音任务禁止 {action}；不启动扬声器、麦克风、虚拟输入或回环。")
PRODUCT = ROOT / "patches/neko-study-2026-10-10-product"
MAIN_PORT = 48911
PLUGIN_PORT = 48916


def require_task_speaker_output_allowed(action: str) -> None:
    """Explicit output permission never grants a capture or mixed UI permission."""
    policy = ROOT / "benchmarks/raw/daily-companion-audio-policy.json"
    try:
        data = json.loads(policy.read_text(encoding="utf-8"))
        permitted = (isinstance(data, dict) and data.get("speaker_output_allowed") is True
                     and data.get("microphone_allowed") is False
                     and data.get("capture_devices_allowed") is False)
    except (OSError, ValueError):
        permitted = False
    if os.environ.get("NEKO_TASK_SILENT") == "1" or not permitted:
        raise RuntimeError(f"任务未明确授权无捕获的扬声器输出：{action}")


def read_key() -> str:
    for line in KEY_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.strip()
        if value.startswith("sk-") and len(value) > 20:
            return value
    raise RuntimeError("no chat credential found")


def prepare_store(key: str, store: Path, core_provider: str = "deepseek") -> Path:
    """Merge the text-only safety settings into a disposable host store.

    The host's ConfigManager resolves core_config.json from %LOCALAPPDATA%, which
    is *not* covered by NEKO_STORAGE_SELECTED_ROOT, so the caller redirects that
    variable at this tree as well. Without that redirection the host reads the
    user's real settings, and the tutor's `agent` slot silently resolves to the
    user's provider instead of the disposable one.
    """
    config_file = store / "N.E.K.O/config/core_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, object] = {}
    if config_file.is_file():
        try:
            loaded = json.loads(config_file.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError('configuration must be an object')
            config = loaded
        except (OSError, ValueError):
            raise RuntimeError(f'宿主配置无法读取，已保留原文件：{config_file}') from None
    before = {"DISABLE_TTS": config.get("DISABLE_TTS"), "coreApi": config.get("coreApi"),
              "ttsProvider": config.get("ttsProvider"), "assistApi": config.get("assistApi")}
    config.update({
        "DISABLE_TTS": True,
        "enableCustomApi": True,
        # Only the avatar's own brain. The Study plugin asks for the `agent` slot, so a
        # `free` core is the product's own way to run realtime voice while the teaching
        # tools still resolve to the paid model - not a new orchestration layer.
        "coreApi": core_provider,
        "assistApi": "deepseek",
        "assistApiKeyDeepseek": key,
        "coreApiKeyDeepseek": key,
        "ttsProvider": "",
        "proactive_enabled": False,
        "voice_wake_word_enabled": False,
        # The tutor asks for the `agent` slot, which resolves through the custom
        # fields when enableCustomApi is on; assist alone is not enough. The file
        # schema is camelCase (config/api_profiles.py), not UPPER_SNAKE.
        "agentModelId": MODEL,
        "agentModelUrl": MODEL_URL,
        "agentModelApiKey": key,
    })
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"store": store.name, "config_before": before}, ensure_ascii=False))
    return store


def apply_voice_host_patch() -> str:
    """Replay the reliability patches onto the vendored host trees before anything imports them.

    N.E.K.O's own source lives in `benchmarks/`, which this repository ignores, so the fix for
    the silent tool-result drop exists as `scripts/neko_voice_host_patch.py` and gets re-applied
    here on every launch. A refused patch is reported rather than swallowed: an unpatched host
    behaves exactly like the patched one except that dropped tool work leaves no trace.
    """
    import neko_voice_host_patch as voice_patch
    import neko_output_only_patch as capture_patch
    from neko_runtime_helpers import deploy_runtime_helpers
    manifest = json.loads((ROOT / 'patches/neko-study-2026-10-10-host/manifest.json').read_text(encoding='utf-8'))
    results = []
    for host_root in voice_patch.HOSTS:
        deployed_helpers = deploy_runtime_helpers(ROOT, host_root, manifest)
        results.append(f"{host_root.name}/phrase-helpers={','.join(deployed_helpers)}")
        for relative, _ in voice_patch.TARGETS:
            target = host_root / relative
            results.append(f"{host_root.name}/{relative}={voice_patch.apply_to(target)}")
        import neko_spoken_turn_patch as turn_patch
        trace_path = host_root / "main_logic/omni_realtime_client/_wire_trace.py"
        original = trace_path.read_text(encoding="utf-8")
        traced = turn_patch.patch_wire_trace(original)
        if traced != original:
            trace_path.write_text(traced, encoding="utf-8", newline="\n")
        results.append(f"{host_root.name}/_wire_trace.py=diagnostics ready")
        results.append(f"{host_root.name}/capture-bootstrap={capture_patch.apply_to(host_root)}")
        import neko_dsml_output_patch as dsml_patch
        results.append(f"{host_root.name}/dsml-output={dsml_patch.apply_to(host_root)}")
    return ",".join(results)


def prepare_tutor_onboarding(runtime_root: Path) -> dict:
    """Tutor opens directly into learning, using the host's durable skip states."""
    sys.path.insert(0, str(SOURCE_APP))
    from utils.seven_day_tutorial_state import (
        load_seven_day_tutorial_store, replace_seven_day_tutorial_state,
    )
    from utils.initial_personality_state import (
        load_initial_personality_state, mark_initial_personality_state,
    )

    class TutorPaths:
        local_state_dir = runtime_root / "state"

        def get_config_path(self, name):
            return runtime_root / "config" / name

        def ensure_local_state_directory(self):
            self.local_state_dir.mkdir(parents=True, exist_ok=True)

    paths = TutorPaths()
    (runtime_root / "config").mkdir(parents=True, exist_ok=True)
    current = load_seven_day_tutorial_store(paths)
    progress = dict(current.get("state") or {})
    completed = set(progress.get("completedRounds") or [])
    skipped = sorted(set(range(1, 8)) - completed)
    if not current["initialized"] or progress.get("skippedRounds") != skipped:
        # "skip" is distinct from completing a lesson. Keep manual reset intents,
        # so the learner can still deliberately reopen the upstream tutorial.
        progress["skippedRounds"] = skipped
        progress["currentRound"] = None
        progress["pendingRound"] = None
        current = replace_seven_day_tutorial_state(
            progress, expected_revision=current["revision"], config_manager=paths)
    persona = load_initial_personality_state(paths)
    if persona["status"] == "pending" and not persona["manual_reselect_character_name"]:
        persona = mark_initial_personality_state("skipped", config_manager=paths)
    return {"tutorial_skipped": current["state"]["skippedRounds"],
            "tutorial_completed": current["state"]["completedRounds"],
            "persona_onboarding": persona["status"]}


def prepare_tutor_conversation_defaults(runtime_root: Path) -> str:
    """Use the host's real preference slot; preserve explicit saved choices."""
    path = runtime_root / "config/user_preferences.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not isinstance(rows, list):
        raise RuntimeError("学习偏好文件格式无效，已保留原文件：" + str(path))
    global_row = next((row for row in rows if isinstance(row, dict)
                       and row.get("model_path") == "__global_conversation__"), None)
    if global_row is None:
        global_row = {"model_path": "__global_conversation__"}
        rows.append(global_row)
    changed = "proactiveChatEnabled" not in global_row
    if changed:
        # Complicated proactive companionship is deferred by the contract.
        global_row["proactiveChatEnabled"] = False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return "proactive chat defaults off" if changed else "kept saved proactive choice"


def prepare_product_plugin(store: Path, *, study_vision: bool = False, text_only: bool = False) -> None:
    """Deploy only source/assets into the new isolated store; never copy learning data."""
    source = APP / "plugins/study_companion"
    target = store / "plugin-code/study_companion"
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file() and item.suffix in {".py", ".toml", ".md"}:
            shutil.copy2(item, target / item.name)
        elif item.is_dir() and item.name in {"static", "surfaces", "i18n"}:
            shutil.copytree(item, target / item.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.db", "*.sqlite*"))
    for overlay, destination in ((PRODUCT / "payload/study_companion", target),
                                 (PRODUCT / "static", target / "static")):
        if overlay.is_dir():
            for item in overlay.rglob("*"):
                if item.is_file() and item.suffix != ".cjs" and "__pycache__" not in item.parts:
                    output = destination / item.relative_to(overlay)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, output)
    manifest = (target / "plugin.toml").read_text(encoding="utf-8")
    if study_vision:
        # New daily stores have a working image entry; saved learner settings still win.
        manifest = manifest.replace('llm_vision_enabled = false', 'llm_vision_enabled = true')
        manifest = manifest.replace('llm_vision_max_image_px = 768', 'llm_vision_max_image_px = 2048')
    manifest = manifest.replace('plugins.study_companion.lab_bootstrap_plane:StudyCompanionPlugin',
                                'plugins.study_companion:StudyCompanionPlugin')
    manifest = manifest.replace('expose_legacy_static_panel = false', 'expose_legacy_static_panel = true')
    # Keep all teaching responses in Study UI; no character messaging or narration.
    manifest = manifest.replace('[study_companion.communication]\nenabled = true',
                                '[study_companion.communication]\nenabled = false')
    manifest = manifest.replace('solution_narration_enabled = true', 'solution_narration_enabled = false')
    manifest = manifest.replace('general_narration_enabled = true', 'general_narration_enabled = false')
    manifest = manifest.replace('os_signals_enabled = true', 'os_signals_enabled = false')
    manifest = manifest.replace('[study.supervision]\nenabled = true', '[study.supervision]\nenabled = false')
    (target / "plugin.toml").write_text(manifest, encoding="utf-8")
    if text_only:
        from neko_output_only_runtime import protected_html
        page = target / 'static/index.html'
        library = (ROOT/'scripts/neko_capture_policy.js').read_text(encoding='utf-8')
        page.write_text(protected_html(page.read_text(encoding='utf-8'), library, text_only=True), encoding='utf-8')


def prepare_summary_prompt_audit(store: Path) -> dict:
    """Instrument only an owned acceptance store; credentials never enter messages."""
    if not store.name.startswith('neko-daily-speech-acceptance-'):
        raise RuntimeError('summary prompt audit requires a task-owned acceptance store')
    relative='study_model_gateway.py'
    source=PRODUCT/'payload/study_companion'/relative
    target=store/'plugin-code/study_companion'/relative
    original=source.read_bytes()
    if target.read_bytes()!=original:
        raise RuntimeError('unknown gateway source; preserve it')
    text=original.decode('utf-8')
    anchor='        audit("started")\n'
    if text.count(anchor)!=1:raise RuntimeError('summary audit anchor changed')
    patched=text.replace(anchor,'        audit("started", **({"messages": messages} if operation == "summarize_session" else {}))\n',1)
    ast.parse(patched)
    target.write_text(patched,encoding='utf-8',newline='\n')
    return {'canonical_sha256':hashlib.sha256(original).hexdigest(),
            'instrumented_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'scope':'task-only summary messages; no headers/runtime/credentials'}


def prepare_session_tool_audit(store: Path) -> dict:
    """Observe public session-tool results in an owned continuous-text fixture."""
    if not store.name.startswith('neko-daily-continuous-text-'):
        raise RuntimeError('session tool audit requires a task-owned continuous-text store')
    source=PRODUCT/'payload/study_companion/study_avatar_tools.py'
    target=store/'plugin-code/study_companion/study_avatar_tools.py'
    original=source.read_bytes()
    if target.read_bytes()!=original:
        raise RuntimeError('unknown avatar tool source; preserve it')
    text=original.decode('utf-8')
    anchor='        # Only an ack has nothing to teach, so only an ack gets pre-worded: a status read\n'
    if text.count(anchor)!=1:raise RuntimeError('session audit anchor changed')
    audit_path=str(store/'session-tool-audit.jsonl')
    addition=(f'        with __import__("pathlib").Path({audit_path!r}).open("a", encoding="utf-8") as receipt:\n'
              '            receipt.write(json.dumps({"action": action, "requested_course": course_id,\n'
              '                **{key: state.get(key) for key in ("course_id", "session_id", "current_question", "question_state")}},\n'
              '                ensure_ascii=False) + "\\n")\n')
    patched=text.replace(anchor,addition+anchor,1);ast.parse(patched)
    target.write_text(patched,encoding='utf-8',newline='\n')
    return {'canonical_sha256':hashlib.sha256(original).hexdigest(),
            'instrumented_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'scope':'task-only public session-tool receipt; no headers/runtime/private answer'}


def ensure_react_chat_bundle() -> None:
    """Give the source host the chat window's compiled front end.

    The open tree carries no built frontend, so the desktop chat window mounts an
    empty capsule and 404s ``/static/react/neko-chat/neko-chat-window.iife.js``.
    The packaged app ships that bundle; reuse it instead of running a build.
    """
    source = APP / "static/react/neko-chat"
    target = SOURCE_APP / "static/react/neko-chat"
    if not source.is_dir():
        raise RuntimeError("打包版缺少 React 聊天构建产物，原生聊天窗口无法渲染")
    if (target / "neko-chat-window.iife.js").is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)


FREE_ROUTE_VOICE = "yui"


def apply_free_voice_route(store: Path) -> dict:
    """Pick the voice the app itself treats as provider-native on the free route.

    Why this is the difference between a talking avatar and a silent one, measured rather
    than assumed: `native_audio = not use_tts` (lifecycle.py:2381) decides whether the
    realtime session is opened with `modalities ["text","audio"]` or `["text"]`
    (omni_realtime_client/_transport.py:654). With the mainland preset
    `voice-tone-RcH2svtsrw`, `resolve_native_voice_for_routing('free', ..., 'wss://www.lanlan.app/core')`
    returns use_native=False, so `_resolve_session_use_tts` (tts_runtime.py:2124) answers
    "use the external TTS" - and the external TTS is muted by DISABLE_TTS, which stays on.
    The result was a turn that understood the question, called the teaching tools, produced
    a transcript and then said nothing (`audio_deltas=0`).
    `yui` is the product's own overseas free voice (`free_intl`: full Gemini set + yui) and
    does resolve native on that host, so the audio comes back inside the realtime session.
    It is *not* native on the mainland host, so this choice only speaks on the route this
    machine actually dials - fail-closed, not fail-silent.
    """
    path = (store / "N.E.K.O/config/characters.json").resolve()
    try:
        shown = path.relative_to(ROOT).as_posix()
    except ValueError:
        shown = path.as_posix()
    report = {"file": shown, "changed": {}, "skipped": {}}
    if not path.exists():
        # First startup has no card yet. Use the host's own defaults before its
        # route/prompt are read, instead of requiring a second launch to speak.
        path.parent.mkdir(parents=True, exist_ok=True)
        runtime_root = path.parent.parent
        seed_env = {**os.environ, "NEKO_TASK_SILENT":"1", "NEKO_DEV_TEXT_ONLY":"1",
            "NEKO_STORAGE_SELECTED_ROOT":str(runtime_root), "NEKO_STORAGE_ANCHOR_ROOT":str(runtime_root),
            "NEKO_STORAGE_CLOUDSAVE_ROOT":str(runtime_root), "NEKO_DO_NOT_TRACK":"1",
            "LOCALAPPDATA":str(store), "APPDATA":str(store)}
        subprocess.run([str(SOURCE_PYTHON), "-X", "utf8", "-B", "-c",
            "import json,sys; from config import get_localized_default_characters; "
            "data=get_localized_default_characters('zh-CN'); "
            "f=open(sys.argv[1],'x',encoding='utf-8'); "
            "json.dump(data,f,ensure_ascii=False,indent=2); f.close()", str(path)],
            cwd=SOURCE_APP, env=seed_env, capture_output=True, check=True, timeout=20)
        report["created_from_host_defaults"] = True
    data = json.loads(path.read_text(encoding="utf-8"))

    def walk(node: object) -> None:
        if isinstance(node, dict):
            reserved = node.get("_reserved")
            if isinstance(reserved, dict) and "voice_id" in reserved:
                current = str(reserved.get("voice_id") or "")
                if current == FREE_ROUTE_VOICE:
                    report["skipped"]["already native"] = current
                else:
                    reserved["voice_id"] = FREE_ROUTE_VOICE
                    report["changed"][current or "(empty)"] = FREE_ROUTE_VOICE
            for value in node.values():
                walk(value)

    walk(data)
    if report["changed"]:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def ensure_character_models(store: Path) -> list[str]:
    """Give the source host the Live2D model the store's own character card points at.

    The open tree only ships `mao_pro`; the bundled app carries the rest (yui-lolita is
    18 MB of moc3/motion files). With the model missing, `/static/yui-lolita/….model3.json`
    404s, `live2dManager.currentModel` stays null - and the floating toolbar that holds the
    microphone is built inside the model-load path, so a voice run has no native entry at
    all and looks like a UI defect instead of a missing asset.
    """
    copied: list[str] = []
    wanted: set[str] = set()
    cards = [*(store / "N.E.K.O/config").rglob("*.json"),
             *(store / "N.E.K.O/character_cards").rglob("*.json")]
    for card in cards:
        for match in re.finditer(r'"model_path"\s*:\s*"([^"]+)"', card.read_text(encoding="utf-8")):
            path = match.group(1).strip().lstrip("/")
            if path.startswith("static/") or "/" in path:
                wanted.add(path.split("/")[-2] if path.startswith("static/") else path.split("/")[0])
    for name in sorted(wanted):
        source, target = APP / "static" / name, SOURCE_APP / "static" / name
        if name in ("", ".", "..") or not source.is_dir() or target.is_dir():
            continue
        shutil.copytree(source, target)
        copied.append(name)
    return copied


def verify_source_audio_gate() -> None:
    manifest = json.loads((ROOT / "patches/neko-study-2026-10-10-host/manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = SOURCE_APP / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["patched_sha256"]:
            raise RuntimeError(f"text-only host source fingerprint differs: {item['path']}")
    for item in manifest.get("runtime_helpers", []):
        path = ROOT / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError(f"native phrase runtime helper fingerprint differs: {item['path']}")
    from neko_runtime_helpers import verify_runtime_helpers
    verify_runtime_helpers(ROOT, SOURCE_APP, manifest, SOURCE_PYTHON)


QUIET_BRAIN_KEYS = ("recent_memory_auto_review",)
# Turning powerful_memory off was this project's own saving, and the ledger says it backfired:
# with it off, fact extraction falls back to running on every learner turn. Itemising the
# learner's session (2026-10-12, `scripts/neko_request_attribution.py`) found 30 of the 80 paid
# requests sitting immediately after a `[MemoryServer] cache` write, i.e. per-turn memory work,
# while the idle reflection loop we were actually trying to silence had already been switched
# off separately. So the batched behaviour (product default: extract once every 10 turns) comes
# back on, and only where this launcher wrote the off value itself.
QUIET_BRAIN_REVERT = ("powerful_memory_enabled",)
QUIET_BRAIN_STATE = ROOT / "benchmarks/raw/neko-desktop-quiet-brain.json"


def apply_quiet_brain_config(runtime_root: Path) -> str:
    """Turn off the host's background memory loops, which are paid model calls.

    Only keys nobody has written are set, so a learner who turns a loop back on in the product
    keeps it. The emotion loop has no switch at all and still fires per reply. Keys this launcher
    did write are recorded, because a later measurement may show one of them was the expensive
    choice - and reverting our own write is not the same thing as overriding the learner's.
    """
    path = runtime_root / "config" / "core_config.json"
    if not path.is_file():
        return "no isolated core_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        return "core_config.json is not an object"
    try:
        written = json.loads(QUIET_BRAIN_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # The first run under this file's provenance: the earlier launcher wrote both keys off
        # and kept no record, so a key that is present as `False` and is one this project owns
        # the off-value for is treated as ours. A learner value cannot be told apart here, which
        # is why the revert only ever turns a key back on to the product default.
        written = [key for key in QUIET_BRAIN_KEYS + QUIET_BRAIN_REVERT
                   if config.get(key) is False]
    default_on = [key for key in QUIET_BRAIN_KEYS if key not in config]
    chosen_on = [key for key in QUIET_BRAIN_KEYS if config.get(key) is True]
    chosen_on += [key for key in QUIET_BRAIN_REVERT
                  if key not in written and config.get(key) is True]
    revert = [key for key in QUIET_BRAIN_REVERT
              if key in written and config.get(key) is False]
    if default_on:
        config.update({key: False for key in default_on})
    if revert:
        config.update({key: True for key in revert})
    if default_on or revert:
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        QUIET_BRAIN_STATE.parent.mkdir(parents=True, exist_ok=True)
        QUIET_BRAIN_STATE.write_text(json.dumps(sorted(set(written) | set(default_on))),
                                     encoding="utf-8")
    notes = []
    if default_on:
        notes.append("disabled " + ", ".join(default_on))
    if revert:
        notes.append("put back on (this launcher had turned it off, and per-turn extraction "
                     "costs more than the idle loop it saved): " + ", ".join(revert))
    if chosen_on:
        notes.append("kept the learner's own: " + ", ".join(chosen_on))
    return "; ".join(notes) if notes else "already quiet"


TUTOR_ROLE_GUIDANCE_PREFIX = "Study Companion mode:"
TUTOR_ROLE_GUIDANCE = (
    "Study Companion mode: when a study tool hands you teaching text, say it in the "
    "language it arrived in and keep code identifiers exact - never translate, "
    "summarize or extend it. The language the learner happened to type in does not "
    "choose the teaching language; the course preference does unless the learner "
    "explicitly requests a one-time switch. For that switch, set study_explain.language "
    "and keep the full length/quiz limits in question; never save the one-time language.\n"
    "Call required study tools silently; do not emit a planning sentence or an English "
    "tool-use preface before their results. Only the learner-facing answer should appear, "
    "in the current course language unless this turn explicitly requests another.\n"
    "Spoken delivery: your answer may be read aloud by a speech model that stumbles "
    "over digits and paths. In Chinese, say a line number as 第一百四十八行 rather than "
    "148 行; in English write line 148 as one flowing phrase. Refer to a file by its last "
    "segment (location_map.dart), never by a full path - the path belongs on the text "
    "surface, not in the sentence being spoken.\n"
    "Daily learning: be brief, patient and willing to correct yourself. Use study_preferences "
    "for explicit ongoing teaching preferences only; temporary requests are not memories. "
    "After a correction, recheck the submitted image or source evidence before answering. "
    "For source-change questions, analyze only the specified edit and trace its actual "
    "consumer and guards. Distinguish statement order, lookup keys and assigned values; "
    "do not give different edits the same effect without evidence. Do not add an unasked "
    "adjacent case that changes the conclusion. If asked for two sentences, use at most "
    "two short sentences total, including any uncertainty. "
    "When source questions name a file, use study_code mode=file first; a unique filename "
    "or path suffix can resolve through the authorized index. For ambiguous names, use the "
    "returned paths to choose the relevant file rather than broad symbol searches. "
    "For an explanation of an image submitted in Study, call study_material then study_explain with the learner's "
    "question and no invented observations in text. Study vision is the reliable image route.\n"
    "For an explicitly requested quiz (出一道题/方向题), call study_quiz, not study_explain. "
    "For a current-picture quiz omit topic so the saved pixels remain its source. "
    "Speak the actual returned question; never draft a possible question or stop at a quiz preface. "
    "Grade a learner answer with study_answer. "
    "For a recap of mistakes, corrections or learning progress, call study_summary before "
    "speaking; your own earlier wording is not a substitute for the stored learning record. "
    "Keep the relation's meaning: an arrow for a call is not evidence of data returning "
    "in the opposite direction.\n"
    "About yourself: when the learner asks what you can see, which files are in scope, or "
    "how the authorization works, call study_scope and answer from what it returns - never "
    "from impression, and never claim more reach than one authorized directory plus a window "
    "the learner names. Then spend at most one sentence on that, and take the conversation "
    "back to the material: name one concrete thread inside the project and offer to teach it. "
    "A turn that only describes the tool has not taught anything."
    "\nFor study follow-ups, include the learner's immediately preceding sentence, "
    "code-format and quiz limits in the teaching tool's question, until the "
    "learner changes them. A formatting-only voice fragment is not a new concept "
    "question: acknowledge it briefly and apply it to the next teaching answer."
    "\nIf a study tool returns degraded=true or status=unavailable, say its reply as "
    "written and stop. This is a service failure, not evidence that the learner's "
    "example cannot be explained. Do not invent teaching, a quiz, or a grade."
    "\nFor an architecture diagram, ask study_material whether a current Study picture "
    "exists, then use study_explain to inspect its actual pixels and arrowheads. Never "
    "infer direction from layout or an older picture. Native Realtime screen perception "
    "is not reliable evidence for this version; study_read_window supplies OCR words "
    "only. Without a Study picture, ask the learner to choose or paste the image in "
    "Study. Do not invent diagram observations in a tool's text/topic parameter. "
    "For pointing at displayed source, use study_point kind=source with the original "
    "source_line and symbol (source_file if ambiguous); the tool resolves current "
    "filtered evidence, so do not invent CSS. For diagram pointing, call study_point "
    "status first and copy its current material identity and locator metadata. The learner "
    "selects and scrolls the material; you "
    "only highlight. Source evidence from study_code is offered as a separate material, "
    "not automatically selected. Never reuse a previous version's coordinates."
    "\nDefault teaching replies to two short sentences, then let the learner follow up; "
    "respect an explicit request or saved preference for more detail. Your earlier answers "
    "are fallible history: prefer current tool evidence over repeating your own wording. "
    "For a specific source line use study_code file mode with a small window; cite the "
    "statement's actual line, not the enclosing function's declaration line. When corrected, "
    "read that material again and acknowledge a real mistake. Distinguish reordering named "
    "map/object entries from changing which value belongs to a key or positional argument; "
    "check the consumer before claiming that an order change breaks behaviour. A wrong "
    "value under an existing key is not a missing key: do not call that value undefined. "
    "When asked for two sentences, keep exactly two brief sentences without a third aside. An index "
    "refresh marked throttled does not block source queries: narrow the next read now, "
    "without asking the learner to wait for an imaginary service recovery."
)


def apply_tutor_role_guidance(runtime_root: Path) -> str:
    """Put the no-translation rule where the character's own prompt is read from.

    The host has no output-language instruction anywhere: `language_style` in
    prompts_chara.py permits every language in every locale, so the only
    character-level slot this can occupy is
    `_reserved.persona_override.prompt_guidance`, which persona_payload.py appends
    verbatim to the role prompt. This touches only the disposable project store, and
    never overwrites guidance the learner wrote themselves.
    """
    path = runtime_root / "config" / "characters.json"
    if not path.is_file():
        return "no characters.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        active = str(data.get("当前猫娘") or "").strip()
        card = (data.get("猫娘") or {}).get(active)
        if not isinstance(card, dict):
            return "no active character"
        reserved = card.get("_reserved")
        if not isinstance(reserved, dict):
            return "character has no _reserved"
        override = reserved.setdefault("persona_override", {})
        if not isinstance(override, dict):
            return "persona_override is not an object"
        if str(override.get("preset_id") or "").strip():
            # A persona preset owns this slot entirely: its guidance replaces the
            # base prompt, so writing here would silently do nothing.
            return "a persona preset already owns the guidance"
        existing = str(override.get("prompt_guidance") or "").strip()
        if existing == TUTOR_ROLE_GUIDANCE:
            return "already set"
        # Ours, from an earlier launch: an older copy of this same rule must not
        # outlive the rule. Recognised by the marker this function writes, so a
        # learner's own guidance still wins and is left alone.
        ours = existing.startswith(TUTOR_ROLE_GUIDANCE_PREFIX)
        if existing and not ours:
            return "kept the learner's own guidance"
        override["prompt_guidance"] = TUTOR_ROLE_GUIDANCE
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return "upgraded" if ours else "set"
    except (OSError, ValueError) as error:
        return f"skipped: {type(error).__name__}"


class Sink(threading.Thread):
    """Allow-listed CONNECT/HTTP relay that records every denial."""

    def __init__(self, max_paid: int | None = None, extra: dict[str, int | None] | None = None,
                 cap_file: Path | None = None, round_id: str | None = None, offline: bool = False) -> None:
        super().__init__(daemon=True)
        self.decisions: list[dict[str, object]] = []
        self.offline = offline
        self._lock = threading.Lock()
        # Every paid request to the model host is one tunnel, from the character's
        # own chat as well as from Study. Counting here caps both at once; the
        # in-code study budget alone leaves the avatar's turns unmetered.
        # Voice providers are closed by default: a host only appears in `budgets`
        # when the launch explicitly allows it with a limit, so audio can never
        # spend without a number attached to it.
        # A cap of zero means zero. Unlimited is the absence of a number, because
        # `--egress-budget 0` read as "no limit" once let 13 paid requests out of a
        # launch that was supposed to make none.
        self.budgets: dict[str, float] = {
            ALLOWED_HOST: float("inf") if max_paid is None else float(max_paid)}
        self.budgets.update({host.lower(): float("inf") if limit is None else float(limit)
                             for host, limit in (extra or {}).items()})
        self.spent: dict[str, int] = {}
        self.cap_file = cap_file
        self.round_id = round_id
        # A restart inside the same budget round must resume the real balance. The
        # cap used to be re-granted on every launch, so a night of restarts spent
        # far more than the number the operator typed once.
        self.resumed = False
        if cap_file is not None:
            self._load_ledger()
            if not self.resumed:
                if self.offline:
                    raise RuntimeError('offline relay requires an existing valid same-round ledger; it will not create or reset one')
                self._persist()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(32)
        self.port = self._server.getsockname()[1]
        self.stop = False

    @property
    def paid(self) -> int:
        with self._lock:
            return self.spent.get(ALLOWED_HOST, 0)

    @property
    def paid_cap(self) -> float | None:
        """The cap in force right now, `None` for uncapped so it stays valid JSON."""
        limit = self._limit(ALLOWED_HOST)
        return None if limit == float("inf") else limit

    def _record(self, host: str, action: str) -> bool:
        with self._lock:
            self.decisions.append({"host": host[:120], "action": action,
                                   "at": datetime.now(timezone.utc).isoformat()})
        return action == "allowed"

    def _limit(self, host: str) -> float | None:
        """The cap in force right now, unless the operator has raised it mid-launch.

        The character spends requests on its own for the first minute after boot, so a
        small budget is only useful if it can stay at zero through that burst and be
        opened just before the learner actually asks something.
        """
        self._adopt_live_caps()
        return self.budgets.get(host)

    def _adopt_live_caps(self) -> None:
        """Pull the whole cap file into memory before serving a request.

        Adopting every host, not just the one being asked about, is what keeps the next
        write-through from silently reverting a number the operator edited while the
        avatar was open. A per-host lookup did exactly that in testing.
        """
        if self.cap_file is None or not self.cap_file.is_file():
            return
        try:
            raw = self.cap_file.read_text(encoding="utf-8").strip()
        except OSError:
            return
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("budgets"), dict):
            live = data["budgets"]
        elif re.fullmatch(r"-?\d+", raw):
            # Legacy single-number file: it only ever meant the model host.
            live = {ALLOWED_HOST: float(raw)}
        else:
            return
        for name, entry in live.items():
            self.budgets[str(name).lower()] = float("inf") if entry is None else float(entry)

    def _read_ledger(self) -> dict | None:
        """The JSON ledger, or None when the file is absent/legacy/not JSON yet."""
        if self.cap_file is None or not self.cap_file.is_file():
            return None
        try:
            data = json.loads(self.cap_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) and "budgets" in data else None

    def _load_ledger(self) -> None:
        """Resume this round's balances; a different or missing round gets a fresh grant."""
        ledger = self._read_ledger()
        if not ledger or ledger.get("round") != self.round_id:
            return
        self.resumed = True
        for host, entry in ledger.get("budgets", {}).items():
            self.budgets[host] = float("inf") if entry is None else float(entry)
        self.spent = {host: int(used) for host, used in ledger.get("spent", {}).items()}

    def _persist(self) -> None:
        """Write the ledger so a restart in the same round cannot re-grant the budget.

        ``inf`` becomes ``null`` because bare ``Infinity`` is not portable JSON.
        """
        if self.cap_file is None:
            return
        body = {
            "round": self.round_id,
            "budgets": {host: (None if limit == float("inf") else limit)
                        for host, limit in self.budgets.items()},
            "spent": self.spent,
        }
        tmp = self.cap_file.with_name(self.cap_file.name + ".tmp")
        tmp.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.cap_file)

    def _spend(self, host: str) -> bool:
        """Reserve one request against that host's cap; refuse once it is spent."""
        with self._lock:
            limit = self._limit(host)
            if limit is None:
                return False
            used = self.spent.get(host, 0)
            if used >= limit:
                return False
            self.spent[host] = used + 1
            self._persist()
        return True

    def _refuse(self, conn: socket.socket, host: str, allowed: bool) -> None:
        self._record(host or "unknown", "denied" if not allowed else "budget_exhausted")
        reason = b"NEKO_EGRESS_BUDGET_EXHAUSTED" if allowed else b"Forbidden"
        conn.sendall(b"HTTP/1.1 403 " + reason + b"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(20)
            head = conn.recv(65536)
            if not head:
                return
            first = head.split(b"\r\n")[0].decode("latin-1", "replace")
            parts = first.split()
            target = ""
            if self.offline:
                if len(parts)>1:
                    target=(parts[1] if parts[0].upper()=='CONNECT' else re.sub(r'^https?://','',parts[1]).split('/')[0])
                self._record(target.split(':')[0].lower() or 'unknown', 'offline_denied')
                conn.sendall(b'HTTP/1.1 403 NEKO_EGRESS_OFFLINE\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
                return
            if parts and parts[0].upper() == "CONNECT":
                target = parts[1] if len(parts) > 1 else ""
                host = target.split(":")[0].lower()
                allowed = host in self.budgets
                if not allowed or not self._spend(host):
                    self._refuse(conn, host, allowed)
                    return
                conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                self._tunnel(conn, target)
                return
            if len(parts) > 1 and "//" in parts[1]:
                target = re.sub(r"^https?://", "", parts[1]).split("/")[0]
            host = target.split(":")[0].lower()
            allowed = host in self.budgets
            if allowed and self._spend(host):
                self._forward(conn, head, host)
                self._record(host, "allowed")
            else:
                self._refuse(conn, host, allowed)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _upstream(self, host: str, port: int) -> socket.socket:
        sock = socket.create_connection((host, port), timeout=20)
        self._record(host, "direct_connect")
        return sock

    def _tunnel(self, conn: socket.socket, target: str) -> None:
        host = target.split(":")[0].lower()
        if host not in self.budgets:
            self._record(host or "unknown", "denied")
            conn.close()
            return
        self._record(host, "allowed_connect")
        try:
            up = socket.create_connection((host, 443), timeout=20)
        except OSError:
            return
        # The 20s deadline bounds CONNECT/header setup, not an established
        # realtime conversation. Quiet in either direction must not close it.
        # The owning host's bounded lifetime and peer EOF still end the relay.
        conn.settimeout(None)
        up.settimeout(None)
        threading.Thread(target=self._pump, args=(conn, up), daemon=True).start()
        self._pump(up, conn)

    @staticmethod
    def _pump(source: socket.socket, dest: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                dest.sendall(data)
        except OSError:
            pass
        finally:
            for sock in (source, dest):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass

    def _forward(self, conn: socket.socket, head: bytes, host: str) -> None:
        try:
            up = socket.create_connection((host, 443 if host == ALLOWED_HOST else 80), timeout=20)
        except OSError:
            return
        # Absolute-URI requests already carry the path; keep them as sent.
        up.sendall(head)
        threading.Thread(target=self._pump, args=(conn, up), daemon=True).start()
        self._pump(up, conn)

    def run(self) -> None:
        while not self.stop:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return list(self.decisions)


def egress_audit(stop: threading.Event, pid: int, seen: set[str]) -> None:
    import psutil
    while not stop.is_set():
        try:
            descendants = {pid, *(child.pid for child in psutil.Process(pid).children(recursive=True))}
            out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError, psutil.Error):
            return
        for line in out.splitlines():
            if "ESTABLISHING" in line.upper():
                continue
            cols = line.split()
            if len(cols) >= 5 and cols[-1].isdigit() and int(cols[-1]) in descendants and cols[2].startswith(("127.", "[::")) is False:
                remote = cols[2]
                if not remote.startswith(("127.", "0.0.0.0", "[::1]", "::1")):
                    seen.add(remote)
        stop.wait(2.0)


def get(path: str, timeout: float = 8.0, method: str = "GET") -> tuple[int, str]:
    request = urllib.request.Request(
        path, method=method,
        data=b"{}" if method == "POST" else None,
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return int(error.code), ""
    except Exception as exc:  # noqa: BLE001 - health probe reports the failure type only
        return 0, type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="stop the host after health checks")
    parser.add_argument("--stop", action="store_true", help="stop the previously started host")
    parser.add_argument("--seconds", type=int, default=120, help="health wait budget")
    parser.add_argument("--hold", type=int, default=1800,
                        help="seconds to keep the host alive after health checks (0 = --probe)")
    parser.add_argument("--store", default="neko-appdata",
                        help="disposable LOCALAPPDATA tree under benchmarks/raw holding the plugin")
    parser.add_argument("--source", action="store_true", help="run pinned source host with verified text-only audio gates")
    parser.add_argument("--study-vision", action="store_true", help="enable existing Study vision for new store defaults")
    parser.add_argument("--api-budget", type=int, default=30, help="maximum Study model requests in this launch")
    parser.add_argument("--egress-budget", type=int, default=None,
                        help="hard cap on every paid model request this launch, character chat "
                             "included; omit for uncapped, 0 to allow none")
    parser.add_argument("--allow-host", action="append", default=[],
                        dest="allow_hosts",
                        help="extra host with its own cap, HOST:LIMIT. Voice hosts stay "
                             "closed unless listed here, so audio cannot spend uncounted")
    parser.add_argument("--budget-round", default=None,
                        help="label for one authorised spending round; restarts inside the "
                             "same round keep the spent balance instead of re-granting it")
    parser.add_argument("--core-provider", default="deepseek",
                        help="whose brain the avatar runs on; `free` selects the "
                             "app-supplied realtime profile (wss://www.lanlan.tech/core) "
                             "and needs no key, the Study plugin still uses `agent`")
    parser.add_argument("--voice", action="store_true",
                        help="except ONLY the native realtime audio events out of the "
                             "development mute; external TTS stays refused")
    parser.add_argument("--output-only", action="store_true",
                        help="source host only: block all browser capture APIs; fixed input over WS, speaker output only")
    parser.add_argument('--offline-egress', action='store_true',
                        help='deny this relay external requests before spending; keep the existing shared ledger')
    parser.add_argument('--text-only', action='store_true',
                        help='source host: guarded capture-free pages and muted text teaching')
    parser.add_argument('--summary-prompt-audit',action='store_true',
                        help='task acceptance store only: record actual summary messages in private API audit')
    parser.add_argument('--session-tool-audit',action='store_true',
                        help='continuous-text task store only: record public session-tool receipts privately')
    args = parser.parse_args()

    if args.text_only and (not args.source or args.voice or args.output_only):
        parser.error('--text-only requires source and cannot combine with voice/output-only')

    if args.output_only and not args.source:
        parser.error("--output-only requires the verified source host")
    if args.summary_prompt_audit and not args.source:
        parser.error('--summary-prompt-audit requires the verified source host')
    if args.session_tool_audit and not args.source:
        parser.error('--session-tool-audit requires the verified source host')
    if not args.stop and args.output_only:
        require_task_speaker_output_allowed("output-only source host")
    elif not args.stop and args.voice:
        require_task_audio_allowed("Native voice host")
    if not args.stop and not args.source:
        require_task_audio_allowed("unverified packaged host")

    pid_file = ROOT / "benchmarks/raw/neko-desktop-host.pid"
    if args.stop:
        if not pid_file.is_file():
            print(json.dumps({"stopped": False, "reason": "no pid file"}))
            return 1
        pid = int(pid_file.read_text().strip())
        get(f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/stop", timeout=30, method="POST")
        result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        pid_file.unlink(missing_ok=True)
        print(json.dumps({"stopped": result.returncode == 0, "pid": pid,
                          "detail": result.stdout.strip()[:200] or result.stderr.strip()[:200]}))
        return 0

    executable = SOURCE_PYTHON if args.source else SERVER
    try:
        __import__("psutil")
    except ImportError:
        raise SystemExit(f"Run this launcher with {SOURCE_PYTHON} (psutil is required for the process audit).")
    if not executable.is_file():
        print(json.dumps({"status": "MISSING_HOST_BINARY", "path": str(SERVER)}))
        return 1

    key = read_key()
    if args.source:
        print(f"宿主侧可靠性补丁：{apply_voice_host_patch()}")
        from neko_output_only_patch import HOSTS, apply_to
        for source_tree in HOSTS:
            apply_to(source_tree)
        verify_source_audio_gate()
    store = (ROOT / "benchmarks/raw" / args.store).resolve()
    if not store.is_relative_to(ROOT / "benchmarks/raw"):
        raise SystemExit("store must remain inside benchmarks/raw")
    store = prepare_store(key, store, args.core_provider)
    if args.source:
        prepare_product_plugin(store, study_vision=args.study_vision, text_only=args.text_only)
        if args.summary_prompt_audit:
            print(json.dumps({'summary_prompt_audit':prepare_summary_prompt_audit(store)}))
        if args.session_tool_audit:
            print(json.dumps({'session_tool_audit':prepare_session_tool_audit(store)}))
        runtime_root = store / "N.E.K.O"
        print(prepare_tutor_conversation_defaults(runtime_root))
        print(json.dumps({"tutor_onboarding": prepare_tutor_onboarding(runtime_root)}, ensure_ascii=False))
        policy = runtime_root / "state/storage_policy.json"
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text(json.dumps({"version": 1, "anchor_root": str(runtime_root),
            "selected_root": str(runtime_root), "selection_source": "default",
            "cloudsave_strategy": "fixed_anchor", "first_run_completed": True,
            "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    # The caps also have to be raisable while the avatar is open, so they live in a
    # JSON ledger the running relay re-reads per request. A launch must NOT rewrite a
    # live round: `--egress-budget 0` at the end of one night used to become the
    # ceiling of the next one, and a plain relaunch used to hand the whole budget back.
    cap_file = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
    extra_hosts: dict[str, int] = {}
    for entry in args.allow_hosts:
        host, _, limit = entry.rpartition(":")
        if not host or not (limit.isdigit() or limit == "unlimited"):
            raise SystemExit(f"--allow-host wants HOST:LIMIT, got {entry!r}")
        extra_hosts[host.lower()] = None if limit == "unlimited" else int(limit)
    round_id = args.budget_round or datetime.now(timezone.utc).strftime("round-%Y-%m-%d")
    sink = Sink(args.egress_budget, extra=extra_hosts, cap_file=cap_file, round_id=round_id, offline=args.offline_egress)
    sink.start()
    # Host and plugin share this process environment, so minting it once here is how
    # the plugin gets a first-party CSRF credential. A caller may pin its own value
    # for a scripted check; it is never logged or written to the evidence files.
    csrf_token = os.environ.get("NEKO_AUTOSTART_CSRF_TOKEN") or secrets.token_hex(16)

    env = dict(os.environ)
    env.update({
        "NEKO_STORAGE_SELECTED_ROOT": str(store),
        "NEKO_STORAGE_ANCHOR_ROOT": str(store),
        "NEKO_STORAGE_CLOUDSAVE_ROOT": str(store),
        # Own the whole app-data tree so the host never reads the user's real
        # core_config.json (whose provider is `free` with no key at all).
        "LOCALAPPDATA": str(store),
        "APPDATA": str(store),
        "PYTHONIOENCODING": "utf-8",
        "NEKO_DEV_AUDIO_ALLOW": VOICE_GATE_EXCEPTIONS if args.voice else "",
        "NEKO_OUTPUT_ONLY": "1" if args.output_only else "0",
        "NEKO_TEXT_ONLY": "1" if args.text_only else "0",
        "HTTP_PROXY": f"http://127.0.0.1:{sink.port}",
        "HTTPS_PROXY": f"http://127.0.0.1:{sink.port}",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    guidance_status: str | None = None
    character_models: list[str] = []
    voice_route: dict = {}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.source:
        ensure_react_chat_bundle()
        voice_route = apply_free_voice_route(store) if args.voice else {}
        character_models = ensure_character_models(store)
        # Before the character's prompt is built, not after - the host reads the
        # persona card at startup, so this is the last moment the rule can land in
        # the very first conversation turn.
        guidance_status = apply_tutor_role_guidance(runtime_root)
        env.update({"NEKO_MERGED": "1", "NEKO_CLOUDSAVE_DISABLED": "livetutor-isolated",
                    "NEKO_STORAGE_SELECTED_ROOT": str(runtime_root),
                    "NEKO_STORAGE_ANCHOR_ROOT": str(runtime_root),
                    "NEKO_STORAGE_CLOUDSAVE_ROOT": str(runtime_root),
                    "NEKO_DO_NOT_TRACK": "1", "PLUGIN_CONFIG_ROOT": str(store / "plugin-code"),
                    "NEKO_DEV_TEXT_ONLY": "1",
                    # The host derives its local-mutation CSRF token from this one env
                    # var, so minting it here gives the Study plugin - which runs with
                    # the same environment - a first-party credential instead of
                    # letting it guess an Origin. Fresh per launch, never printed.
                    "NEKO_AUTOSTART_CSRF_TOKEN": csrf_token,
                    "NEKO_DEV_AUDIO_AUDIT": str(EVIDENCE / f"neko-product-audio-{stamp}.jsonl"),
                    "NEKO_STUDY_API_BUDGET": str(max(0, args.api_budget)),
                    "NEKO_STUDY_API_AUDIT": str(EVIDENCE / f"neko-product-api-{stamp}.jsonl")})
    log_path = ROOT / "benchmarks/raw/neko-desktop-host.log"
    # Append, with a banner per launch. This file is the evidence channel for whole voice
    # turns - which response produced audio, which CONNECT the sink refused - and opening it
    # "wb" deleted the proof of every earlier launch inside the same spending round. The
    # acceptance runs are seconds apart, so a relaunch used to erase the run being cited.
    handle = log_path.open("ab")
    handle.write(f"\n===== launch {stamp} source={args.source} voice={args.voice} "
                 f"core={args.core_provider} round={args.budget_round} =====\n".encode())
    handle.flush()
    started = time.monotonic()
    command = [str(SOURCE_PYTHON), "launcher.py"] if args.source else [str(SERVER)]
    process = subprocess.Popen(command, cwd=str(SOURCE_APP if args.source else APP), env=env,
                               stdout=handle, stderr=subprocess.STDOUT)
    pid_file.write_text(str(process.pid), encoding="utf-8")

    stop = threading.Event()
    remote: set[str] = set()
    threading.Thread(target=egress_audit, args=(stop, process.pid, remote), daemon=True).start()

    base = f"http://127.0.0.1:{MAIN_PORT}"
    health: dict[str, object] = {}
    deadline = started + args.seconds
    ready_seconds = 0.0
    while time.monotonic() < deadline:
        status, _ = get(f"{base}/api/agent/user_plugin/availability")
        if status in (200, 409):  # 409 means the API is up but awaiting a storage choice
            ready_seconds = round(time.monotonic() - started, 1)
            break
        if process.poll() is not None:
            break
        time.sleep(2)

    # A host start does not re-scan the plugin directory on its own; without this
    # the Study UI answers 404 until something asks for a refresh.
    refresh_status, refresh_body = get(
        f"http://127.0.0.1:{PLUGIN_PORT}/plugins/refresh", timeout=30.0, method="POST"
    )
    registered = "study_companion" in refresh_body
    start_status, start_body = get(
        f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/start", timeout=90.0, method="POST"
    )
    time.sleep(2)
    plugin_running = start_status == 200 and '"success":true' in start_body.replace(" ", "")

    for name, url in (
        ("plugin_availability", f"{base}/api/agent/user_plugin/availability"),
        ("plugin_dashboard", f"{base}/api/agent/user_plugin/dashboard"),
        ("study_ui", f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/ui/"),
        ("study_ui_index", f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/ui/index.html"),
        ("study_ui_main", f"{base}/plugin/study_companion/ui/"),
    ):
        status, body = get(url)
        health[name] = {"status": status, "study_companion": "study_companion" in body,
                        "html": "<html" in body.lower(), "bytes": len(body),
                        "note": "" if status == 200 else body[:120]}

    time.sleep(6)

    # The launcher ties its lifetime to its parent process ("foreground
    # residency via parent_handle"), so this script must stay alive for the host
    # to keep serving. `--stop` or deleting the pid file ends the session.
    hold = 0 if args.probe else max(30, args.hold)
    deadline_hold = time.monotonic() + hold
    while hold and time.monotonic() < deadline_hold:
        if not pid_file.is_file() or process.poll() is not None:
            break
        time.sleep(2)

    stop.set()
    sink_decisions = sink.snapshot()
    allowed = sorted({d["host"] for d in sink_decisions if str(d["action"]).startswith("allowed")})
    denied = sorted({d["host"] for d in sink_decisions if d["action"] == "denied"})
    if args.source and process.poll() is None:
        get(f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/stop", timeout=30, method="POST")
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        pid_file.unlink(missing_ok=True)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host_binary": "pinned_source_launcher" if args.source else SERVER.name,
        "host_pid": process.pid,
        "host_running": process.poll() is None,
        "host_ready_seconds": ready_seconds,
        "storage_root": store.relative_to(ROOT).as_posix(),
        "safety_config": {"DISABLE_TTS": True, "ttsProvider": "empty",
                          "proactive": False, "wake_word": False,
                          "proxy_sink_port": sink.port},
        "source_text_only_gate": args.source,
        # The audit has to state which audio the mute let through and which it did not,
        # otherwise a voice launch reads as "audio protection removed".
        "voice_gate": {
            "requested": bool(args.voice),
            "allowed_events": sorted(VOICE_GATE_EXCEPTIONS.split(",")) if args.voice else [],
            "still_refused_events": [
                "tts_provider_selection_blocked",
                "tts_worker_selection_blocked",
                "ordinary_tts_request_blocked",
                "agent_connectivity_probe_blocked",
            ] if args.voice else sorted(VOICE_GATE_EXCEPTIONS.split(",")),
        },
        "tutor_role_guidance": guidance_status,
        # Without these the Live2D model 404s, and the floating toolbar that carries the
        # microphone is never built - the voice entry then looks like a product defect
        # rather than a missing asset in the open tree.
        "character_models_copied_from_packaged_app": character_models,
        "free_voice_route": voice_route,
        # The app rewrites the free realtime endpoint by region *after* reading its own
        # GeoIP verdict, and that lookup deliberately bypasses this proxy
        # (core_config.py:330), so the only ground truth about which host the avatar
        # dialled is the CONNECT list. Without it a launcher that allowed the configured
        # name and a build that dialled the regional one looked identical: silence.
        "voice_route": {
            "authorized_hosts": dict(sorted(extra_hosts.items())),
            "observed_hosts": sorted({d["host"] for d in sink_decisions
                                      if "lanlan" in str(d["host"])}),
            "geoip_probe": "ip-api.com, direct, invisible to this sink",
        } if args.voice else {},
        "api_budget": args.api_budget if args.source else None,
        "paid_egress_cap": args.egress_budget,
        # A raised cap must show up in the audit, otherwise a launch that spent more
        # than it was given reads as the old `--egress-budget 0` bug.
        "paid_egress_cap_final": sink.paid_cap,
        "paid_egress_cap_file": cap_file.relative_to(ROOT).as_posix(),
        "paid_egress_used": sink.paid,
        # The ledger is what makes the cap a round-level promise rather than a
        # per-launch one, so the audit has to show which round it resumed.
        "budget_round": sink.round_id,
        "budget_round_resumed": sink.resumed,
        "budget_ledger": {host: {"cap": (None if limit == float("inf") else limit),
                                 "spent": sink.spent.get(host, 0)}
                          for host, limit in sink.budgets.items()},
        "plugin_refresh": {"status": refresh_status, "study_companion_registered": registered},
        "plugin_start": {"status": start_status, "running": plugin_running},
        "health": health,
        "sink_allowed_hosts": allowed,
        "sink_denied_hosts": denied,
        "observed_external_connections": sorted(remote),
    }
    serialised = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if key in serialised:
        raise SystemExit("refusing to write a report containing the credential")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"neko-desktop-host-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(serialised + "\n", encoding="utf-8")
    handle.close()

    if args.probe and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        pid_file.unlink(missing_ok=True)
        report["host_running"] = False

    print(json.dumps({"status": "DESKTOP_HOST_PROBE", "artifact": out.relative_to(ROOT).as_posix(),
                      "host_running": report["host_running"],
                      "sink_allowed": allowed, "sink_denied": denied,
                      "external_connections": report["observed_external_connections"],
                      "health": {k: v["status"] for k, v in health.items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
