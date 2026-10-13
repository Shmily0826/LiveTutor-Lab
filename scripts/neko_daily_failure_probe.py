"""Bounded local HTTP failure stub and existing-host recovery probe.

This script never starts/stops a host, model provider, avatar or audio session.
The main agent reviews launch-plan, starts an isolated text-only host separately,
then explicitly runs the probe. Only newly created fixture storage is permitted.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "benchmarks/raw"
GLOBAL_LEDGER = RAW / "neko-desktop-egress-cap"
DUMMY_KEY = "sk-neko-local-fixture-only-20261014"
KIND = "neko-local-failure-fixture-v1"
MODES = {"http503", "drop", "question", "answer", "explain", "summary"}
TRACKED_TABLES = ("interactions", "qa_records", "mastery_snapshots", "wrong_questions", "fsrs_cards")


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def local_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("fixture URL must be plain loopback HTTP")
    return value.rstrip("/")


class FailureStub(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *, port=0, maximum_requests=16):
        self.token = secrets.token_urlsafe(32)
        self.mode = "http503"
        self.maximum_requests = maximum_requests
        self.records = []
        self.unexpected_credential = False
        self.lock = threading.Lock()
        super().__init__(("127.0.0.1", port), FailureHandler)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server_port}"

    def state(self):
        with self.lock:
            return {"kind": KIND, "mode": self.mode, "records": list(self.records),
                    "unexpected_credential": self.unexpected_credential,
                    "maximum_requests": self.maximum_requests}


class FailureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if status == 429:
            self.send_header("Retry-After", "3600")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            self.reply({"error": "loopback host required"}, 403)
            return False
        if not secrets.compare_digest(self.headers.get("X-Failure-Fixture-Token", ""), self.server.token):
            self.reply({"error": "fixture token required"}, 403)
            return False
        return True

    def do_GET(self):
        if self.path == "/health":
            self.reply({"kind": KIND})
        elif self.path == "/control/state":
            if self.authorized():
                self.reply(self.server.state())
        else:
            self.reply({"error": "not found"}, 404)

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in {"/control/mode", "/v1/chat/completions"}:
            self.reply({"error": "not found"}, 404)
            return
        if route.startswith("/control/") and not self.authorized():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 256 * 1024:
                raise ValueError("request must be bounded")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("request must be an object")
        except (ValueError, TypeError):
            self.reply({"error": "invalid request"}, 400)
            return
        if route == "/control/mode":
            if payload.get("mode") not in MODES:
                self.reply({"error": "unsupported fixture mode"}, 400)
                return
            with self.server.lock:
                self.server.mode = payload["mode"]
            self.reply(self.server.state())
            return
        # Never save headers or credentials. A non-dummy credential is refused.
        if not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + DUMMY_KEY):
            self.server.unexpected_credential = True
            self.reply({"error": {"message": "fixture requires its dummy credential", "code": "fixture_auth_refused"}}, 401)
            return
        with self.server.lock:
            if len(self.server.records) >= self.server.maximum_requests:
                self.reply({"error": {"message": "fixture request limit reached", "code": "fixture_limit"}}, 429)
                return
            mode = self.server.mode
            record_id = len(self.server.records) + 1
            self.server.records.append({"id": record_id, "mode": mode,
                "request_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                "message_count": len(payload.get("messages", [])), "dummy_credential_verified": True,
                "at": datetime.now(timezone.utc).isoformat()})
        if mode == "http503":
            self.reply({"error": {"message": "deliberate local fixture HTTP 503", "code": "fixture_unavailable"}}, 503)
        elif mode == "drop":
            self.connection.close()
            self.close_connection = True
        else:
            values = {
                "question": {"question": "【本地故障量具】函数参数有什么作用？", "answer": "函数的输入",
                    "accepted_answers": ["函数的输入"], "key_points": ["输入"], "question_type": "short_answer",
                    "hint": "这是协议测试，不是真实模型教学。", "topic": "local-failure-fixture", "difficulty": 1},
                "answer": {"verdict": "correct", "score": 100, "feedback": "【本地 HTTP stub】仅验证评分通道恢复。",
                    "error_type": "none", "next_action": "finish protocol test", "reference_answer": "函数的输入",
                    "covered_points": ["输入"], "missing_points": [], "misconceptions": []},
                "explain": "【本地 HTTP stub】连接已恢复；这是协议量具回复，不是真实模型教学。",
                "summary": {"summary": "【本地 HTTP stub】已练习函数输入；仅验证总结通道。",
                    "markdown": "本地协议量具：函数参数是函数接收的输入。", "highlights": ["函数输入"],
                    "weak_points": [], "next_actions": ["结束本地协议测试"]},
            }
            value = values[mode]
            content = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
            self.reply({"id": f"local-fixture-{record_id}", "object": "chat.completion", "created": int(time.time()),
                "model": payload.get("model", "local-fixture"), "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


def json_request(url, *, data=None, token="", timeout=15):
    local_url(url)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Failure-Fixture-Token"] = token
    opener = build_opener(ProxyHandler({}))
    request = Request(url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def load_manifest(path):
    path = Path(path).resolve(strict=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    store = Path(value["store"]).resolve(strict=True)
    if not store.is_relative_to(RAW.resolve()) or not store.name.startswith("neko-failure-") or path.parent != store:
        raise ValueError("only a new project failure-fixture store is permitted")
    marker = json.loads((store / "failure-fixture-owner.json").read_text(encoding="utf-8"))
    if value.get("kind") != KIND or marker.get("kind") != KIND or marker.get("nonce") != value.get("nonce"):
        raise ValueError("fixture ownership marker mismatch")
    local_url(value["stub_url"])
    return value


def launch_plan(manifest, *, hold=240):
    """Return argv for main-agent review; never execute it."""
    store = Path(manifest["store"])
    code = (
        "import sys; from pathlib import Path; sys.path.insert(0,'scripts'); import neko_desktop_tutor_host as h; "
        f"h.MODEL_URL={manifest['stub_url'] + '/v1'!r}; h.read_key=lambda:{DUMMY_KEY!r}; "
        "h.apply_voice_host_patch=lambda:'kept existing patches; local failure fixture'; original_sink=h.Sink; "
        f"h.Sink=lambda *a,**k:original_sink(0,extra={{}},cap_file=Path({str(store / 'local-deny-egress.json')!r}),round_id='local-fixture-no-external'); "
        "sys.argv=['neko_desktop_tutor_host.py','--source','--store',"
        f"{store.name!r},'--egress-budget','0','--api-budget','24','--hold',{str(hold)!r},'--seconds','1']; "
        "raise SystemExit(h.main())"
    )
    python = RAW / "neko-product-host/.venv/Scripts/python.exe"
    return {"cwd": str(ROOT), "argv": [str(python), "-X", "utf8", "-c", code],
            "environment": {"PYTHONIOENCODING": "utf-8"},
            "warning": "Main agent only: check host ports are free, run reviewed argv, record ownership and clean that host afterward.",
            "no_external_provider": True, "global_ledger_sha256_before_host": manifest["global_ledger_sha256"]}


def database_snapshot(db):
    db = Path(db).resolve(strict=True)
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
        connection.execute("PRAGMA query_only=ON")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in TRACKED_TABLES if table in tables}
        row = connection.execute("SELECT value FROM kv WHERE key='state'").fetchone()
        state = json.loads(row[0]) if row else {}
        question = dict(state.get("current_question") or {})
        return {"counts": counts, "current_question": question,
                "course_id": state.get("study_course_id", "general"),
                "last_error": state.get("last_error", "")}


def assert_failed_teaching(data, *, operation):
    if not data.get("degraded") or data.get("status") != "unavailable":
        raise AssertionError(f"{operation}: provider failure was not marked unavailable")
    if any(key in data for key in ("question", "question_id", "attempt_id", "score", "verdict")):
        raise AssertionError(f"{operation}: failure exposed a question or grade")
    if not data.get("diagnostic") or not data.get("reply"):
        raise AssertionError(f"{operation}: failure lacks diagnostic or honest reply")


def run_probe(options):
    from neko_lab_client import LabClient
    manifest = load_manifest(options.manifest)
    store = Path(manifest["store"])
    db = options.db.resolve(strict=True)
    if not db.is_relative_to(store) or db.name != "study_companion.db":
        raise ValueError("DB must be this fixture store's actual Study database")
    if options.output.exists():
        raise ValueError("keep old evidence; use a new output path")
    output_path = options.output.resolve()
    if not output_path.is_relative_to((RAW / "evidence").resolve()) and not output_path.is_relative_to(store):
        raise ValueError("evidence output must stay in this fixture store or project raw/evidence")
    core = json.loads((store / "N.E.K.O/config/core_config.json").read_text(encoding="utf-8"))
    if core.get("agentModelUrl") != manifest["stub_url"] + "/v1" or any(core.get(key) != DUMMY_KEY for key in ("agentModelApiKey", "assistApiKeyDeepseek", "coreApiKeyDeepseek")):
        raise ValueError("isolated model configuration is not the dummy-key loopback fixture")
    if file_sha256(GLOBAL_LEDGER) != manifest["global_ledger_sha256"]:
        raise ValueError("shared ledger changed since fixture preparation; review before proceeding")
    before = database_snapshot(db)
    if before["counts"].get("interactions") != 0 or before["counts"].get("qa_records", 0) != 0 or before["current_question"]:
        raise ValueError("probe requires a fresh empty learning DB; never reuse learner history")
    base = f"http://127.0.0.1:{options.plugin_port}"
    client = LabClient(port=options.plugin_port)
    report = {"proof": "real plugin/SDK/DB with local HTTP stub; no real model or playback claim",
              "store": store.name, "steps": [], "db_before": before, "global_ledger_sha256_before": file_sha256(GLOBAL_LEDGER)}
    token = manifest["token"]

    def save():
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def mode(value):
        json_request(manifest["stub_url"] + "/control/mode", data={"mode": value}, token=token)

    def callback(name, fields):
        body = {"name": name, "arguments": fields, "raw_arguments": json.dumps(fields),
                "call_id": "local_failure_" + secrets.token_hex(6)}
        result = json_request(base + f"/api/llm-tools/callback/study_companion/{name}", data=body, timeout=90)
        report["steps"].append({"tool": name, "result": result, "database": database_snapshot(db)})
        save()
        if result.get("is_error"):
            raise AssertionError(f"callback {name} did not produce the teaching failure contract")
        return result.get("output", {})

    try:
        status = client.call("study_status", timeout=30)["data"]
        observed_course = str(status.get("study_course_id") or (status.get("state") or {}).get("study_course_id") or "general")
        if observed_course != str(before["course_id"] or "general"):
            raise ValueError("running host does not match this fresh fixture DB")
        fixture_state = json_request(manifest["stub_url"] + "/control/state", token=token)
        if fixture_state["records"] or fixture_state["unexpected_credential"]:
            raise ValueError("fixture already received model traffic; investigate instead of repeating")
        client.call("study_update_settings_config", {"config": {"communication": {"enabled": False}, "ocr_reader": {"enabled": False}, "awareness": {"enabled": False}}})
        course = "local-failure-" + manifest["nonce"][:12]
        client.call("study_start_session", {"course_id": course})
        mode("question")
        generated = client.call("study_generate_question", {"text": "本地协议量具：函数参数是函数接收的输入。", "topic": "local-failure-fixture"})
        report["steps"].append({"entry": "study_generate_question", "result": generated, "database": database_snapshot(db)})
        save()
        question = generated["data"]
        if question.get("degraded") or not question.get("attempt_id") or not question.get("question_id"):
            raise AssertionError("local stub did not create a genuine pending attempt in Study")
        baseline = database_snapshot(db)
        mode("http503")
        for name, fields in (("study_explain", {"text": "函数参数是函数接收的输入。", "question": "简短解释这段材料"}),
                             ("study_quiz", {"topic": "local-failure-fixture", "target_weak": False}),
                             ("study_answer", {"answer": "函数的输入"})):
            failed = callback(name, fields)
            assert_failed_teaching(failed, operation=name)
            snap = database_snapshot(db)
            if snap["counts"] != baseline["counts"]:
                raise AssertionError(f"{name}: degraded output changed teaching/grade DB counts")
            if snap["current_question"].get("attempt_id") != question["attempt_id"] or snap["current_question"].get("attempt_evaluated") or snap["current_question"].get("attempt_evaluation_pending"):
                raise AssertionError(f"{name}: pending question lost, consumed, or left reserved")
        mode("answer")
        recovered = callback("study_answer", {"answer": "函数的输入"})
        after_grade = database_snapshot(db)
        if recovered.get("degraded") or recovered.get("score") != 100 or not after_grade["current_question"].get("attempt_evaluated") or after_grade["counts"].get("qa_records", 0) != baseline["counts"].get("qa_records", 0) + 1:
            raise AssertionError("restored same attempt did not score exactly once in DB")
        mode("explain")
        explained = callback("study_explain", {"text": "函数参数是函数接收的输入。", "question": "恢复后简短解释"})
        if explained.get("degraded") or "本地 HTTP stub" not in explained.get("reply", ""):
            raise AssertionError("after recovery the plugin could not accept a new explanation")
        report["result"] = "PASS_REAL_BACKEND_LOCAL_STUB"
    except Exception as exc:
        report["result"] = "FAIL"
        report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        try:
            mode("http503")
            report["stub"] = json_request(manifest["stub_url"] + "/control/state", token=token)
        except Exception as exc:
            report["stub"] = {"records": [], "unexpected_credential": False, "error": type(exc).__name__}
            report["result"] = "FAIL"
        try:
            report["db_after"] = database_snapshot(db)
        except Exception as exc:
            report["db_after"] = {"error": type(exc).__name__}
            report["result"] = "FAIL"
        report["global_ledger_sha256_after"] = file_sha256(GLOBAL_LEDGER)
        report["global_ledger_unchanged"] = report["global_ledger_sha256_after"] == report["global_ledger_sha256_before"]
        if not report["global_ledger_unchanged"] or report["stub"]["unexpected_credential"]:
            report["result"] = "FAIL"
        save()
    print(json.dumps({"output": str(options.output), "result": report["result"],
                      "stub_requests": len(report["stub"]["records"]), "global_ledger_unchanged": report["global_ledger_unchanged"]}, ensure_ascii=True))
    return 0 if report["result"] == "PASS_REAL_BACKEND_LOCAL_STUB" else 1


def serve(options):
    if not options.store_name.startswith("neko-failure-") or Path(options.store_name).name != options.store_name:
        raise ValueError("new store name must start neko-failure- and contain no path")
    store = RAW / options.store_name
    store.mkdir(exist_ok=False)
    stub = FailureStub(port=options.port)
    nonce = secrets.token_hex(16)
    manifest = {"kind": KIND, "nonce": nonce, "store": str(store.resolve()), "stub_url": stub.base_url,
                "token": stub.token, "stub_pid": os.getpid(), "global_ledger_sha256": file_sha256(GLOBAL_LEDGER)}
    (store / "failure-fixture-owner.json").write_text(json.dumps({"kind": KIND, "nonce": nonce}), encoding="utf-8")
    path = store / "failure-stub-manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    thread = threading.Thread(target=stub.serve_forever, daemon=True)
    thread.start()
    print(json.dumps({"manifest": str(path), "stub_url": stub.base_url, "stub_pid": os.getpid(), "expires_seconds": options.hold}), flush=True)
    try:
        threading.Event().wait(options.hold)
    except KeyboardInterrupt:
        pass
    finally:
        stub.shutdown()
        stub.server_close()
        thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stub = commands.add_parser("serve")
    stub.add_argument("--store-name", required=True)
    stub.add_argument("--port", type=int, default=0)
    stub.add_argument("--hold", type=int, default=300, choices=range(30, 901), metavar="30..900")
    plan = commands.add_parser("launch-plan")
    plan.add_argument("--manifest", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--db", type=Path, required=True)
    run.add_argument("--plugin-port", type=int, default=48916)
    run.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    if options.command == "serve":
        serve(options)
    elif options.command == "launch-plan":
        print(json.dumps(launch_plan(load_manifest(options.manifest)), ensure_ascii=True, indent=2))
    else:
        return run_probe(options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
