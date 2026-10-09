"""Isolated, method-level Study Companion tutoring loop.

Run with the project-local venv:
  .tmp-uv-cache/neko-study-venv/Scripts/python.exe -I -B scripts/neko_study_plugin_methods_fixture.py

This exercises the extracted release plugin methods with a deterministic local
agent double. It does not start the host, UI, OCR, audio, or any real provider.
All mutable plugin data is confined to .tmp-uv-cache.
"""
from __future__ import annotations

import builtins
import hashlib
import importlib
import io
import asyncio
import json
import logging
import multiprocessing
import os
from pathlib import Path
import socket
import _socket
import sqlite3
import subprocess
import sys
import tempfile
import types
import uuid
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "candidates" / "N.E.K.O"
RELEASE = ROOT / "benchmarks" / "raw" / "neko-app" / "resources" / "bin"
EVIDENCE_ROOT = ROOT / "benchmarks" / "raw" / "evidence"
TEMP_ROOT = ROOT / ".tmp-uv-cache" / "neko-study-method-fixture" / f"run-{uuid.uuid4().hex}"
COUNTS = {
    "provider_import_attempts_blocked": 0,
    "network_attempts_blocked": 0,
    "audio_attempts_blocked": 0,
    "process_attempts_blocked": 0,
    "outside_reads_blocked": 0,
    "outside_writes_blocked": 0,
    "outside_directory_writes_blocked": 0,
    "sqlite_outside_temp_blocked": 0,
    "sqlite_temp_opens": 0,
    "host_output_attempts_blocked": 0,
    "config_manager_stub_calls": 0,
    "network_provider_connects": 0,
    "own_config_served": 0,
}
BLOCKED_IMPORTS: list[str] = []
OUTSIDE_FILE_METADATA: list[dict[str, object]] = []
CONFIG_DATA_READS: list[dict[str, object]] = []
PLUGIN_INSTANCE_CREATED = False
PLUGIN_INSTANCE = None
AGENT_INSTANCE = None
ACTIVE_SESSION_ID = ""
_provider_downstream_calls = 0
_socket_downstream_calls = 0
_audio_downstream_calls = 0

# Real-model mode may name exactly one provider hostname. Nothing else about the
# guard layer changes: every other destination still fails closed at connect.
NETWORK_ALLOW_HOSTS: set[str] = set()
NETWORK_ALLOW_IPS: set[str] = set()
_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_GETHOSTBYNAME = socket.gethostbyname
_REAL_CREATE_CONNECTION = socket.create_connection


def _deny_process(*_args, **_kwargs):
    COUNTS["process_attempts_blocked"] += 1
    raise RuntimeError("process creation blocked")


def _deny_network(*_args, **_kwargs):
    COUNTS["network_attempts_blocked"] += 1
    raise RuntimeError("network access blocked")


def _deny_audio(*_args, **_kwargs):
    COUNTS["audio_attempts_blocked"] += 1
    raise RuntimeError("audio output blocked")


def _host_of(address) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0] or "").split("%")[0]
    return ""


def _network_gate(address) -> None:
    """Allow only the named provider host (or an IP it just resolved)."""
    host = _host_of(address)
    if host and (
        host.lower() in NETWORK_ALLOW_HOSTS or host in NETWORK_ALLOW_IPS
    ):
        COUNTS["network_provider_connects"] += 1
        return
    _deny_network()


def _gated_getaddrinfo(host, port, *args, **kwargs):
    _network_gate((host, port))
    infos = _REAL_GETADDRINFO(host, port, *args, **kwargs)
    if host.lower() in NETWORK_ALLOW_HOSTS:
        for info in infos:
            sockaddr = info[4] if len(info) > 4 else ()
            if isinstance(sockaddr, tuple) and sockaddr:
                NETWORK_ALLOW_IPS.add(str(sockaddr[0]))
    return infos


def _gated_gethostbyname(name):
    _network_gate((name, 0))
    address = _REAL_GETHOSTBYNAME(name)
    if str(name).lower() in NETWORK_ALLOW_HOSTS:
        NETWORK_ALLOW_IPS.add(str(address))
    return address


def _gated_create_connection(address, *args, **kwargs):
    _network_gate(address)
    return _REAL_CREATE_CONNECTION(address, *args, **kwargs)


