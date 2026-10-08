#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Third runtime pass: close the quiz -> evaluate -> persist -> review loop.

Key correction vs pass 2: `question_id` / `attempt_id` are ONLY injected by
`_question_private_payload()` on the *targeted_question* path.  For the plain
`study_generate_question` path the returned payload carries no ids, so
`current_question_requires_identity` is False and `study_evaluate_answer` must
be called with just `answer` (it falls back to `self._state.current_question`).
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
EVID = os.path.join(RAW, "evidence", "study-runtime3.txt")
os.makedirs(os.path.dirname(EVID), exist_ok=True)
_lines = []


def out(msg=""):
    print(msg)
    _lines.append(str(msg))


def http(base, path, method="GET", data=None, timeout=45):
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


def call(entry, args=None, timeout_s=180):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    t0 = time.time()
    st, body = http(PBASE, "/runs", "POST",
                    {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
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
    raw = json.loads(b3)
    for it in (raw.get("items") or []):
        if it.get("type") == "json" and it.get("json"):
            j = it["json"]
            if j.get("success") is False or j.get("error"):
                return False, {"plugin_error": j.get("error") or j.get("message")}, elapsed
            return True, j.get("data") if "data" in j else j, elapsed
    return False, {"no_json": True}, elapsed


def keys(d):
    if isinstance(d, dict):
        return sorted(d.keys())
    return None


def main():
    out("=" * 78)
    out("N.E.K.O Study Companion - RUNTIME pass 3 (close quiz/evaluate/review loop)")
    out("time: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    out("=" * 78)
    steps = []

    # A. generate fresh question -------------------------------------------
    ok, q, ms = call("study_generate_question",
                     {"text": "Use the chain rule to differentiate f(x)=sin(x^2).",
                      "topic": "calculus-chain-rule"}, 150)
    steps.append(("study_generate_question", ok, ms))
    out("")
    out("### A. study_generate_question   ok=%s  %.0f ms" % (ok, ms))
    if not ok:
        out("    FAIL: %s" % json.dumps(q, ensure_ascii=False)[:600])
    else:
        out("    PAYLOAD KEYS: %s" % keys(q))
        out("    question_id=%r attempt_id=%r" % (q.get("question_id"), q.get("attempt_id")))
        out("    QUESTION  : %s" % str(q.get("question"))[:300])
        out("    ANSWER    : %s" % str(q.get("answer") or q.get("reference_answer"))[:200])
        out("    TOPIC     : %s" % str(q.get("topic"))[:120])
        out("    DIFFICULTY: %s   type: %s" % (q.get("difficulty"), q.get("question_type")))

    ref_answer = str((q or {}).get("answer") or "2x cos(x^2)") if ok else "2x cos(x^2)"

    # B. wrong answer, no ids ------------------------------------------------
    ok2, ev, ms2 = call("study_evaluate_answer", {"answer": "42"}, 150)
    steps.append(("study_evaluate_answer_wrong", ok2, ms2))
    out("")
    out("### B. study_evaluate_answer (WRONG: '42')  ok=%s  %.0f ms" % (ok2, ms2))
    if not ok2:
        out("    FAIL: %s" % json.dumps(ev, ensure_ascii=False)[:600])
    else:
        out("    PAYLOAD KEYS: %s" % keys(ev))
        out("    VERDICT=%s SCORE=%s ERROR_TYPE=%s" %
            (ev.get("verdict"), ev.get("score"), ev.get("error_type")))
        out("    FEEDBACK   : %s" % str(ev.get("feedback"))[:400])
        out("    NEXT_ACTION: %s" % str(ev.get("next_action"))[:250])

    # C. correct answer, no ids ---------------------------------------------
    ok3, ev2, ms3 = call("study_evaluate_answer",
                         {"answer": ref_answer,
                          "question": str((q or {}).get("question") or ""),
                          "expected_answer": ref_answer}, 150)
    steps.append(("study_evaluate_answer_correct", ok3, ms3))
    out("")
    out("### C. study_evaluate_answer (CORRECT: %r)  ok=%s  %.0f ms" % (ref_answer[:60], ok3, ms3))
    if not ok3:
        out("    FAIL: %s" % json.dumps(ev2, ensure_ascii=False)[:600])
    else:
        out("    PAYLOAD KEYS: %s" % keys(ev2))
        out("    VERDICT=%s SCORE=%s ERROR_TYPE=%s" %
            (ev2.get("verdict"), ev2.get("score"), ev2.get("error_type")))
        out("    FEEDBACK   : %s" % str(ev2.get("feedback"))[:400])

    # D. learning-state context after two evaluations ------------------------
    ok4, ctx, ms4 = call("study_question_context", {}, 90)
    steps.append(("study_question_context_after", ok4, ms4))
    out("")
    out("### D. study_question_context (after 2 evaluations)  ok=%s  %.0f ms" % (ok4, ms4))
    if ok4:
        out("    PAYLOAD KEYS: %s" % keys(ctx))
        out("    no_data=%s  selection_context_id=%r" %
            (ctx.get("no_data"), ctx.get("selection_context_id")))
        out("    selection_reason=%s" % ctx.get("selection_reason"))
        out("    mastery_overview=%s" % json.dumps(ctx.get("mastery_overview"), ensure_ascii=False)[:600])
        out("    weak_topics=%s" % json.dumps(ctx.get("weak_topics"), ensure_ascii=False)[:600])
        out("    due_reviews=%s" % json.dumps(ctx.get("due_reviews"), ensure_ascii=False)[:400])
        out("    practice_scope=%s" % json.dumps(ctx.get("practice_scope"), ensure_ascii=False)[:300])
    else:
        out("    FAIL: %s" % json.dumps(ctx, ensure_ascii=False)[:600])

    # E. targeted / adaptive question ----------------------------------------
    ctx_id = (ctx or {}).get("selection_context_id") if ok4 else None
    if ctx_id:
        ok5, tq, ms5 = call("study_generate_targeted_question",
                            {"selection_context_id": ctx_id}, 150)
        out("")
        out("### E. study_generate_targeted_question  ok=%s  %.0f ms" % (ok5, ms5))
        if ok5:
            out("    PAYLOAD KEYS: %s" % keys(tq))
            out("    question_id=%r attempt_id=%r" % (tq.get("question_id"), tq.get("attempt_id")))
            out("    QUESTION: %s" % str(tq.get("question"))[:300])
            out("    TOPIC   : %s / %s" % (tq.get("selected_topic_id"), tq.get("selected_topic_name")))
            out("    REASON  : %s" % str(tq.get("selection_reason"))[:200])
        else:
            out("    FAIL: %s" % json.dumps(tq, ensure_ascii=False)[:600])
    else:
        # try without context id - builder should build a pending context itself
        ok5, tq, ms5 = call("study_generate_targeted_question", {}, 150)
        out("")
        out("### E. study_generate_targeted_question (no ctx id)  ok=%s  %.0f ms" % (ok5, ms5))
        if ok5:
            out("    PAYLOAD KEYS: %s" % keys(tq))
            out("    question_id=%r attempt_id=%r" % (tq.get("question_id"), tq.get("attempt_id")))
            out("    QUESTION: %s" % str(tq.get("question"))[:300])
            out("    TOPIC   : %s / %s" % (tq.get("selected_topic_id"), tq.get("selected_topic_name")))
            out("    REASON  : %s" % str(tq.get("selection_reason"))[:200])
        else:
            out("    FAIL: %s" % json.dumps(tq, ensure_ascii=False)[:600])
    steps.append(("study_generate_targeted_question", ok5, ms5))

    # F. persistence / review ------------------------------------------------
    ok6, stt, ms6 = call("study_status", {}, 60)
    steps.append(("study_status_final", ok6, ms6))
    out("")
    out("### F. study_status persistence snapshot  ok=%s  %.0f ms" % (ok6, ms6))
    if ok6:
        out("    KEYS: %s" % keys(stt))
        out("    active_mode=%s  is_first_run=%s" % (stt.get("active_mode"), stt.get("is_first_run")))
        out("    last_answer_evaluation=%s" %
            json.dumps(stt.get("last_answer_evaluation"), ensure_ascii=False)[:500])
        out("    session_summary_seed=%s" %
            json.dumps(stt.get("session_summary_seed"), ensure_ascii=False)[:700])
        evs = stt.get("recent_learning_events") or []
        out("    recent_learning_events=%d" % len(evs))
        for e in evs[:10]:
            out("       - %s" % str(e.get("operation") or e.get("kind")))

    out("")
    out("=" * 78)
    out("SUMMARY pass 3")
    out("=" * 78)
    for n, ok_, ms_ in steps:
        out("  %-38s %-8s %6.0f ms" % (n, {True: "OK", False: "FAILED", None: "SKIPPED"}[ok_], ms_))

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
