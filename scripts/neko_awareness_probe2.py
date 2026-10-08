#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Awareness probe v2 - uses the OFFICIAL plugin config API.

v1 finding: study_update_settings_config silently ignores the "awareness" key
(entry_status_entries.py:_apply_settings_config has no awareness branch).
The real source is plugin.toml [study.awareness], read at plugin startup()
(__init__.py:373).  This probe therefore:

  1. GET  /plugin/study_companion/config           -> save pristine copy
  2. PUT  same config with study.awareness.enabled=true
  3. POST /plugin/study_companion/reload           -> startup() re-runs
  4. wait for plugin ready, then sample 150 s:
       - study_status (config echo + supervision signals)
       - awareness config echo
  5. grep plugin logs for awareness-related lines
  6. REVERT: PUT pristine config back, reload again, verify enabled=false

Lightweight path expectation: capture_lightweight = screenshot + thumbnail +
phash + window title, NO full OCR, so ticks should land near the 5 s target
even though full study_ocr_snapshot costs 23-25 s on this box.

Privacy: never prints screen text; only counts, flags, truncated titles.
"""
import copy
import json
import os
import time
import urllib.error
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "study-runtime8-awareness-v2.txt")
_lines = []


def out(msg=""):
    print(msg)
    _lines.append(str(msg))


def http(path, method="GET", data=None, timeout=60):
    req = urllib.request.Request(
        PBASE + path, method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"} if data is not None else {})
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


def jbody(b):
    try:
        return json.loads(b)
    except Exception:
        return {}


def call_entry(entry, args=None, timeout_s=300):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    st, body = http("/runs", "POST",
                    {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
    if st != 200:
        return False, {"_error": body[:200].decode("utf-8", "replace")}
    run_id = jbody(body).get("run_id") or jbody(body).get("id")
    delay, deadline, last = 0.25, time.time() + timeout_s, {}
    while time.time() < deadline:
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
        st2, b2 = http("/runs/%s" % run_id)
        if st2 != 200:
            continue
        last = jbody(b2)
        if last.get("status") in ("succeeded", "failed", "canceled", "timeout"):
            break
    if last.get("status") != "succeeded":
        return False, {"_error": "run_status=%s" % last.get("status")}
    st3, b3 = http("/runs/%s/export" % run_id)
    if st3 != 200:
        return False, {"_error": "export http %s" % st3}
    for it in (jbody(b3).get("items") or []):
        if it.get("type") == "json" and it.get("json"):
            j = it["json"]
            if j.get("success") is False or j.get("error"):
                return False, {"_error": j.get("error") or j.get("message")}
            return True, (j.get("data") if "data" in j else j)
    return False, {"_error": "no json item"}


def find_awareness(obj, path=""):
    """Recursively yield (path, value) for any dict that looks like awareness."""
    hits = []
    if isinstance(obj, dict):
        if "snapshot_interval_seconds" in obj and "enabled" in obj:
            hits.append((path, obj))
        for k, v in obj.items():
            hits.extend(find_awareness(v, path + "/" + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_awareness(v, path + "/%d" % i))
    return hits


def supervision_bits(data):
    """Pull supervision-ish timestamps out of a study_status payload."""
    bits = {}
    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if any(t in kl for t in ("supervision", "idle", "distraction",
                                         "last_activity", "foreground")):
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        bits[p + "/" + str(k)] = v
                    else:
                        bits[p + "/" + str(k)] = "<dict:%d>" % len(v)
                walk(v, p + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o[:3]):
                walk(v, p + "/%d" % i)
    walk(data)
    return bits


FRAMEWORK_SECTIONS = ("plugin", "plugin_runtime", "plugin_state")


def user_config(cfg):
    """Strip framework-internal sections; PUT rejects their fields outright
    ('Cannot modify critical field plugin.id' even when the value is unchanged)."""
    return {k: copy.deepcopy(v) for k, v in cfg.items()
            if k not in FRAMEWORK_SECTIONS}


out("=" * 78)
out("Awareness probe v2 (official config API)  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
out("=" * 78)

# ---------------------------------------------------- 1. pristine config
st, b = http("/plugin/%s/config" % PLUGIN)
if st != 200:
    out("FATAL: cannot GET config: %s %s" % (st, b[:200]))
    raise SystemExit(1)
pristine = jbody(b).get("config")
if not isinstance(pristine, dict):
    out("FATAL: unexpected config payload")
    raise SystemExit(1)
enabled_before = ((pristine.get("study") or {}).get("awareness") or {}).get("enabled")
out("### 1. pristine config fetched; study.awareness.enabled = %r" % enabled_before)

# ---------------------------------------------------- 2. enable
modified = user_config(pristine)
modified.setdefault("study", {})["awareness"]["enabled"] = True
st, b = http("/plugin/%s/config" % PLUGIN, "PUT", {"config": modified})
out("### 2. PUT config (awareness.enabled=true, framework sections stripped) -> %s  %s"
    % (st, b[:200].decode("utf-8", "replace")))
st, b = http("/plugin/%s/config" % PLUGIN)
cfg_after = jbody(b).get("config") or {}
now_enabled = ((cfg_after.get("study") or {}).get("awareness") or {}).get("enabled")
kept = sorted(set(cfg_after) & set(FRAMEWORK_SECTIONS))
out("    verify after PUT: study.awareness.enabled = %r; framework sections still present: %s"
    % (now_enabled, kept))

# ---------------------------------------------------- 3. reload
out("### 3. POST /plugin/%s/reload  (plugin restart, OCR init may take a while)"
    % PLUGIN)
st, b = http("/plugin/%s/reload" % PLUGIN, "POST", {}, timeout=120)
out("    reload -> %s  %s" % (st, b[:200].decode("utf-8", "replace")))

ready = False
t0 = time.time()
while time.time() - t0 < 240:
    time.sleep(3)
    okS, stt = call_entry("study_status", {}, timeout_s=60)
    if okS:
        ready = True
        break
out("    plugin ready after %.0f s (study_status ok=%s)" % (time.time() - t0, ready))
if not ready:
    out("    fallback: POST /plugin/%s/start" % PLUGIN)
    st, b = http("/plugin/%s/start" % PLUGIN, "POST", {}, timeout=180)
    out("    start -> %s %s" % (st, b[:200].decode("utf-8", "replace")))
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(3)
        okS, stt = call_entry("study_status", {}, timeout_s=60)
        if okS:
            ready = True
            break
    out("    ready=%s after fallback" % ready)

# ---------------------------------------------------- 4. sample
out("")
out("### 4. sampling 150 s (every 10 s)")
t_start = time.time()
supv_seen = {}
samples = []
while time.time() - t_start < 150:
    time.sleep(10)
    el = time.time() - t_start
    okS, stt = call_entry("study_status", {}, timeout_s=120)
    info = {"ok": okS}
    if okS:
        d = stt.get("data", stt)
        for p, v in find_awareness(d):
            if p.endswith("/enabled") or "config" in p:
                info["awareness@" + p.split("/config")[-1]] = v.get("enabled")
                break
        sb = supervision_bits(d)
        info["sup_keys"] = len(sb)
        for k, v in sb.items():
            if v not in (None, "", False, 0, "<dict:0>"):
                supv_seen[k] = v
        recent = d.get("recent_screen_classifications") or []
        info["recent_cls"] = len(recent)
    samples.append((el, info))
    out("  t=%4.0fs  %s" % (el, json.dumps(info, ensure_ascii=False)[:280]))
out("")
out("    distinct non-empty supervision signals observed: %d" % len(supv_seen))
for k in sorted(supv_seen)[:12]:
    out("      %s = %s" % (k, str(supv_seen[k])[:100]))

# ---------------------------------------------------- 5. logs
out("")
out("### 5. plugin logs (awareness-related lines)")
st, b = http("/plugin/%s/logs?tail=400" % PLUGIN, timeout=60)
if st == 200:
    txt = b.decode("utf-8", "replace")
    hits = [ln for ln in txt.splitlines()
            if any(t in ln.lower() for t in ("awareness", "activity buffer",
                                             "push_message", "supervision"))]
    out("    matched %d lines (showing up to 20)" % len(hits))
    for ln in hits[-20:]:
        out("      " + ln[:170])
else:
    out("    logs endpoint http %s" % st)

# ---------------------------------------------------- 6. revert
out("")
out("### 6. revert")
st, b = http("/plugin/%s/config" % PLUGIN, "PUT",
             {"config": user_config(pristine)})
out("    PUT pristine (stripped) -> %s" % st)
st, b = http("/plugin/%s/reload" % PLUGIN, "POST", {}, timeout=120)
out("    reload -> %s" % st)
t0 = time.time()
ready2 = False
while time.time() - t0 < 240:
    time.sleep(3)
    okS, _ = call_entry("study_status", {}, timeout_s=60)
    if okS:
        ready2 = True
        break
if not ready2:
    st, b = http("/plugin/%s/start" % PLUGIN, "POST", {}, timeout=180)
    out("    fallback start -> %s" % st)
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(3)
        okS, _ = call_entry("study_status", {}, timeout_s=60)
        if okS:
            ready2 = True
            break
st, b = http("/plugin/%s/config" % PLUGIN)
final_enabled = ((jbody(b).get("config") or {}).get("study") or {}) \
    .get("awareness", {}).get("enabled")
out("    plugin ready=%s  final study.awareness.enabled = %r (pristine=%r)"
    % (ready2, final_enabled, enabled_before))
out("    REVERT %s" % ("OK" if (ready2 and final_enabled == enabled_before)
                       else "FAILED - NEEDS MANUAL CHECK"))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
