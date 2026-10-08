#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Awareness probe 4 - THE ONLY WORKING PATH: edit the BASE toml.

Proven so far (probe v2/v3):
  - study_update_settings_config: no awareness branch (source read)
  - PUT /plugin/{id}/config: writes override toml, but plugin process reads
    BASE toml only (runtime echo False after stop/start; merged GET True)
  - hot-update temporary: 200 hot_reloaded=true, handler_called=false,
    runtime echo unchanged -> running _cfg is never replaced
  - hot-update permanent: persistence NOT implemented (binary strings)

So: 1-line edit of the shipped base toml + plugin restart.

Steps:
  1. backup  resources/bin/plugin/plugins/study_companion/plugin.toml
  2. flip    [study.awareness] enabled = false  ->  true   (section-scoped)
  3. stop + start plugin, verify runtime echo == True
  4. sample 90 s: supervision.last_activity_at diffs = real tick cadence
  5. REVERT: restore backup, stop + start, verify echo False + frozen ts
"""
import json
import re
import shutil
import time
import urllib.error
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
TOML = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
        r"\resources\bin\plugin\plugins\study_companion\plugin.toml")
BAK = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
       r"\study_companion.plugin.toml.bak-awareness")
EVID = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
        r"\study-runtime9-awareness-basetoml.txt")
_lines = []


def out(m=""):
    print(m)
    _lines.append(str(m))


def http(path, method="GET", data=None, timeout=120):
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


def call_entry(entry, args=None, timeout_s=120):
    args = dict(args or {})
    args.setdefault("locale", "zh-CN")
    st, body = http("/runs", "POST",
                    {"plugin_id": PLUGIN, "entry_id": entry, "args": args})
    if st != 200:
        return False, None
    j = jbody(body)
    run_id = j.get("run_id") or j.get("id")
    delay, deadline = 0.25, time.time() + timeout_s
    last = {}
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
        return False, None
    st3, b3 = http("/runs/%s/export" % run_id)
    if st3 != 200:
        return False, None
    for it in (jbody(b3).get("items") or []):
        if it.get("type") == "json" and it.get("json"):
            jj = it["json"]
            if jj.get("success") is False:
                return False, None
            return True, (jj.get("data") if "data" in jj else jj)
    return False, None


def runtime_state():
    ok, data = call_entry("study_status", {}, timeout_s=90)
    if not ok:
        return None, None
    d = data.get("data", data)
    aw = ((d.get("config") or {}).get("awareness")) or {}
    sup = {}
    try:
        sup = d["knowledge"]["habit"]["supervision"] or {}
    except Exception:
        for k, v in (d.get("habit") or {}).items():
            if k == "supervision":
                sup = v
    return aw.get("enabled"), sup.get("last_activity_at")


def restart_plugin():
    st, b = http("/plugin/%s/stop" % PLUGIN, "POST", {})
    out("  stop -> %s" % st)
    time.sleep(2)
    st, b = http("/plugin/%s/start" % PLUGIN, "POST", {})
    out("  start -> %s" % st)
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(3)
        ok, _ = call_entry("study_status", {}, timeout_s=60)
        if ok:
            out("  ready after %.0f s" % (time.time() - t0))
            return True
    out("  NOT READY after 240 s")
    return False


out("=" * 70)
out("Awareness probe 4 (base-toml path)  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

# 1. backup + flip
shutil.copyfile(TOML, BAK)
src = open(TOML, encoding="utf-8").read()
section = re.search(r"\[study\.awareness\][^\[]*", src, re.S).group(0)
assert "enabled = false" in section, "unexpected toml shape"
new_section = section.replace("enabled = false", "enabled = true", 1)
open(TOML, "w", encoding="utf-8", newline="\n").write(src.replace(section, new_section, 1))
out("### 1. base toml flipped enabled=false -> true (backup: %s)" % BAK)

# 2. restart + verify
out("### 2. restart plugin")
ok = restart_plugin()
en, ts = runtime_state()
out("    runtime echo: awareness.enabled=%r  last_activity_at=%r" % (en, ts))

if en is True:
    # 3. cadence sampling
    out("### 3. sampling 90 s (last_activity_at diffs = tick intervals)")
    t_start = time.time()
    prev, intervals = None, []
    while time.time() - t_start < 90:
        time.sleep(5)
        el = time.time() - t_start
        en2, ts2 = runtime_state()
        delta = None
        if ts2 and prev and ts2 != prev:
            delta = ts2 - prev
            intervals.append(delta)
        prev = ts2 if ts2 else prev
        out("  t=%4.0fs enabled=%s last_activity_at=%s %s"
            % (el, en2, ts2, ("tick delta %.1f s" % delta) if delta else ""))
    if intervals:
        intervals.sort()
        out("    ticks observed: %d  interval min/median/max = %.1f / %.1f / %.1f s"
            % (len(intervals), intervals[0],
               intervals[len(intervals) // 2], intervals[-1]))
    else:
        out("    NO tick deltas observed in 90 s")
    # logs
    st, b = http("/plugin/%s/logs?tail=200" % PLUGIN, timeout=60)
    if st == 200:
        txt = b.decode("utf-8", "replace")
        hits = [ln for ln in txt.splitlines() if "awareness" in ln.lower()]
        out("    log lines mentioning awareness: %d" % len(hits))
        for ln in hits[-8:]:
            out("      " + ln[:170])

# 4. revert
out("### 4. revert")
shutil.copyfile(BAK, TOML)
out("    base toml restored from backup")
ok = restart_plugin()
en2, ts2 = runtime_state()
out("    runtime echo after revert: awareness.enabled=%r  last_activity_at=%r"
    % (en2, ts2))
out("    REVERT %s" % ("OK" if en2 is False else "CHECK NEEDED"))
cur = open(TOML, encoding="utf-8").read()
out("    toml enabled line now: %r"
    % re.search(r"\[study\.awareness\][^\[]*", cur, re.S).group(0).splitlines()[1])

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
