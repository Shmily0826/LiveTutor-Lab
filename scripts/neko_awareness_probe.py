#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Awareness (continuous screen understanding) feasibility probe.

awareness config says snapshot_interval_seconds=5, but one full-screen OCR
costs 23-31 s on this box.  This probe:

  1. reads the current settings config
  2. enables awareness
  3. samples awareness/OCR state every 10 s for 90 s
  4. disables awareness again (always, even on error)

Expectation to verify: with a 25 s OCR cost and a 5 s target interval, the
loop should fall behind.  Counting actual snapshots tells us the real cadence.
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
EVID = os.path.join(RAW, "evidence", "study-runtime7-awareness.txt")
_lines = []


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


def call(entry, args=None, timeout_s=300):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    t0 = time.time()
    st, body = http(PBASE, "/runs", "POST",
                    {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
    if st != 200:
        return False, {"_error": body[:300].decode("utf-8", "replace")}, (time.time() - t0) * 1000
    run_id = json.loads(body).get("run_id") or json.loads(body).get("id")
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


out("=" * 78)
out("Awareness feasibility probe  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
out("=" * 78)

ok, cfg, ms = call("study_get_settings_config")
out("### 0. study_get_settings_config   ok=%s  %.0f ms" % (ok, ms))
aware_cfg = {}
if ok:
    d = cfg.get("data") if isinstance(cfg.get("data"), dict) else cfg
    aware_cfg = d.get("awareness") or {}
    out("    awareness=%s" % json.dumps(aware_cfg, ensure_ascii=False)[:400])
out("")

WAS_ENABLED = bool(aware_cfg.get("enabled"))
out("### baseline awareness.enabled = %s" % WAS_ENABLED)
out("")

# ---------------------------------------------------------------- enable
if not WAS_ENABLED:
    ok1, r1, ms1 = call("study_update_settings_config",
                        {"config": {"awareness": {"enabled": True}}})
    out("### 1. enable awareness   ok=%s  %.0f ms  resp=%s"
        % (ok1, ms1, json.dumps(r1, ensure_ascii=False)[:200]))
out("")

# ---------------------------------------------------------------- observe
out("### 2. observing 90 s (sampling every 10 s)")
t_start = time.time()
samples = []
while time.time() - t_start < 90:
    time.sleep(10)
    el = time.time() - t_start
    okS, stt, msS = call("study_status", {}, timeout_s=120)
    info = {}
    if okS:
        d = stt.get("data", stt)
        aw = d.get("awareness") or d.get("awareness_status") or {}
        if isinstance(aw, dict):
            info = {k: aw.get(k) for k in
                    ("running", "last_snapshot_at", "snapshot_count",
                     "last_error", "push_count", "queue_depth") if k in aw}
        recent = d.get("recent_screen_classifications") or []
        info["recent_classifications"] = len(recent)
        last_cls = recent[-1] if recent else {}
        info["last_screen_type"] = last_cls.get("screen_type")
        info["last_confidence"] = last_cls.get("confidence")
        info["last_ocr_chars"] = len(d.get("last_ocr_text") or "")
    samples.append((el, okS, msS, info))
    out("  t=%4.0fs status_ok=%s status_ms=%.0f  %s" % (el, okS, msS, json.dumps(info, ensure_ascii=False)[:260]))
out("")

# ---------------------------------------------------------------- revert
if not WAS_ENABLED:
    ok2, r2, ms2 = call("study_update_settings_config",
                        {"config": {"awareness": {"enabled": False}}})
    out("### 3. revert awareness to disabled   ok=%s  %.0f ms  resp=%s"
        % (ok2, ms2, json.dumps(r2, ensure_ascii=False)[:200]))
    ok3, cfg3, _ = call("study_get_settings_config")
    if ok3:
        d3 = cfg3.get("data") if isinstance(cfg3.get("data"), dict) else cfg3
        out("    final awareness.enabled = %s"
            % bool((d3.get("awareness") or {}).get("enabled")))
out("")

n_ok = sum(1 for s in samples if s[1])
out("summary: %d/%d status polls ok; samples=%s" % (n_ok, len(samples), len(samples)))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
