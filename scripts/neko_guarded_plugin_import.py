"""Guarded import-only probe for the extracted Study Companion package.

Run with the project-local venv: python -I -B scripts/neko_guarded_plugin_import.py
The probe imports the package/class only; it never constructs plugin or host objects.
"""
from __future__ import annotations

import builtins
import hashlib
import importlib
import io
import json
import logging
import multiprocessing
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import types


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "candidates" / "N.E.K.O"
RELEASE = ROOT / "benchmarks" / "raw" / "neko-app" / "resources" / "bin"
TEMP_ROOT = ROOT / ".tmp-uv-cache"
COUNTS = {
    "process_attempts": 0,
    "network_attempts": 0,
    "database_attempts": 0,
    "outside_file_attempts": 0,
    "file_write_attempts": 0,
    "directory_write_attempts": 0,
    "get_plugins_directory_calls": 0,
}
BLOCKED_IMPORTS: list[str] = []
OUTSIDE_FILE_METADATA: list[dict[str, object]] = []


def _blocked_process(*_args, **_kwargs):
    COUNTS["process_attempts"] += 1
    raise RuntimeError("process creation blocked by guarded import")


def _blocked_network(*_args, **_kwargs):
    COUNTS["network_attempts"] += 1
    raise RuntimeError("network operation blocked by guarded import")


def _blocked_database(*_args, **_kwargs):
    COUNTS["database_attempts"] += 1
    raise RuntimeError("database access blocked by guarded import")


def _blocked_directory_write(*_args, **_kwargs):
    COUNTS["directory_write_attempts"] += 1
    raise RuntimeError("directory creation blocked by guarded import")


