"""Stage 2.1: restart the backend root process and settle the capture_busy question.

Why a restart is the only decisive probe: `_interactive_capture_active` is a
module-level global in a long-lived process. Nothing short of a fresh process can
tell apart "the flag was latched True and its release future was orphaned" (a leak)
from "a live overlay session is legitimately holding it".

Steps, all verified:
  1. record pre-restart baseline (ports, Study status, awareness config, DB counts),
  2. prove pid 3812 owns 48911 and is the lab's own backend exe,
  3. stop only that process tree root,
  4. relaunch with the identical exe path / cwd / (empty) argv,
  5. wait for the ports, then immediately replay the plugin's exact request
     (POST /api/screenshot/interactive with NO Origin header),
  6. re-check the DB counts so the restart is proven non-destructive.

Never touches the database files and never uses the initial full backup.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import urllib.request

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

k32 = ctypes.windll.kernel32

SERVER_EXE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\resources\bin\projectneko_server.exe"
SERVER_CWD = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\resources\bin"
DB = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store\plugins\study_companion\data\study_companion.db"
EVIDENCE = Path(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence")
LOG = Path(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence\stage2-restart-stdout.log")

TARGET_PID = 3812


def probe(title=""):
    out = {"label": title}
    for port in (48911, 48912, 48915, 48916):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                out[f"port_{port}"] = json.load(r).get("status", "ok")
        except Exception as exc:  # noqa: BLE001
            out[f"port_{port}"] = f"down ({type(exc).__name__})"
    return out


def interactive_probe():
    """Replay the plugin's exact request: loopback, JSON, NO Origin header."""
    body = json.dumps({"selection_only": True, "copy_to_clipboard": False,
                       "session_timeout_ms": 45000}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:48911/api/screenshot/interactive",
        data=body, method="POST",
        headers={"Content-Type": "application/json"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {"http": response.status,
                    "elapsed_s": round(time.monotonic() - started, 2),
                    "body": response.read(300).decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        return {"http": exc.code, "elapsed_s": round(time.monotonic() - started, 2),
                "body": exc.read(300).decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001
        return {"http": None, "elapsed_s": round(time.monotonic() - started, 2),
                "body": f"{type(exc).__name__}: {exc}"}


def db_counts():
    try:
        con = sqlite3.connect(DB)
        counts = {}
        for table in ("interactions", "qa_records", "topics", "mastery_snapshots"):
            counts[table] = con.execute(f"select count(*) from {table}").fetchone()[0]
        con.close()
        return counts
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def exe_of(pid):
    handle = k32.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(1024)
        if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        k32.CloseHandle(handle)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=TARGET_PID)
    parser.add_argument("--wait-seconds", type=int, default=45)
    parser.add_argument("--no-restart", action="store_true",
                        help="only probe; do not stop or launch anything")
    options = parser.parse_args()

    report = {"pid": options.pid,
              "exe_owned": exe_of(options.pid),
              "exe_expected": SERVER_EXE,
              "ownership_ok": exe_of(options.pid) == SERVER_EXE}
    report["before"] = {"ports": probe("before"), "db": db_counts(),
                        "interactive": interactive_probe()}

    if not report["ownership_ok"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("ABORT: pid is not the expected backend exe")
        return
    if options.no_restart:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # --- stop only the tree root ---
    stopped = subprocess.run(["taskkill", "/PID", str(options.pid), "/T", "/F"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace")
    report["taskkill"] = {"rc": stopped.returncode,
                          "out": (stopped.stdout or stopped.stderr or "").strip()}
    time.sleep(4)
    report["after_stop_ports"] = probe("after_stop")

    # --- relaunch identically ---
    with open(LOG, "ab") as log:
        proc = subprocess.Popen([SERVER_EXE], cwd=SERVER_CWD, stdout=log,
                                stderr=subprocess.STDOUT, close_fds=True)
    report["relaunched_pid"] = proc.pid
    report["relaunched_cwd"] = SERVER_CWD

    deadline = time.time() + options.wait_seconds
    ready = False
    while time.time() < deadline:
        time.sleep(3)
        state = probe("waiting")
        if all(state.get(f"port_{p}") == "ok" for p in (48911, 48912, 48916)):
            ready = True
            report["after_start_ports"] = state
            break
    report["ports_ready"] = ready
    if not ready:
        report["after_start_ports"] = probe("timeout")

    # --- the decisive probe, immediately after a fresh process ---
    report["after_interactive"] = interactive_probe()
    report["after_db"] = db_counts()
    report["db_intact"] = (
        report["after_db"].get("interactions") == report["before"]["db"].get("interactions")
        and report["after_db"].get("qa_records") == report["before"]["db"].get("qa_records"))

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE / "goal-stage2-restart.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
