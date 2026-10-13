"""The mechanism behind the "no leftover paid session" rule.

Last night's cost overrun was not a bad decision, it was an unbounded background
session: a launcher started with a looping fake microphone kept asking questions for
18 minutes and spent the remaining paid allowance. The instruction "don't leave drivers
running" is worthless without something that can answer, in one command, "is anything
running right now, and what did it spend?".

    python scripts/neko_session_guard.py check                 # exit 3 if a session is alive
    python scripts/neko_session_guard.py save before.json      # ledger + processes snapshot
    python scripts/neko_session_guard.py diff before.json      # what was spent since
    python scripts/neko_session_guard.py stop                  # kill only what it recognises

Ownership is a command-line signature, never a port or a name prefix: the launcher, the
host, the native shell, and any Chromium fed `--use-file-for-fake-audio-capture` (the flag
that replays a wav forever). Anything else on the machine is not touched, and the process
is refused if it cannot be matched. `psutil` gives pid + create_time pairs, so a recycled
pid from an unrelated program cannot be killed by accident.

No monitoring platform, no daemon, no scheduled job - this is a question you ask and an
answer you can put in a report.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
HOST_LOG = ROOT / "benchmarks/raw/neko-desktop-host.log"
BROWSER_OWNER_FILE = ROOT / "benchmarks/raw/neko-desktop-browser-owner.json"

SIGNATURES = (
    "neko_tutor_start.py",
    "neko_desktop_tutor_host.py",
    "neko_native_shell.py",
    "neko_loopback_meter.py",
    "use-file-for-fake-audio-capture",
)


def session_processes() -> list[dict]:
    """Every process this project started that can spend money, with its identity."""
    import psutil

    found = []
    for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(process.info["cmdline"] or [])
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if not cmdline or not any(signal in cmdline for signal in SIGNATURES):
            continue
        if "neko_session_guard" in cmdline:  # never match the tool doing the asking
            continue
        found.append({"pid": process.info["pid"], "name": process.info["name"],
                      "created_at": process.info["create_time"],
                      "matched": [s for s in SIGNATURES if s in cmdline],
                      "cmdline": cmdline[:400]})
    return found


def ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def log_mtime() -> float:
    try:
        return HOST_LOG.stat().st_mtime
    except OSError:
        return 0.0


def snapshot() -> dict:
    return {"taken_at": time.time(), "ledger": ledger(), "host_log_mtime": log_mtime(),
            "processes": session_processes()}


def kill(processes: list[dict]) -> list[int]:
    """Terminate children before parents, then confirm each identity is gone."""
    import psutil

    targets = []
    for entry in sorted(processes, key=lambda item: -item["created_at"]):
        try:
            process = psutil.Process(entry["pid"])
            if abs(process.create_time() - entry["created_at"]) > 1.0:
                continue  # the pid was recycled by something unrelated
        except psutil.NoSuchProcess:
            continue
        targets.extend([*process.children(recursive=True), process])
    seen, ordered = set(), []
    for process in reversed(targets):
        if process.pid not in seen:
            seen.add(process.pid)
            ordered.append(process)
    for process in ordered:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(ordered, timeout=8)
    for process in remaining:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(remaining, timeout=8)
    return [process.pid for process in remaining]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("check", "save", "diff", "stop"))
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()

    if args.action == "check":
        state = snapshot()
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 3 if state["processes"] else 0

    if args.action == "save":
        if args.file is None:
            parser.error("save needs a path")
        args.file.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"saved {args.file}")
        return 0

    if args.action == "diff":
        if args.file is None:
            parser.error("diff needs a path")
        before = json.loads(args.file.read_text(encoding="utf-8"))
        now = snapshot()
        spent = {}
        for host, count in (now["ledger"].get("spent") or {}).items():
            delta = count - ((before["ledger"].get("spent") or {}).get(host) or 0)
            if delta:
                spent[host] = {"before": (before["ledger"].get("spent") or {}).get(host),
                               "after": count, "delta": delta}
        print(json.dumps({"spent_since_snapshot": spent,
                          "budgets": (now["ledger"].get("budgets") or {}),
                          "round": now["ledger"].get("round"),
                          "processes_now": [entry["pid"] for entry in now["processes"]]},
                         ensure_ascii=False, indent=2))
        return 0

    # stop
    processes = session_processes()
    if not processes:
        print(json.dumps({"stopped": [], "note": "nothing recognised as a paid session"}))
        return 0
    stuck = kill(processes)
    time.sleep(2.0)
    settled = log_mtime()
    time.sleep(3.0)
    still_writing = log_mtime() > settled
    left = session_processes()
    print(json.dumps({"asked": [entry["pid"] for entry in processes], "stuck": stuck,
                      "left_over": [entry["pid"] for entry in left],
                      "host_log_still_advancing": still_writing}, ensure_ascii=False, indent=2))
    return 4 if (left or stuck or still_writing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