def _install_guards() -> None:
    global _provider_downstream_calls
    sys.path[:0] = [str(CANDIDATE), str(RELEASE)]
    sys.dont_write_bytecode = True
    tempfile.tempdir = str(TEMP_ROOT)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    # Scope both candidate runtime storage and Electron's port-file fallback to
    # the ignored project temp area, never the user's profile.
    os.environ["NEKO_STORAGE_SELECTED_ROOT"] = str(TEMP_ROOT / "runtime")
    os.environ["APPDATA"] = str(TEMP_ROOT / "fake-appdata")
    os.environ["LOCALAPPDATA"] = str(TEMP_ROOT / "fake-localappdata")

    logging.getLogger().addHandler(logging.NullHandler())
    logging.getLogger("N.E.K.O.Plugin").addHandler(logging.NullHandler())

    # The real config manager creates user directories. Replace it with a
    # side-effect-free in-memory object before importing the plugin.
    import utils

    class InMemoryConfigManager:
        def get_core_config(self):
            return {}

        def get_model_api_config(self, *_args, **_kwargs):
            return {}

        def get_config(self, *_args, **_kwargs):
            return {}

    config_stub = types.ModuleType("utils.config_manager")
    config_stub.ConfigManager = InMemoryConfigManager

    def get_config_manager():
        COUNTS["config_manager_stub_calls"] += 1
        return InMemoryConfigManager()

    config_stub.get_config_manager = get_config_manager
    config_stub.get_plugins_directory = lambda *_a, **_k: TEMP_ROOT / "plugins"
    sys.modules["utils.config_manager"] = config_stub
    utils.config_manager = config_stub

    # Preserve Popen's type for asyncio internals while making all launches fail.
    real_popen = subprocess.Popen

    class BlockedPopen(real_popen):
        def __init__(self, *_args, **_kwargs):
            _deny_process()

    subprocess.Popen = BlockedPopen
    for name in ("run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        setattr(subprocess, name, _deny_process)
    for name in ("system", "popen", "startfile"):
        if hasattr(os, name):
            setattr(os, name, _deny_process)
    for name in dir(os):
        if name.startswith(("spawn", "exec")) and callable(getattr(os, name, None)):
            setattr(os, name, _deny_process)
    multiprocessing.process.BaseProcess.start = _deny_process

    import asyncio.windows_utils  # noqa: F401

    real_socket = socket.socket

    class BlockedSocket(real_socket):
        def __init__(self, *args, **kwargs):
            # The optional UI adapter may wrap an already accepted loopback
            # connection. It may never create or connect an outbound socket.
            # Real-provider mode additionally allows construction, because the
            # destination is not known yet; connect() stays destination-gated.
            if (
                kwargs.get("fileno") is not None
                or NETWORK_ALLOW_HOSTS
            ):
                real_socket.__init__(self, *args, **kwargs)
                return
            _deny_network()

        def connect(self, address):
            _network_gate(address)
            return real_socket.connect(self, address)

        def connect_ex(self, address):
            _network_gate(address)
            return real_socket.connect_ex(self, address)

        def bind(self, address):
            host = address[0] if isinstance(address, tuple) and address else ""
            if host not in {"127.0.0.1", "::1"}:
                _deny_network()
            return real_socket.bind(self, address)

    real_raw_socket = _socket.socket

    class BlockedRawSocket(real_raw_socket):
        def connect(self, address):
            _network_gate(address)
            return real_raw_socket.connect(self, address)

        def connect_ex(self, address):
            _network_gate(address)
            return real_raw_socket.connect_ex(self, address)

        def bind(self, address):
            host = address[0] if isinstance(address, tuple) and address else ""
            if host not in {"127.0.0.1", "::1"}:
                _deny_network()
            return real_raw_socket.bind(self, address)

    socket.socket = BlockedSocket
    _socket.socket = BlockedRawSocket
    socket.create_connection = _gated_create_connection
    socket.getaddrinfo = _gated_getaddrinfo
    socket.gethostbyname = _gated_gethostbyname

    # Provider and audio SDK imports are denied before module execution.
    blocked_prefixes = (
        "openai", "anthropic", "dashscope", "google.genai", "google.generativeai",
        "main_logic.tts_client", "main_logic.asr_client", "utils.tts", "utils.audio",
        "utils.audio_processor", "av", "soxr", "sounddevice", "pyaudio", "winsound",
        "dxcam", "mss", "pyautogui", "pynput", "screeninfo", "PIL.ImageGrab",
        "win32gui", "win32api", "pytesseract", "rapidocr_onnxruntime", "onnxruntime",
    )

    class ImportBlocker:
        def find_spec(self, fullname, path=None, target=None):
            if any(fullname == p or fullname.startswith(p + ".") for p in blocked_prefixes):
                BLOCKED_IMPORTS.append(fullname)
                COUNTS["provider_import_attempts_blocked"] += 1
                raise ImportError("external provider/audio/capture import blocked")

    sys.meta_path.insert(0, ImportBlocker())

    # Constrain sqlite to the project ignored temp subtree; use the genuine
    # SQLite implementation only for isolated fixture data.
    real_sqlite_connect = sqlite3.connect
    real_dbapi_connect = sqlite3.dbapi2.connect

    def guarded_sqlite_connect(database, *args, **kwargs):
        path = Path(os.fspath(database)).resolve()
        if path != TEMP_ROOT.resolve() and TEMP_ROOT.resolve() not in path.parents:
            COUNTS["sqlite_outside_temp_blocked"] += 1
            raise RuntimeError("SQLite path outside isolated temp blocked")
        COUNTS["sqlite_temp_opens"] += 1
        return real_sqlite_connect(database, *args, **kwargs)

    sqlite3.connect = guarded_sqlite_connect
    sqlite3.dbapi2.connect = guarded_sqlite_connect

    allowed_read_roots = tuple(
        p.resolve() for p in (CANDIDATE, RELEASE, TEMP_ROOT, Path(sys.prefix), Path(sys.base_prefix))
    )

    def read_root_class(resolved: Path) -> str:
        for root, label in (
            (TEMP_ROOT.resolve(), "fixture_temp"),
            (CANDIDATE.resolve(), "candidate_source"),
            (RELEASE.resolve(), "extracted_plugin_source"),
            (Path(sys.prefix).resolve(), "project_python_venv"),
            (Path(sys.base_prefix).resolve(), "bundled_python_runtime"),
        ):
            if resolved == root or root in resolved.parents:
                return label
        return "outside_allowed_roots"

    def safe_file_call_stack() -> list[dict[str, str]]:
        frame = sys._getframe(1)
        stack = []
        while frame is not None and len(stack) < 8:
            stack.append({
                "module": str(frame.f_globals.get("__name__", "unknown"))[:120],
                "function": frame.f_code.co_name[:120],
            })
            frame = frame.f_back
        return stack

    def check_path(path, mode: str) -> None:
        try:
            raw_path = os.fspath(path)
            if isinstance(raw_path, bytes):
                raw_path = os.fsdecode(raw_path)
            resolved = Path(raw_path).resolve()
        except Exception:
            COUNTS["outside_reads_blocked"] += 1
            OUTSIDE_FILE_METADATA.append({
                "path_class": "unresolvable_path",
                "path_type": type(path).__name__,
                "stack_inner_to_outer": safe_file_call_stack(),
            })
            raise RuntimeError("unresolvable file path blocked") from None
        writing = any(flag in mode for flag in ("w", "a", "x", "+"))
        if writing:
            in_temp = resolved == TEMP_ROOT.resolve() or TEMP_ROOT.resolve() in resolved.parents
            is_proof = (
                resolved.parent == EVIDENCE_ROOT.resolve()
                and resolved.name.startswith("neko-study-plugin-")
                and resolved.suffix == ".json"
            )
            if in_temp or is_proof:
                return
            COUNTS["outside_writes_blocked"] += 1
            raise RuntimeError("file write outside isolated temp blocked")
        if resolved.suffix.lower() in {".json", ".toml", ".yaml", ".yml", ".db", ".sqlite", ".sqlite3"}:
            entry = {
                "path_class": read_root_class(resolved),
                "suffix_class": "config_or_data",
            }
            entry["stack_inner_to_outer"] = safe_file_call_stack()
            if entry not in CONFIG_DATA_READS and len(CONFIG_DATA_READS) < 120:
                CONFIG_DATA_READS.append(entry)
        if not any(resolved == root or root in resolved.parents for root in allowed_read_roots):
            COUNTS["outside_reads_blocked"] += 1
            # Keep only safe metadata: no path, basename, or content.
            OUTSIDE_FILE_METADATA.append({
                "path_class": "outside_allowed_roots",
                "path_type": type(path).__name__,
                "stack_inner_to_outer": safe_file_call_stack(),
            })
            raise RuntimeError("file read outside isolated roots blocked")

    real_builtin_open, real_io_open = builtins.open, io.open
    real_path_open, real_os_open = Path.open, os.open
    real_os_mkdir, real_os_makedirs = os.mkdir, os.makedirs
    real_path_mkdir = Path.mkdir

    def check_temp_mutation(path) -> Path:
        resolved = Path(os.fspath(path)).resolve()
        if resolved == TEMP_ROOT.resolve() or TEMP_ROOT.resolve() in resolved.parents:
            return resolved
        COUNTS["outside_directory_writes_blocked"] += 1
        raise RuntimeError("directory mutation outside isolated temp blocked")

    def guarded_mkdir(path, mode=0o777, *, dir_fd=None):
        check_temp_mutation(path)
        return real_os_mkdir(path, mode, dir_fd=dir_fd)

    def guarded_makedirs(name, mode=0o777, exist_ok=False):
        check_temp_mutation(name)
        return real_os_makedirs(name, mode=mode, exist_ok=exist_ok)

    def guarded_path_mkdir(self, mode=0o777, parents=False, exist_ok=False):
        check_temp_mutation(self)
        return real_path_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    def guarded_builtin_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        check_path(file, mode)
        return real_builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def guarded_io_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        check_path(file, mode)
        return real_io_open(file, mode, buffering, encoding, errors, newline, closefd)

    def guarded_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        check_path(self, mode)
        return real_path_open(self, mode, buffering, encoding, errors, newline)

    def guarded_os_open(file, flags, *args, **kwargs):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        check_path(file, "w" if flags & write_flags else "r")
        return real_os_open(file, flags, *args, **kwargs)

    builtins.open = guarded_builtin_open
    io.open = guarded_io_open
    Path.open = guarded_path_open
    os.open = guarded_os_open
    os.mkdir = guarded_mkdir
    os.makedirs = guarded_makedirs
    Path.mkdir = guarded_path_mkdir

    # Fail closed for imports that bypass Python's public open wrappers.
    # OS code imports under sys.prefix/base_prefix and project source under ROOT.


def _exercise_gates() -> dict[str, object]:
    global _provider_downstream_calls, _socket_downstream_calls, _audio_downstream_calls
    try:
        importlib.import_module("dashscope")
    except ImportError:
        pass
    else:
        _provider_downstream_calls += 1
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=0.01)
    except RuntimeError:
        pass
    else:
        _socket_downstream_calls += 1
    try:
        _deny_audio("synthetic-study-audio")
    except RuntimeError:
        pass
    else:
        _audio_downstream_calls += 1
    return {
        "stimulus": ["blocked provider import", "blocked socket connect", "blocked audio sink"],
        "provider_downstream_calls": _provider_downstream_calls,
        "socket_downstream_calls": _socket_downstream_calls,
        "audio_downstream_calls": _audio_downstream_calls,
    }


