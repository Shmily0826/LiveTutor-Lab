"""Two real Study backend calls on existing isolated history; no audio/Native."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import time

import neko_desktop_tutor_host as host
from neko_daily_voice_probe import stop_owned_host
from neko_lab_client import LabClient
from neko_tutor_start import plugin_server_ready

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks/raw/neko-desktop-egress-cap"


def snapshot(db):
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5) as connection:
        connection.execute("PRAGMA query_only=ON")
        state = json.loads(connection.execute("SELECT value FROM kv WHERE key='state'").fetchone()[0])
        # Retain actual rows locally, so unchanged prior history can be checked.
        interactions = connection.execute("SELECT * FROM interactions ORDER BY id").fetchall()
        qa = connection.execute("SELECT * FROM qa_records ORDER BY id").fetchall()
        return {"course_id": state.get("study_course_id"), "session_id": state.get("study_session_id"),
                "interactions": interactions, "qa": qa}


def main(args):
    store = (ROOT / "benchmarks/raw" / args.store).resolve()
    output = args.output.resolve()
    if (not args.store.startswith("neko-daily-speech-acceptance-")
            or not store.is_relative_to(ROOT / "benchmarks/raw")
            or not output.is_relative_to(ROOT / "benchmarks/raw/evidence")
            or output.exists()):
        raise ValueError("existing isolated speech history only; unique raw evidence path required")
    db = store / "N.E.K.O/plugins/study_companion/data/study_companion.db"
    if not db.is_file():
        raise ValueError("existing history is missing; do not create synthetic learning records")
    before = snapshot(db.resolve())
    if not before["qa"]:
        raise ValueError("this check needs a prior real graded question")
    source_question = ""
    if not args.summary_only:
        if args.source_question is None:
            raise ValueError("source question is required for the two-call mode")
        question_path = args.source_question.resolve(strict=True)
        if not question_path.is_relative_to(ROOT / "benchmarks/raw/evidence"):
            raise ValueError("source question must be the prepared public-source evidence")
        source_question = question_path.read_text(encoding="utf-8")
        if not source_question.strip() or len(source_question) > 8000:
            raise ValueError("bounded source question is required before any model launch")
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("existing host occupies the ports; leave it running")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if ledger["round"] != "bargein-autocheck-20261012" or ledger["spent"].get("api.deepseek.com", 0) >= 2000:
        raise RuntimeError("shared round/cap prevents this line; never reset it")
    report = {"before_ledger": ledger, "before_database": before, "calls": [],
              "room_microphone": False, "native_window": False, "audio_session": False,
              "scope": "real Study SDK/backend and existing SQLite history; no Native/device/human proof"}
    if source_question:
        report["source_question_sha256"] = hashlib.sha256(question_path.read_bytes()).hexdigest()
    report["summary_only"] = args.summary_only
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_suffix(".host.log").open("wb")
    process = subprocess.Popen([str(host.SOURCE_PYTHON), "-X", "utf8",
        str(ROOT / "scripts/neko_desktop_tutor_host.py"), "--source", "--core-provider", "free",
        "--store", args.store, "--hold", "300", "--seconds", "100", "--api-budget", "10",
        "--egress-budget", "2000", "--allow-host", "www.lanlan.app:unlimited",
        "--allow-host", "www.lanlan.tech:0", "--budget-round", "bargein-autocheck-20261012"],
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}, stdout=log, stderr=subprocess.STDOUT)
    report["host_launcher_pid"] = process.pid

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        ready, reason = plugin_server_ready(100, process)
        if not ready:
            raise RuntimeError("host not ready: " + reason)
        client = LabClient()
        requests = [("study_summarize_session", {"focus": "用两句话回顾上一轮题目、我的错答与正确方向，以及下一步。不出新题。"})]
        if source_question:
            requests.append(("study_explain_text", {"text": source_question}))
        for entry, arguments in requests:
            started = time.time()
            row = {"entry": entry, "arguments": arguments, "started_wall": started}
            report["calls"].append(row); save()
            row["result"] = client.call(entry, arguments, timeout=120)
            row["completed_wall"] = time.time(); save()
            data = row["result"]["data"]
            if data.get("degraded") or data.get("status") == "unavailable":
                raise RuntimeError("real model unavailable; stop without retrying")
        report["after_database"] = snapshot(db.resolve())
        after = report["after_database"]
        report["checks"] = {
            "previous_interactions_unchanged": after["interactions"][:len(before["interactions"])] == before["interactions"],
            "previous_grades_unchanged": after["qa"] == before["qa"],
            "same_course": after["course_id"] == before["course_id"],
            "expected_real_backend_results": len(report["calls"]) == len(requests),
        }
    except Exception as error:
        # An observation timeout is not a claim that its existing run terminated.
        report["failure"] = type(error).__name__ + ": " + str(error)
        report["observation_timeout"] = isinstance(error, TimeoutError)
    finally:
        stop_owned_host(process); log.close()
        report["after_ledger"] = json.loads(LEDGER.read_text(encoding="utf-8"))
        report["result"] = ("BACKEND_FAILURE" if report.get("failure")
                            else "BACKEND_CALLS_COMPLETED_REQUIRES_SEMANTIC_REVIEW")
        report["finalized"] = True; save()
        print(json.dumps({"report": str(output), "failure": report.get("failure"),
            "checks": report.get("checks"), "spent": report["after_ledger"]["spent"],
            "responses": [call.get("result", {}).get("data", {}) for call in report["calls"]]}, ensure_ascii=False), flush=True)
    return 1 if report.get("failure") or not all(report.get("checks", {}).values()) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-question", type=Path)
    parser.add_argument("--summary-only", action="store_true", help="one changed summary check; skip the already-passed source explanation")
    raise SystemExit(main(parser.parse_args()))
