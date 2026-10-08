#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Runtime exercise of N.E.K.O's Study Companion plugin through its real
plugin-run API on the user-plugin server (port 48916).

Contract (taken from the shipped plugin UI, static/main.js):
  POST /runs            {"plugin_id","entry_id","args"}   -> run_id
  GET  /runs/{run_id}   poll until status in succeeded/failed/canceled/timeout
  GET  /runs/{run_id}/export -> {"items":[{"type":"json","json":{...}}]}

Everything is read/invoke only against our own lab instance; no product files
are modified.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
MBASE = "http://127.0.0.1:48911"
PLUGIN = "study_companion"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "study-runtime.txt")

os.makedirs(os.path.dirname(EVID), exist_ok=True)
_lines = []


def out(msg=""):
    print(msg)
    _lines.append(str(msg))


def http(base, path, method="GET", data=None, timeout=30):
    url = base + path
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    t = time.time()
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read(), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(), (time.time() - t) * 1000
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode(), (time.time() - t) * 1000


def call(entry, args=None, timeout_s=150, label=None):
    """Invoke a plugin entry; return (ok, data_or_error, elapsed_ms)."""
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    t0 = time.time()
    st, body, _ = http(PBASE, "/runs", "POST",
                       {"plugin_id": PLUGIN, "entry_id": entry, "args": args}, timeout=30)
    if st != 200:
        return False, {"http": st, "body": body[:600].decode("utf-8", "replace")}, (time.time() - t0) * 1000
    try:
        run_id = json.loads(body).get("run_id") or json.loads(body).get("id")
    except Exception:
        return False, {"parse": body[:400].decode("utf-8", "replace")}, (time.time() - t0) * 1000
    if not run_id:
        return False, {"no_run_id": body[:400].decode("utf-8", "replace")}, (time.time() - t0) * 1000

    delay = 0.25
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
        st2, b2, _ = http(PBASE, "/runs/%s" % run_id, "GET", timeout=20)
        if st2 != 200:
            continue
        try:
            rec = json.loads(b2)
        except Exception:
            continue
        last = rec
        status = rec.get("status")
        if status in ("succeeded", "failed", "canceled", "timeout"):
            break
    elapsed = (time.time() - t0) * 1000
    if last.get("status") != "succeeded":
        return False, {"run_status": last.get("status"), "error": last.get("error"),
                       "record": {k: last.get(k) for k in ("status", "message")}}, elapsed

    st3, b3, _ = http(PBASE, "/runs/%s/export" % run_id, "GET", timeout=30)
    if st3 != 200:
        return False, {"export_http": st3}, elapsed
    try:
        payload = json.loads(b3)
    except Exception:
        return False, {"export_parse": b3[:400].decode("utf-8", "replace")}, elapsed
    items = payload.get("items") or []
    for it in items:
        if it.get("type") == "json" and it.get("json"):
            j = it["json"]
            if j.get("success") is False or j.get("error"):
                return False, {"plugin_error": j.get("error") or j.get("message")}, elapsed
            return True, j.get("data") if "data" in j else j, elapsed
    return False, {"no_json_item": [i.get("type") for i in items]}, elapsed


def show(title, ok, data, ms, limit=900):
    out("")
    out("### %s" % title)
    out("    ok=%s  %.0f ms" % (ok, ms))
    if isinstance(data, dict):
        s = json.dumps(data, ensure_ascii=False)
    else:
        s = str(data)
    out("    " + s[:limit].replace("\n", "\n    "))