class LocalAgentDouble:
    """Deterministic response fixture; no model/provider implementation exists."""

    def __init__(self, reply_type, lesson: str):
        self.reply_type = reply_type
        self.lesson = lesson
        self.calls: list[dict[str, object]] = []

    def _session_id(self, context):
        return str(context.get("session_id") or "")

    def _find_lesson(self, value):
        if isinstance(value, str):
            if value == self.lesson:
                return value
            try:
                decoded = json.loads(value)
            except (TypeError, ValueError):
                return ""
            return self._find_lesson(decoded) if decoded != value else ""
        if isinstance(value, dict):
            for nested in value.values():
                match = self._find_lesson(nested)
                if match:
                    return match
        elif isinstance(value, (list, tuple)):
            for nested in value:
                match = self._find_lesson(nested)
                if match:
                    return match
        return ""

    def _follow_up_index(self, text: str) -> int:
        followups = {
            "为什么例题2有1/2？": 1,
            "为什么要令 u=x^2？": 2,
        }
        if text in followups:
            return followups[text]
        try:
            request = json.loads(text)
        except (TypeError, ValueError):
            return 0
        return followups.get(request.get("current_followup"), 0) if isinstance(request, dict) else 0

    def _contains_exact_context_text(self, value, expected: str) -> bool:
        if isinstance(value, str):
            if value == expected:
                return True
            try:
                decoded = json.loads(value)
            except (TypeError, ValueError):
                return False
            return decoded != value and self._contains_exact_context_text(decoded, expected)
        if isinstance(value, dict):
            return any(self._contains_exact_context_text(nested, expected) for nested in value.values())
        if isinstance(value, (list, tuple)):
            return any(self._contains_exact_context_text(nested, expected) for nested in value)
        return False

    async def concept_explain(self, text, *, mode, context):
        follow_up_index = self._follow_up_index(text)
        is_follow_up = bool(follow_up_index)
        prior_lesson = self._find_lesson(context)
        prior_follow_up_reply = next((
            str(call.get("reply") or "") for call in reversed(self.calls)
            if call.get("follow_up_index") == 1
        ), "")
        first_follow_up = "为什么例题2有1/2？"
        call = {
            "method": "concept_explain",
            "input": text,
            "follow_up": is_follow_up,
            "follow_up_index": follow_up_index,
            "context_session_id": self._session_id(context),
            "prior_lesson_in_context": bool(prior_lesson) if is_follow_up else False,
            "previous_followup_question_in_context": self._contains_exact_context_text(context, first_follow_up) if follow_up_index == 2 else False,
            "previous_followup_response_in_context": self._contains_exact_context_text(context, prior_follow_up_reply) if follow_up_index == 2 and prior_follow_up_reply else False,
        }
        if is_follow_up:
            compact_lesson = "".join(str(prior_lesson or "").split()).lower().replace("²", "^2")
            if not prior_lesson or "u=x^2" not in compact_lesson or "du=2xdx" not in compact_lesson:
                raise RuntimeError("contextual follow-up lacks the exact prior example 2 material")
            if follow_up_index == 2 and not (call["previous_followup_question_in_context"] and call["previous_followup_response_in_context"]):
                raise RuntimeError("second follow-up context omitted the previous question or response")
            reply = (
                f"针对先前问题“{first_follow_up}”，结合前一解释“{prior_follow_up_reply}”，"
                "例题2中选择 u=x^2 后 du=2x dx，所以代换系数为 1/2。"
                if follow_up_index == 2 else
                f"针对先前内容“{prior_lesson}”，例题2中 du=2x dx，因此 x dx=du/2；被积式替换后系数就是 1/2。"
            )
            call["reply"] = reply
            self.calls.append(call)
            return self.reply_type(
                operation="concept_explain", input_text=text, reply=reply,
                payload={"summary": "根据先前例题2的代换关系解释 1/2", "diagnostic": "fixture", "contextual_follow_up": True},
            )
        self.calls.append(call)
        return self.reply_type(
            operation="concept_explain", input_text=text,
            reply="令 u=x^2，则 du=2x dx，所以 x dx=du/2；积分变为 (1/2)∫e^u du=(1/2)e^(x^2)+C。",
            payload={"summary": "用 u=x^2 代换", "diagnostic": "fixture"},
        )

    async def question_generate(self, text, *, mode, context):
        context_text = json.dumps(context, ensure_ascii=False, default=str)
        self.calls.append({"method": "question_generate", "input": text, "context_session_id": self._session_id(context), "prior_lesson_in_context": self.lesson in context_text})
        question = "计算 ∫ x·e^(x^2) dx，并写出令 u 等于什么。"
        answer = "u=x^2，du=2x dx，因此结果为 (1/2)e^(x^2)+C。"
        return self.reply_type(
            operation="question_generate", input_text=text,
            reply=question,
            payload={"question": question, "answer": answer,
                     "hint": "先比较 x dx 与 du", "difficulty": 2,
                     "topic": "u-substitution", "question_type": "short_answer"},
        )

    async def answer_evaluate(self, *, question, answer, expected_answer, mode, context):
        self.calls.append({"method": "answer_evaluate", "input": question, "context_session_id": self._session_id(context)})
        correct = "1/2" in answer and "e^" in answer and "u=x^2" in answer
        return self.reply_type(
            operation="answer_evaluate", input_text=answer,
            reply="回答正确：代换和系数 1/2 都正确。" if correct else "请检查 du=2x dx 导致的 1/2。",
            payload={"verdict": "correct" if correct else "partial",
                     "score": 100 if correct else 45,
                     "feedback": "代换与系数均正确。" if correct else "检查链式法则中的 1/2。",
                     "next_action": "再练一道 u 代换题", "error_type": "none",
                     "mastery_delta": 0.08 if correct else -0.02,
                     "topic": "u-substitution"},
        )

    async def summarize_session(self, history, *, mode, context):
        self.calls.append({"method": "summarize_session", "input": "session", "context_session_id": self._session_id(context), "history_interaction_ids": [str(row.get("id") or "") for row in history], "history_count": len(history)})
        summary = f"本次练习已保存；同一 SQLite 会话含 {len(history)} 条历史互动，主题为 u-substitution。"
        return self.reply_type(
            operation="summarize_session", input_text="session",
            reply=summary, payload={"summary": summary, "highlights": ["u-substitution"]},
        )


