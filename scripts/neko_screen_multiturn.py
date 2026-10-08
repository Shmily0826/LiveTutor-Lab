#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Screen-grounded multi-turn teaching test on the REAL desktop.

Flow:
  1. study_ocr_snapshot  : capture the user's actual screen via RapidOCR
  2. study_explain_text {"text": ""} : ask about what is on screen
     (empty text makes the entry fall back to self._state.last_ocr_text)
  3. study_explain_text with a follow-up that depends on turn 2

Privacy: only a truncated OCR preview and the classification are printed,
never the full screen text.
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
EVID = os.path.join(RAW, "evidence", "study-runtime6-screen-multiturn.txt")
_lines = []

DIAG_KEYS = [
    "degraded", "diagnostic",
    "study_semantic_status", "study_semantic_intent", "study_semantic_subject",
    "study_semantic_content_type",
    "knowledge_guidance_status", "knowledge_guidance_applied",
    "knowledge_guidance_focus_topic",
    "study_response_mode", "screen_grounded",
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
        return False, {"_error": "no run_id"}, (time.time() - t0) * 1000
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


def show(tag, ok, payload, ms, reply_key="reply"):
    out("### %s   ok=%s  %.0f ms" % (tag, ok, ms))
    if not ok or payload.get("_error"):
        out("    ERROR: %s" % (payload.get("_error") or payload))
        out("")
        return
    d = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    reply = d.get(reply_key) or d.get("text") or ""
    out("    REPLY(500): %s" % " ".join(str(reply).split())[:500])
    for k in DIAG_KEYS:
        if k in d:
            out("      %-32s %s" % (k, d[k]))
    diag = d.get("diagnostics") or {}
    for k in DIAG_KEYS:
        if k in diag and k not in d:
            out("      %-32s %s" % (k, diag[k]))
    out("")


out("=" * 78)
out("Screen-grounded MULTI-TURN teaching test (real desktop)  %s"
    % time.strftime("%Y-%m-%d %H:%M:%S"))
out("=" * 78)

# --- turn 0: capture the screen -------------------------------------------------
ok0, p0, ms0 = call("study_ocr_snapshot", {"capture_mode": "fullscreen"})
out("### 0. study_ocr_snapshot   ok=%s  %.0f ms" % (ok0, ms0))
d0 = p0.get("data") if isinstance(p0.get("data"), dict) else p0
if not ok0:
    out("    ERROR: %s" % (p0.get("_error") or p0))
else:
    snap = d0.get("snapshot") or d0
    txt = (snap.get("text") or "")
    out("    ocr status=%r  text_chars=%d" % (snap.get("status"), len(txt)))
    out("    text preview(180): %s" % " ".join(txt.split())[:180])
    cls = d0.get("screen_classification") or snap.get("screen_classification") or {}
    if isinstance(cls, dict):
        out("    classification: %s" % json.dumps(cls, ensure_ascii=False)[:300])
    out("")

# --- turn 1: ask about the screen ------------------------------------------------
ok1, p1, ms1 = call("study_explain_text", {"text": ""})
show("1. study_explain_text on-screen (empty text -> OCR fallback)", ok1, p1, ms1)

# --- turn 2: a follow-up that depends on turn 1 ----------------------------------
ok2, p2, ms2 = call("study_explain_text",
                    {"text": "就你刚才回答里提到的那个要点，给我出一个练习题并说明为什么"})
show("2. follow-up: generate an exercise about turn-1's key point", ok2, p2, ms2)

out("latency: ocr=%.0fms turn1=%.0fms turn2=%.0fms" % (ms0, ms1, ms2))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