def main():
    out("=" * 78)
    out("N.E.K.O Study Companion - RUNTIME exercise")
    out("time: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    out("=" * 78)

    # --- 0. environment / provider -------------------------------------
    out("\n--- 0. environment ---")
    st, b, _ = http(PBASE, "/server/info")
    out("  /server/info -> %s %s" % (st, b[:300].decode("utf-8", "replace")))
    st, b, _ = http(PBASE, "/plugin/status")
    out("  /plugin/status -> %s %s" % (st, b[:300].decode("utf-8", "replace")))
    for p in ("/docs",):
        pass
    st, b, _ = http(MBASE, "/api/config/api_providers", timeout=30)
    if st == 200:
        try:
            prov = json.loads(b)
            out("  provider groups: %s" % sorted(prov.keys()))
            out("  default_models: %s" % json.dumps(prov.get("default_models"), ensure_ascii=False)[:400])
        except Exception as e:
            out("  api_providers parse: %s" % e)
    else:
        out("  /api/config/api_providers -> %s" % st)

    cfg = os.path.join(RAW, "neko-store", "config", "core_config.json")
    if os.path.exists(cfg):
        out("  core_config.json: %s" % open(cfg, encoding="utf-8").read().strip())

    steps = []

    # --- 1. baseline status -------------------------------------------
    ok, d, ms = call("study_status", {}, 40)
    show("1. study_status (baseline)", ok, d, ms, 1200)
    steps.append(("study_status", ok, ms))

    # --- 2. set teaching mode -----------------------------------------
    ok, d, ms = call("study_set_mode", {"mode": "teaching", "reason": "ui"}, 40)
    show("2. study_set_mode -> teaching", ok, d, ms)
    steps.append(("study_set_mode", ok, ms))
    mode_after = None
    if ok and isinstance(d, dict):
        mode_after = d.get("mode") or d.get("current_mode")

    # --- 3. concept explanation ----------------------------------------
    q1 = "Explain the chain rule for derivatives, and why we multiply by the derivative of the inner function."
    ok, d, ms = call("study_explain_text", {"text": q1}, 150)
    show("3. study_explain_text (concept explanation)", ok, d, ms, 2500)
    steps.append(("study_explain_text", ok, ms))

    # --- 4. follow-up (adaptation) -------------------------------------
    q2 = "I still don't understand. Can you show it with f(x)=sin(x^2) step by step?"
    ok, d, ms = call("study_explain_text", {"text": q2}, 150)
    show("4. study_explain_text (follow-up / adaptation)", ok, d, ms, 2500)
    steps.append(("study_explain_text_followup", ok, ms))

    # --- 5. learning-state context -------------------------------------
    ok, d, ms = call("study_question_context", {}, 60)
    show("5. study_question_context (learning state)", ok, d, ms, 1500)
    ctx_id = None
    if ok and isinstance(d, dict):
        ctx_id = d.get("selection_context_id")
    out("    selection_context_id = %r" % ctx_id)
    steps.append(("study_question_context", ok, ms))

    # --- 6. generate a targeted question --------------------------------
    question = None
    if ctx_id:
        ok, d, ms = call("study_generate_targeted_question", {"selection_context_id": ctx_id}, 90)
        show("6. study_generate_targeted_question (quiz)", ok, d, ms, 2000)
        if ok and isinstance(d, dict):
            question = d
        steps.append(("study_generate_targeted_question", ok, ms))
    else:
        out("\n### 6. study_generate_targeted_question SKIPPED (no selection_context_id)")
        steps.append(("study_generate_targeted_question", None, 0))

    # --- 7/8. evaluate answers ------------------------------------------
    if question and question.get("question_id"):
        qid = question.get("question_id")
        aid = question.get("attempt_id")
        out("\n    generated question_id=%r attempt_id=%r" % (qid, aid))
        out("    question text: %s" % str(question.get("question"))[:300])
        out("    expected     : %s" % str(question.get("answer") or question.get("expected_answer"))[:200])

        ok, d, ms = call("study_evaluate_answer",
                         {"answer": "I have no idea, maybe 42?", "question_id": qid,
                          "attempt_id": aid, "selected_topic_id": question.get("selected_topic_id") or ""}, 90)
        show("7. study_evaluate_answer (deliberately poor answer)", ok, d, ms, 1800)
        steps.append(("study_evaluate_answer_wrong", ok, ms))

        ok, d, ms = call("study_evaluate_answer",
                         {"answer": str(question.get("answer") or ""), "question_id": qid,
                          "attempt_id": aid, "selected_topic_id": question.get("selected_topic_id") or ""}, 90)
        show("8. study_evaluate_answer (reference answer)", ok, d, ms, 1800)
        steps.append(("study_evaluate_answer_correct", ok, ms))
    else:
        out("\n### 7/8. study_evaluate_answer SKIPPED (no generated question)")
        steps.append(("study_evaluate_answer", None, 0))

    # --- 9. session summary / persistence --------------------------------
    ok, d, ms = call("study_summarize_session", {}, 120)
    show("9. study_summarize_session", ok, d, ms, 1800)
    steps.append(("study_summarize_session", ok, ms))

    ok, d, ms = call("study_status", {}, 40)
    show("10. study_status (after the session - persistence)", ok, d, ms, 1500)
    steps.append(("study_status_after", ok, ms))

    # --- 11. screen-grounded tutoring ------------------------------------
    ok, d, ms = call("study_ocr_snapshot", {}, 120)
    show("11. study_ocr_snapshot (screen-grounded input)", ok, d, ms, 1200)
    steps.append(("study_ocr_snapshot", ok, ms))

    # --- summary table ----------------------------------------------------
    out("")
    out("=" * 78)
    out("SUMMARY")
    out("=" * 78)
    for name, ok, ms in steps:
        out("  %-38s %-8s %6.0f ms" % (name, {True: "OK", False: "FAILED", None: "SKIPPED"}[ok], ms))

    # --- persistence evidence ---------------------------------------------
    out("")
    out("=== persistence evidence (learning DB) ===")
    for root, _dirs, files in os.walk(os.path.join(RAW, "neko-store")):
        for f in files:
            if f.endswith(".db"):
                p = os.path.join(root, f)
                out("  %s  %d bytes  mtime=%s" % (p, os.path.getsize(p),
                                                  time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p)))))
    db = os.path.join(RAW, "neko-store", "data", "study_companion.db")
    if os.path.exists(db):
        out("  study_companion.db EXISTS (%d bytes)" % os.path.getsize(db))

    with open(EVID, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines))
    out("\nevidence written -> %s" % EVID)


if __name__ == "__main__":
    main()
