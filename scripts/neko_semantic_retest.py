#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Semantic-routing retest after switching ASSIST from `free` to `deepseek`.

Baseline (free provider, 2026-10-08 morning): every call came back with
  study_semantic_status = routing_unavailable
  study_semantic_reason = invalid_response
  knowledge_guidance_status = routing_unavailable
  knowledge_guidance_applied = false
and 27-33 s latency.

Success criteria here:  study_semantic_status != routing_unavailable
and (ideally) knowledge_guidance_applied = true.
"""
import json
import os
import time
import urllib.error
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "study-runtime5-deepseek.txt")
_lines = []

DIAG_KEYS = [
    "degraded", "diagnostic",
    "study_semantic_status", "study_semantic_reason", "study_semantic_intent",
    "study_semantic_subject", "study_semantic_entity", "study_semantic_content_type",
    "knowledge_guidance_status", "knowledge_guidance_source",
    "knowledge_guidance_subject", "knowledge_guidance_applied",
    "knowledge_guidance_focus_topic", "knowledge_guidance_entity",
    "study_response_mode",
]


def out(msg=""):
    print(msg)
    _lines.append(str(msg))


def http(base, path, method="GET", data=None, timeout=60):
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


def call(entry, args=None, timeout_s=240):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    t0 = time.time()
    st, body = http(PBASE, "/runs", "POST",
                    {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
    if st != 200:
        return False, {"_error": body[:300].decode("utf-8", "replace")}, (time.time() - t0) * 1000
    run_id = json.loads(body).get("run_id") or json.loads(body).get("id")
    if not run_id:
        return False, {"_error": "no run_id in %s" % body[:200]}, (time.time() - t0) * 1000
    # terminal statuses per the runs API: succeeded / failed / canceled / timeout
    delay, deadline, last = 0.25, time.time() + timeout_s, {}
    while time.time() < deadline:
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
        st2, b2 = http(PBASE, "/runs/%s" % run_id)
        if st2 != 200:
            continue
        last = json.loads(b2)
        if last.get("status") in ("succeeded", "failed", "canceled", "timeout"):
            break
    elapsed = (time.time() - t0) * 1000
    if last.get("status") != "succeeded":
        return False, {"_error": "run_status=%s err=%s" % (last.get("status"), last.get("error"))}, elapsed
    st3, b3 = http(PBASE, "/runs/%s/export" % run_id)
    if st3 != 200:
        return False, {"_error": "export http %s" % st3}, elapsed
    for it in (json.loads(b3).get("items") or []):
        if it.get("type") == "json" and it.get("json"):
            j = it["json"]
            if j.get("success") is False or j.get("error"):
                return False, {"_error": j.get("error") or j.get("message")}, elapsed
            return True, (j.get("data") if "data" in j else j), elapsed
    return False, {"_error": "no json item"}, elapsed


def show(tag, ok, payload, ms):
    out("### %s   ok=%s  %.0f ms" % (tag, ok, ms))
    if not ok or payload.get("_error"):
        out("    ERROR: %s" % (payload.get("_error") or payload))
        out("")
        return
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    reply = data.get("reply") or data.get("text") or ""
    out("    REPLY(400): %s" % " ".join(str(reply).split())[:400])
    diag = data.get("diagnostics") or data.get("diag") or {}
    if not diag and isinstance(data, dict):
        for k in ("diagnostic", "study_semantic_status"):
            if k in data:
                diag = data
                break
    out("    --- diagnostics ---")
    for k in DIAG_KEYS:
        if k in diag:
            out("      %-32s %s" % (k, diag[k]))
        elif k in data:
            out("      %-32s %s" % (k, data[k]))
    out("")


out("=" * 78)
out("Study Companion semantic retest, ASSIST=deepseek  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
out("=" * 78)

ok, stt, ms = call("study_status", {})
out("### 0. study_status   ok=%s  %.0f ms" % (ok, ms))
if ok:
    d = stt.get("data", stt)
    cfg = d.get("config") or {}
    out("    mode=%r  ocr_enabled=%r  awareness=%r  llm_vision=%r" % (
        cfg.get("mode"), cfg.get("ocr_enabled"),
        (cfg.get("awareness") or {}).get("enabled"), cfg.get("llm_vision_enabled")))
    weak = d.get("weak_topics") or []
    out("    weak_topics=%d  memory_deck_items=%d" % (
        len(weak), ((d.get("memory_deck") or {}).get("item_count") or 0)))
out("")

# the SAME question used in the `free` baseline, for a fair latency comparison
Q = "Flutter里StatelessWidget和StatefulWidget的区别是什么？"
ok1, p1, ms1 = call("study_explain_text", {"text": Q})
show("1. study_explain_text (companion)", ok1, p1, ms1)

ok2, p2, ms2 = call("study_explain_text", {"text": "二阶导数怎么判断极值？"})
show("2. study_explain_text (math, subject routing)", ok2, p2, ms2)

ok3, stt3, ms3 = call("study_status", {})
out("### 3. final study_status   ok=%s  %.0f ms" % (ok3, ms3))
if ok3:
    d3 = stt3.get("data", stt3)
    weak3 = d3.get("weak_topics") or []
    out("    weak_topics=%d" % len(weak3))
    for w in weak3[:3]:
        out("      %s mastery=%.4f attempts=%s" % (w.get("topic_id"), w.get("mastery", -1), w.get("attempts")))
out("")

out("latency summary: call1=%.0fms call2=%.0fms  (baseline free: 31412 / 33570 ms)" % (ms1, ms2))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
