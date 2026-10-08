#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Second runtime pass: quiz generation, answer evaluation (wrong + correct),
learning-state writeback, and screen-grounded (OCR-fallback) tutoring.
"""
import json
import os
import time
import urllib.request
import urllib.error

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
MBASE = "http://127.0.0.1:48911"
PLUGIN = "study_companion"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "study-runtime2.txt")
os.makedirs(os.path.dirname(EVID), exist_ok=True)
_lines = []


def out(msg=""):
    print(msg)
    _lines.append(str(msg))


def http(base, path, method="GET", data=None, timeout=30):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


def call(entry, args=None, timeout_s=150):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    t0 = time.time()
    st, body = http(PBASE, "/runs", "POST", {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
    if st != 200:
        return False, {"http": st, "body": body[:500].decode("utf-8", "replace")}, (time.time() - t0) * 1000
    run_id = json.loads(body).get("run_id") or json.loads(body).get("id")
    delay, deadline, last = 0.25, time.time() + timeout_s, {}
    while time.time() < deadline:
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
        st2, b2 = http(PBASE, "/runs/%s" % run_id, "GET")
        if st2 != 200:
            continue
        last = json.loads(b2)
        if last.get("status") in ("succeeded", "failed", "canceled", "timeout"):
            break
    elapsed = (time.time() - t0) * 1000
    if last.get("status") != "succeeded":
        return False, {"run_status": last.get("status"), "error": last.get("error")}, elapsed
    st3, b3 = http(PBASE, "/runs/%s/export" % run_id, "GET")
    if st3 != 200:
        return False, {"export_http": st3}, elapsed
    for it in (json.loads(b3).get("items") or []):
        if it.get("type") == "json" and it.get("json"):
            j = it["json"]
            if j.get("success") is False or j.get("error"):
                return False, {"plugin_error": j.get("error") or j.get("message")}, elapsed
            return True, j.get("data") if "data" in j else j, elapsed
    return False, {"no_json": True}, elapsed


def show(title, ok, data, ms, limit=1400):
    out("")
    out("### %s" % title)
    out("    ok=%s  %.0f ms" % (ok, ms))
    s = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    out("    " + s[:limit].replace("\n", "\n    "))


def main():
    out("=" * 78)
    out("N.E.K.O Study Companion - RUNTIME pass 2 (quiz / evaluation / persistence)")
    out("time: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    out("=" * 78)
    steps = []

    # A. generate a question on a known topic -----------------------------
    ok, q, ms = call("study_generate_question",
                     {"text": "Use the chain rule to differentiate f(x)=sin(x^2).",
                      "topic": "math"}, 120)
    show("A. study_generate_question", ok, q, ms, 1800)
    steps.append(("study_generate_question", ok, ms))

    qid = q.get("question_id") if ok and isinstance(q, dict) else None
    aid = q.get("attempt_id") if ok and isinstance(q, dict) else None
    out("    question_id=%r attempt_id=%r" % (qid, aid))
    if ok and isinstance(q, dict):
        out("    QUESTION : %s" % str(q.get("question"))[:300])
        out("    ANSWER   : %s" % str(q.get("answer") or q.get("expected_answer"))[:200])
        out("    HINT     : %s" % str(q.get("hint"))[:200])
        out("    TOPIC    : %s" % str(q.get("topic"))[:200])
        out("    DIFFICULTY: %s" % q.get("difficulty"))

    if qid:
        # B. deliberately poor answer -------------------------------------
        ok2, ev, ms2 = call("study_evaluate_answer",
                            {"answer": "42", "question_id": qid, "attempt_id": aid,
                             "selected_topic_id": (q or {}).get("selected_topic_id") or ""}, 120)
        show("B. study_evaluate_answer (wrong answer '42')", ok2, ev, ms2, 1800)
        steps.append(("study_evaluate_answer_wrong", ok2, ms2))
        if ok2 and isinstance(ev, dict):
            out("    VERDICT=%s SCORE=%s" % (ev.get("verdict"), ev.get("score")))
            out("    FEEDBACK=%s" % str(ev.get("feedback"))[:300])
            out("    NEXT_ACTION=%s" % str(ev.get("next_action"))[:200])

        # C. reference answer ----------------------------------------------
        ref = str((q or {}).get("answer") or "2x*cos(x^2)")
        ok3, ev2, ms3 = call("study_evaluate_answer",
                             {"answer": ref, "question_id": qid, "attempt_id": aid,
                              "selected_topic_id": (q or {}).get("selected_topic_id") or ""}, 120)
        show("C. study_evaluate_answer (reference answer)", ok3, ev2, ms3, 1400)
        steps.append(("study_evaluate_answer_correct", ok3, ms3))
        if ok3 and isinstance(ev2, dict):
            out("    VERDICT=%s SCORE=%s" % (ev2.get("verdict"), ev2.get("score")))
            out("    FEEDBACK=%s" % str(ev2.get("feedback"))[:300])

    # D. learning state now? ------------------------------------------------
    ok, ctx, ms = call("study_question_context", {}, 60)
    show("D. study_question_context (after answering)", ok, ctx, ms, 1200)
    steps.append(("study_question_context_after", ok, ms))
    ctx_id = ctx.get("selection_context_id") if ok and isinstance(ctx, dict) else None
    out("    selection_context_id=%r  no_data=%s" % (ctx_id, (ctx or {}).get("no_data")))
    out("    mastery_overview=%s" % json.dumps((ctx or {}).get("mastery_overview"), ensure_ascii=False)[:400])
    out("    weak_topics=%s" % json.dumps((ctx or {}).get("weak_topics"), ensure_ascii=False)[:400])
    out("    due_reviews=%s" % json.dumps((ctx or {}).get("due_reviews"), ensure_ascii=False)[:300])

    # E. targeted question now possible? -------------------------------------
    if ctx_id:
        ok, tq, ms = call("study_generate_targeted_question", {"selection_context_id": ctx_id}, 90)
        show("E. study_generate_targeted_question", ok, tq, ms, 1200)
        steps.append(("study_generate_targeted_question", ok, ms))
    else:
        out("\n### E. study_generate_targeted_question SKIPPED (still no context id)")
        steps.append(("study_generate_targeted_question", None, 0))

    # F. screen-grounded tutoring: explain with NO text (OCR fallback) -------
    ok, sg, ms = call("study_explain_text", {"text": ""}, 150)
    show("F. study_explain_text with empty text (OCR fallback = screen grounding)", ok, sg, ms, 1200)
    steps.append(("study_explain_text_ocr_fallback", ok, ms))
    if ok and isinstance(sg, dict):
        out("    input_text actually used: %s" % str(sg.get("input_text"))[:200])
        out("    reply head: %s" % str(sg.get("reply"))[:300])

    # G. status / persistence ------------------------------------------------
    ok, stt, ms = call("study_status", {}, 40)
    steps.append(("study_status_final", ok, ms))
    if ok and isinstance(stt, dict):
        out("")
        out("### G. persistence snapshot")
        out("    mode=%s  is_first_run=%s" % (stt.get("active_mode"), stt.get("is_first_run")))
        out("    last_ocr_at=%s last_ocr_len=%d" % (stt.get("last_ocr_at"), len(str(stt.get("last_ocr_text") or ""))))
        out("    last_answer_evaluation=%s" % json.dumps(stt.get("last_answer_evaluation"), ensure_ascii=False)[:400])
        out("    session_summary_seed=%s" % json.dumps(stt.get("session_summary_seed"), ensure_ascii=False)[:500])
        ev_count = len(stt.get("recent_learning_events") or [])
        out("    recent_learning_events=%d" % ev_count)
        for e in (stt.get("recent_learning_events") or [])[:8]:
            out("       - %s" % str(e.get("operation") or e.get("kind")))

    out("")
    out("=" * 78)
    out("SUMMARY pass 2")
    out("=" * 78)
    for n, ok, ms in steps:
        out("  %-38s %-8s %6.0f ms" % (n, {True: "OK", False: "FAILED", None: "SKIPPED"}[ok], ms))

    out("")
    out("=== learning DB files ===")
    for root, _d, files in os.walk(os.path.join(RAW, "neko-store")):
        for f in files:
            if f.endswith(".db"):
                p = os.path.join(root, f)
                out("  %s  %d bytes" % (p, os.path.getsize(p)))

    with open(EVID, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines))
    out("\nevidence -> %s" % EVID)


if __name__ == "__main__":
    main()
