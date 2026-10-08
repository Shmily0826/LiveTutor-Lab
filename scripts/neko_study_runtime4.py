#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fourth runtime pass: interactive mode, plugin-resolved LLM configuration,
diagnostic / degraded status of semantic routing and knowledge guidance.
"""
import json
import os
import time
import urllib.request
import urllib.error

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "study-runtime4.txt")
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
        return False, {"http": st, "body": body[:400].decode("utf-8", "replace")}, (time.time() - t0) * 1000
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


DIAG_KEYS = [
    "degraded", "diagnostic",
    "study_semantic_status", "study_semantic_reason",
    "study_semantic_intent", "study_semantic_subject",
    "study_semantic_entity", "study_semantic_content_type",
    "knowledge_guidance_status", "knowledge_guidance_source",
    "knowledge_guidance_subject", "knowledge_guidance_focus_topic",
    "knowledge_guidance_applied", "knowledge_guidance_entity",
    "study_response_mode", "screen_type",
]


def diag(payload):
    out("    --- diagnostics ---")
    for k in DIAG_KEYS:
        if k in payload:
            v = payload.get(k)
            out("      %-32s %s" % (k, json.dumps(v, ensure_ascii=False)[:180]))


def main():
    out("=" * 78)
    out("N.E.K.O Study Companion - RUNTIME pass 4 (interactive mode / LLM config / diagnostics)")
    out("time: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    out("=" * 78)
    steps = []

    # 0. plugin-resolved config ---------------------------------------------
    ok, stt, ms = call("study_status", {}, 60)
    out("")
    out("### 0. study_status.config (plugin-resolved runtime config)")
    if ok:
        cfg = stt.get("config")
        out("    " + json.dumps(cfg, ensure_ascii=False)[:2500])
        out("")
        out("    dependencies=%s" % json.dumps(stt.get("dependencies"), ensure_ascii=False)[:600])
        out("    habit=%s" % json.dumps(stt.get("habit"), ensure_ascii=False)[:400])
        out("    review_queue=%s" % json.dumps(stt.get("review_queue"), ensure_ascii=False)[:400])
        out("    weak_topics=%s" % json.dumps(stt.get("weak_topics"), ensure_ascii=False)[:500])
        out("    mastery_overview=%s" % json.dumps(stt.get("mastery_overview"), ensure_ascii=False)[:500])
        out("    memory_deck=%s" % json.dumps(stt.get("memory_deck"), ensure_ascii=False)[:300])
        out("    session_suggestions=%s" % json.dumps(stt.get("session_suggestions"), ensure_ascii=False)[:400])
    steps.append(("study_status_config", ok, ms))

    # 1. switch to interactive ----------------------------------------------
    ok1, sw, ms1 = call("study_set_mode", {"mode": "interactive"}, 90)
    out("")
    out("### 1. study_set_mode -> interactive   ok=%s  %.0f ms" % (ok1, ms1))
    out("    " + json.dumps(sw, ensure_ascii=False)[:900])
    steps.append(("study_set_mode_interactive", ok1, ms1))

    # 2. explain in interactive mode ----------------------------------------
    ok2, ex, ms2 = call("study_explain_text",
                        {"text": "What is the difference between StatelessWidget and StatefulWidget in Flutter?"},
                        180)
    out("")
    out("### 2. study_explain_text in INTERACTIVE mode   ok=%s  %.0f ms" % (ok2, ms2))
    if ok2:
        out("    MODE=%s" % ex.get("study_response_mode"))
        out("    REPLY: %s" % str(ex.get("reply"))[:700].replace("\n", "\n      "))
        diag(ex)
    else:
        out("    FAIL: %s" % json.dumps(ex, ensure_ascii=False)[:600])
    steps.append(("study_explain_interactive", ok2, ms2))

    # 3. back to teaching for comparison ------------------------------------
    ok3, sw3, ms3 = call("study_set_mode", {"mode": "teaching"}, 90)
    out("")
    out("### 3. study_set_mode -> teaching   ok=%s  %.0f ms" % (ok3, ms3))
    out("    " + json.dumps(sw3, ensure_ascii=False)[:900])
    steps.append(("study_set_mode_teaching", ok3, ms3))

    ok4, ex4, ms4 = call("study_explain_text",
                         {"text": "What is the difference between StatelessWidget and StatefulWidget in Flutter?"},
                         180)
    out("")
    out("### 4. study_explain_text in TEACHING mode (same question)   ok=%s  %.0f ms" % (ok4, ms4))
    if ok4:
        out("    MODE=%s" % ex4.get("study_response_mode"))
        out("    REPLY: %s" % str(ex4.get("reply"))[:700].replace("\n", "\n      "))
        diag(ex4)
    else:
        out("    FAIL: %s" % json.dumps(ex4, ensure_ascii=False)[:600])
    steps.append(("study_explain_teaching", ok4, ms4))

    # 5. companion mode ------------------------------------------------------
    ok5, sw5, ms5 = call("study_set_mode", {"mode": "companion"}, 90)
    out("")
    out("### 5. study_set_mode -> companion   ok=%s  %.0f ms" % (ok5, ms5))
    out("    " + json.dumps(sw5, ensure_ascii=False)[:900])
    steps.append(("study_set_mode_companion", ok5, ms5))

    # 6. final status --------------------------------------------------------
    ok6, stt6, ms6 = call("study_status", {}, 60)
    out("")
    out("### 6. final study_status")
    if ok6:
        out("    active_mode=%s  default_mode=%s" % (stt6.get("active_mode"), stt6.get("default_mode")))
        out("    session_summary_seed=%s" % json.dumps(stt6.get("session_summary_seed"), ensure_ascii=False)[:600])
        out("    recent_mode_switches=%s" % json.dumps(stt6.get("recent_mode_switches"), ensure_ascii=False)[:500])
    steps.append(("study_status_final", ok6, ms6))

    out("")
    out("=" * 78)
    out("SUMMARY pass 4")
    out("=" * 78)
    for n, ok_, ms_ in steps:
        out("  %-38s %-8s %6.0f ms" % (n, {True: "OK", False: "FAILED", None: "SKIPPED"}[ok_], ms_))

    with open(EVID, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines))
    out("\nevidence -> %s" % EVID)


if __name__ == "__main__":
    main()