def _install_guards() -> None:
    sys.path[:0] = [str(CANDIDATE), str(RELEASE)]
    sys.dont_write_bytecode = True
    tempfile.tempdir = str(TEMP_ROOT)

    # Keep imports quiet and prevent the app logger from creating a file sink.
    logging.getLogger("N.E.K.O.Plugin").addHandler(logging.NullHandler())
    logging.getLogger().addHandler(logging.NullHandler())

    # The plugin's import chain needs only these config-manager symbols. The real
    # get_plugins_directory creates a user directory, so this stub returns an
    # inert ignored-project path and deliberately does not mkdir it.
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
    config_stub.get_config_manager = lambda: InMemoryConfigManager()

    def inert_plugins_directory(*_args, **_kwargs):
        COUNTS["get_plugins_directory_calls"] += 1
        return TEMP_ROOT / "neko-plugin-import-only"

    config_stub.get_plugins_directory = inert_plugins_directory
    sys.modules["utils.config_manager"] = config_stub
    utils.config_manager = config_stub

    # Preserve Popen's class identity for asyncio.windows_utils subclassing.
    real_popen = subprocess.Popen

    class BlockedPopen(real_popen):
        def __init__(self, *_args, **_kwargs):
            _blocked_process()

    subprocess.Popen = BlockedPopen
    for name in ("run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        setattr(subprocess, name, _blocked_process)
    for name in ("system", "popen", "startfile"):
        if hasattr(os, name):
            setattr(os, name, _blocked_process)
    for name in dir(os):
        if name.startswith(("spawn", "exec")) and callable(getattr(os, name, None)):
            setattr(os, name, _blocked_process)
    multiprocessing.process.BaseProcess.start = _blocked_process

    # Import this after the Popen guard; the subclass-based guard must remain
    # compatible with asyncio's standard-library subclass declarations.
    import asyncio.windows_utils  # noqa: F401

    real_socket = socket.socket

    class BlockedSocket(real_socket):
        def __init__(self, *_args, **_kwargs):
            COUNTS["network_attempts"] += 1
            raise RuntimeError("socket creation blocked by guarded import")

    socket.socket = BlockedSocket
    socket.create_connection = _blocked_network
    socket.getaddrinfo = _blocked_network
    socket.gethostbyname = _blocked_network
    sqlite3.connect = _blocked_database
    sqlite3.dbapi2.connect = _blocked_database

    allowed_roots = tuple(
        path.resolve()
        for path in (CANDIDATE, RELEASE, TEMP_ROOT, Path(sys.prefix), Path(sys.base_prefix))
    )

    def check_file(path, mode: str) -> None:
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            COUNTS["file_write_attempts"] += 1
            raise RuntimeError("file writes blocked by guarded import")
        try:
            resolved = Path(os.fspath(path)).resolve()
        except Exception:
            COUNTS["outside_file_attempts"] += 1
            raise RuntimeError("file access blocked by guarded import") from None
        if not any(resolved == root or root in resolved.parents for root in allowed_roots):
            COUNTS["outside_file_attempts"] += 1
            try:
                home = Path.home().resolve()
                path_class = "user_profile" if resolved == home or home in resolved.parents else "outside_allowed_roots"
            except Exception:
                path_class = "outside_allowed_roots"
            suffix = resolved.suffix.lower()
            suffix_class = "config_or_data" if suffix in {".json", ".toml", ".yaml", ".yml", ".db", ".sqlite", ".sqlite3"} else "other"
            stack = []
            frame = sys._getframe(1)
            while frame is not None and len(stack) < 8:
                module = str(frame.f_globals.get("__name__", "unknown"))
                stack.append({"module": module, "function": frame.f_code.co_name})
                frame = frame.f_back
            OUTSIDE_FILE_METADATA.append({
                "path_class": path_class,
                "suffix_class": suffix_class,
                "stack_inner_to_outer": stack,
            })
            raise RuntimeError("outside file access blocked by guarded import")

    real_builtin_open, real_io_open = builtins.open, io.open
    real_path_open, real_os_open = Path.open, os.open

    def guarded_builtin_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        check_file(file, mode)
        return real_builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def guarded_io_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        check_file(file, mode)
        return real_io_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def guarded_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        check_file(self, mode)
        return real_path_open(self, mode, buffering, encoding, errors, newline)

    def guarded_os_open(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            COUNTS["file_write_attempts"] += 1
            raise RuntimeError("file writes blocked by guarded import")
        check_file(file, "r")
        return real_os_open(file, flags, *args, **kwargs)

    builtins.open = guarded_builtin_open
    io.open = guarded_io_open
    Path.open = guarded_path_open
    os.open = guarded_os_open
    os.mkdir = _blocked_directory_write
    os.makedirs = _blocked_directory_write
    Path.mkdir = _blocked_directory_write

    blocked_prefixes = (
        "openai", "anthropic", "dashscope", "google.genai", "google.generativeai",
        "main_logic.tts_client", "main_logic.asr_client", "utils.tts", "utils.audio",
        "utils.audio_processor", "utils.screenshot_utils", "utils.desktop_capture",
        "av", "soxr", "pyrnnoise", "sounddevice", "pyaudio", "winsound", "dxcam",
        "mss", "pyautogui", "pynput", "screeninfo", "PIL.ImageGrab", "win32gui",
        "win32api", "pytesseract", "rapidocr_onnxruntime", "onnxruntime",
    )

    class ImportBlocker:
        def find_spec(self, fullname, path=None, target=None):
            if any(fullname == prefix or fullname.startswith(prefix + ".") for prefix in blocked_prefixes):
                BLOCKED_IMPORTS.append(fullname)
                raise ImportError("guarded import blocked: " + fullname)

    sys.meta_path.insert(0, ImportBlocker())


def main() -> None:
    _install_guards()
    started = time.perf_counter()
    try:
        package = importlib.import_module("plugins.study_companion")
        plugin_class = package.StudyCompanionPlugin
        result = {
            "status": "PASS_IMPORT_ONLY",
            "module": package.__name__,
            "class": plugin_class.__qualname__,
            "class_module": plugin_class.__module__,
            "source_file": str(Path(package.__file__).resolve()),
            "source_sha256": hashlib.sha256(Path(package.__file__).read_bytes()).hexdigest(),
        }
    except BaseException as exc:
        result = {
            "status": "BLOCKED_OR_FAILED_IMPORT_ONLY",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
        }
    result.update(
        {
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            "guards": COUNTS,
            "blocked_imports": BLOCKED_IMPORTS,
            "outside_file_attempts_safe_metadata": OUTSIDE_FILE_METADATA,
            "plugin_instantiated": False,
            "host_initialized": False,
            "database_opened": False,
            "provider_called": False,
            "socket_connected": False,
            "process_started": False,
        }
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