def _result_payload(result) -> dict[str, object]:
    value = getattr(result, "value", None)
    if value is None and hasattr(result, "__dict__"):
        value = dict(result.__dict__)
    if isinstance(value, dict):
        return value
    if isinstance(result, dict):
        return result
    return {"result_type": type(result).__name__, "value": str(value)[:300]}


def _own_plugin_config() -> dict[str, object]:
    """The plugin's own shipped config, as the host config bus would serve it.

    ``startup()`` reads it through ``ctx.get_own_config`` before building
    ``StudyConfig``. The shipped host-backends are still switched off here, so
    restoring the lifecycle does not quietly enable persistence backends,
    databases or auto-start behaviour that this fixture refuses.
    """
    import tomllib

    raw = tomllib.loads(
        (RELEASE / "plugins" / "study_companion" / "plugin.toml").read_text(encoding="utf-8")
    )
    plugin_section = dict(raw.get("plugin") or {})
    plugin_section["store"] = {**(plugin_section.get("store") or {}), "enabled": False}
    plugin_section["database"] = {**(plugin_section.get("database") or {}), "enabled": False}
    raw["plugin"] = plugin_section
    raw["plugin_state"] = {"backend": "off"}
    raw["plugin_runtime"] = {**(raw.get("plugin_runtime") or {}), "auto_start": False}
    return raw


def _safe_context():
    """Host context that counts and refuses every host-service call."""
    from types import SimpleNamespace

    class SafeContext:
        plugin_id = "study_companion"
        metadata = {"id": "study_companion", "i18n": {"default_locale": "en"}}
        logger = logging.getLogger("neko.study.fixture")
        bus = None
        config_path = RELEASE / "plugins" / "study_companion" / "plugin.toml"
        _effective_config = {
            "plugin": {"store": {"enabled": False}, "database": {"enabled": False}},
            "plugin_state": {"backend": "off"},
        }
        images = SimpleNamespace()

        async def get_own_config(self, *, timeout: float = 5.0, **_kwargs):
            # The one host service the genuine lifecycle legitimately needs:
            # the plugin's own effective config. Served from the shipped
            # plugin.toml instead of the host config bus.
            COUNTS["own_config_served"] += 1
            return _own_plugin_config()

        async def finish(self, **_kwargs):
            COUNTS["host_output_attempts_blocked"] += 1
            raise RuntimeError("host output blocked in fixture")

        def push_message(self, **_kwargs):
            COUNTS["host_output_attempts_blocked"] += 1
            raise RuntimeError("host output blocked in fixture")

        def __getattr__(self, name):
            if name.startswith(("get_", "update_", "replace_", "upsert_", "delete_", "set_", "trigger_", "export_", "create_", "run_")):
                async def blocked_host_method(*_a, **_k):
                    COUNTS["host_output_attempts_blocked"] += 1
                    raise RuntimeError("host service access blocked in fixture")
                return blocked_host_method
            raise AttributeError(name)

    return SafeContext()


async def bootstrap_plugin():
    """Import the extracted release plugin under the active guards and build it.

    Shared by the deterministic-double loop and the real-model loop so both
    exercise the genuine ``StudyCompanionPlugin`` construction path.
    """
    global PLUGIN_INSTANCE_CREATED, PLUGIN_INSTANCE
    # Import gates and data-path guards are active before plugin import/instance.
    plugin_module = importlib.import_module("plugins.study_companion")
    from plugin.sdk.shared.core.base import NekoPluginBase as SharedPluginBase

    def inert_file_logger(self, **_kwargs):
        logger = logging.getLogger("neko.study.fixture")
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        return logger

    SharedPluginBase.enable_file_logging = inert_file_logger

    # Exercise offline gates before constructing the plugin or invoking entries.
    gate_evidence = _exercise_gates()
    plugin = plugin_module.StudyCompanionPlugin(_safe_context())
    PLUGIN_INSTANCE_CREATED = True
    PLUGIN_INSTANCE = plugin
    return plugin_module, plugin, gate_evidence


async def _run_loop() -> dict[str, object]:
    global AGENT_INSTANCE, ACTIVE_SESSION_ID
    plugin_module, plugin, gate_evidence = await bootstrap_plugin()
    lesson = "例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx。"
    agent = LocalAgentDouble(plugin_module.TutorReply, lesson)
    plugin._agent = agent
    AGENT_INSTANCE = agent
    started = await plugin.study_start_session()
    start_payload = _result_payload(started)
    session_id = str(start_payload.get("session_id") or "")
    if not session_id:
        raise RuntimeError("real plugin start-session entry returned no session id")
    ACTIVE_SESSION_ID = session_id

    explain_result = await plugin.study_explain_text(text=lesson, session_id=session_id)
    explain_payload = _result_payload(explain_result)
    follow_up_text = "为什么例题2有1/2？"
    follow_up_result = await plugin.study_explain_text(text=follow_up_text, session_id=session_id)
    follow_up_payload = _result_payload(follow_up_result)
    second_follow_up_text = "为什么要令 u=x^2？"
    second_follow_up_result = await plugin.study_explain_text(text=second_follow_up_text, session_id=session_id)
    second_follow_up_payload = _result_payload(second_follow_up_result)
    question_result = await plugin.study_generate_question(
        text=lesson, topic="u-substitution", session_id=session_id
    )
    question_payload = _result_payload(question_result)
    question = str(question_payload.get("question") or "")
    expected = str(question_payload.get("answer") or "")
    answer = "u=x^2，du=2x dx，所以 ∫x·e^(x^2)dx=(1/2)e^(x^2)+C。"
    mastery_before = await asyncio.to_thread(plugin._knowledge_tracker.get_mastery, "u-substitution")
    evaluation = await plugin.study_evaluate_answer(
        answer=answer,
        question=question,
        expected_answer=expected,
        question_id=str(question_payload.get("question_id") or ""),
        attempt_id=str(question_payload.get("attempt_id") or ""),
        selected_topic_id="u-substitution",
        session_id=session_id,
    )
    evaluation_payload = _result_payload(evaluation)
    reused = await plugin.study_get_session(session_id=session_id)
    reused_payload = _result_payload(reused)
    stored_session = reused_payload.get("session") if isinstance(reused_payload.get("session"), dict) else {}
    interactions = reused_payload.get("interactions") if isinstance(reused_payload.get("interactions"), list) else []
    mastery_after = await asyncio.to_thread(plugin._knowledge_tracker.get_mastery, "u-substitution")
    session_rows = await asyncio.to_thread(plugin._store.list_sessions, 20)
    session_row = next((row for row in session_rows if row.get("id") == session_id), {})
    follow_up_calls = [call for call in agent.calls if call.get("follow_up")]
    follow_up_call = next((call for call in follow_up_calls if call.get("follow_up_index") == 1), None)
    second_follow_up_call = next((call for call in follow_up_calls if call.get("follow_up_index") == 2), None)
    follow_up_reply = str(follow_up_payload.get("reply") or follow_up_payload.get("summary") or "")
    second_follow_up_reply = str(second_follow_up_payload.get("reply") or second_follow_up_payload.get("summary") or "")
    follow_up_grounded = bool(
        follow_up_call
        and "例题2" in follow_up_reply
        and "u=x^2" in follow_up_reply
        and "du=2x dx" in follow_up_reply
        and "1/2" in follow_up_reply
    )
    if follow_up_text != "为什么例题2有1/2？" or not follow_up_grounded:
        raise RuntimeError("follow-up response did not demonstrate grounding in the exact prior example 2")
    second_follow_up_grounded = bool(
        second_follow_up_text == "为什么要令 u=x^2？"
        and second_follow_up_call
        and second_follow_up_call.get("prior_lesson_in_context")
        and second_follow_up_call.get("previous_followup_question_in_context")
        and second_follow_up_call.get("previous_followup_response_in_context")
        and "为什么例题2有1/2？" in second_follow_up_reply
        and "u=x^2" in second_follow_up_reply
        and "du=2x dx" in second_follow_up_reply
    )
    if not second_follow_up_grounded:
        raise RuntimeError("second follow-up did not retain the original example and exact previous turn")
    if len(interactions) < 5 or not question or evaluation_payload.get("verdict") != "correct" or mastery_after <= mastery_before:
        raise RuntimeError("tutoring sequence failed content, persistence, or mastery assertions")
    if stored_session.get("id") != session_id:
        raise RuntimeError("persisted session record ID did not match the active synthetic session")
    if any(str(item.get("session_id") or "") != session_id for item in interactions):
        raise RuntimeError("persisted interaction escaped the active synthetic session")
    if any(call.get("context_session_id") != session_id for call in agent.calls):
        raise RuntimeError("one or more local agent calls received a different session context")
    if _provider_downstream_calls or _socket_downstream_calls or _audio_downstream_calls:
        raise RuntimeError("an external provider/socket/audio downstream was reached")

    result = {
        "status": "PASS_PLUGIN_METHOD_LOOP",
        "level": "PLUGIN_METHOD; no host/UI/browser E2E",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "plugin_module": plugin_module.__name__,
        "plugin_class": plugin_module.StudyCompanionPlugin.__qualname__,
        "plugin_source_sha256": hashlib.sha256(Path(plugin_module.__file__).read_bytes()).hexdigest(),
        "entry_methods": ["study_start_session", "study_explain_text", "study_generate_question", "study_evaluate_answer", "study_get_session"],
        "source_tree": "extracted_release_plugin_with_candidate_sdk",
        "session_id": session_id,
        "synthetic_material": lesson,
        "explanation": str(explain_payload.get("reply") or explain_payload.get("summary") or "")[:500],
        "follow_ups": [
            {"question": follow_up_text, "reply": follow_up_reply[:500], "prior_example2_in_context": bool(follow_up_call and follow_up_call.get("prior_lesson_in_context")), "response_uses_example2_details": follow_up_grounded},
            {"question": second_follow_up_text, "reply": second_follow_up_reply[:500], "prior_example2_in_context": bool(second_follow_up_call and second_follow_up_call.get("prior_lesson_in_context")), "previous_question_in_context": bool(second_follow_up_call and second_follow_up_call.get("previous_followup_question_in_context")), "previous_response_in_context": bool(second_follow_up_call and second_follow_up_call.get("previous_followup_response_in_context")), "response_uses_previous_turn_and_example": second_follow_up_grounded},
        ],
        "question": question,
        "answer_evaluation": {"source": "deterministic_local_agent_double; not model grading", "verdict": evaluation_payload.get("verdict"), "score": evaluation_payload.get("score"), "feedback": evaluation_payload.get("feedback")},
        "persistence_reuse": {"session_record_id_matches": stored_session.get("id") == session_id, "agent_context_session_ids_match": all(call.get("context_session_id") == session_id for call in agent.calls), "interaction_session_ids_match": all(str(item.get("session_id") or "") == session_id for item in interactions), "interaction_count": len(interactions), "mastery_before_evaluation": mastery_before, "mastery_after_evaluation": mastery_after, "session_status": session_row.get("status")},
        "agent_double_calls": agent.calls,
        "gate_evidence": gate_evidence,
        "downstream_calls": {"provider": _provider_downstream_calls, "socket": _socket_downstream_calls, "audio": _audio_downstream_calls},
        "blocked_imports": BLOCKED_IMPORTS,
        "guards": COUNTS,
        "outside_file_attempts_safe_metadata": OUTSIDE_FILE_METADATA,
        "config_data_reads_safe_metadata": CONFIG_DATA_READS,
        "db_path_class": "project_ignored_temp_only",
        "host_started": False,
        "ocr_or_capture_used": False,
        "real_provider_or_model_used": False,
        "audio_or_mic_used": False,
    }
    proof_stamp = datetime.now(timezone.utc)
    proof_file = EVIDENCE_ROOT / f"neko-study-plugin-method-{proof_stamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    proof = {
        "timestamp_utc": proof_stamp.isoformat(),
        "result": result["status"],
        "evidence_level": result["level"],
        "source_tree": result["source_tree"],
        "plugin_file_sha256": result["plugin_source_sha256"],
        "session_id": session_id,
        "session_record_id_matches": result["persistence_reuse"]["session_record_id_matches"],
        "agent_context_session_ids_match": result["persistence_reuse"]["agent_context_session_ids_match"],
        "interaction_count": len(interactions),
        "interaction_session_ids_match": result["persistence_reuse"]["interaction_session_ids_match"],
        "mastery_before_evaluation": mastery_before,
        "mastery_after_evaluation": mastery_after,
        "sqlite_temp_opens": COUNTS["sqlite_temp_opens"],
        "blocked_attempts": {
            "provider_import": COUNTS["provider_import_attempts_blocked"],
            "network_socket": COUNTS["network_attempts_blocked"],
            "audio_fixture_sink": COUNTS["audio_attempts_blocked"],
        },
        "downstream_calls": result["downstream_calls"],
        "outside_reads_blocked": COUNTS["outside_reads_blocked"],
        "outside_writes_blocked": COUNTS["outside_writes_blocked"],
        "outside_directory_writes_blocked": COUNTS["outside_directory_writes_blocked"],
        "config_data_read_safe_metadata": CONFIG_DATA_READS,
        "db_path_class": "project_ignored_temp_only",
        "ocr_or_capture_used": False,
        "live_model_or_provider_used": False,
        "genuine_ui_e2e": False,
        "private_config_values_or_secrets_included": False,
    }
    proof_file.write_text(json.dumps(proof, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    result["proof_artifact"] = proof_file.relative_to(ROOT).as_posix()
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    # Windows' asyncio proactor loop uses an internal socket pair. Create that
    # runtime plumbing before the network guard, then block application sockets.
    loop = asyncio.new_event_loop()
    _install_guards()
    try:
        result = loop.run_until_complete(_run_loop())
    except BaseException as exc:
        result = {
            "status": "BLOCKED_OR_FAILED_PLUGIN_METHOD_LOOP",
            "error_type": type(exc).__name__,
            "error": str(exc)[:360],
            "guards": COUNTS,
            "blocked_imports": BLOCKED_IMPORTS,
            "outside_file_attempts_safe_metadata": OUTSIDE_FILE_METADATA,
            "plugin_instance_created": PLUGIN_INSTANCE_CREATED,
        }
    finally:
        loop.close()
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
