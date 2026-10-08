#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Awareness probe 6 - cadence measurement with the CORRECT observation path.

probe 5 proved: DB kv row edit -> runtime awareness.enabled=True (loop task
created silently).  probe 5 failed to observe ticks only because it read
supervision from the wrong payload path.  Correct path (source-read):

    study_status data.habit.supervision.last_activity_at
    (service.py build_status_payload "habit" -> ui_api.py "supervision"
     -> supervision.py status()["last_activity_at"], updated by
     observe_activity() which awareness_tick calls every tick)

Plan:
  1. backup db files; stop plugin; flip kv row awareness.enabled=true
  2. start; verify runtime echo True
  3. sample 330 s every 5 s:
       - habit.supervision.last_activity_at deltas -> real tick intervals
       - /plugin/messages?plugin_id=study_companion -> awareness push
         (push_to_llm_interval_seconds=300, so a push should land once)
  4. REVERT: stop, restore row, start, verify False
"""
import json
import os
import shutil
import sqlite3
import time
import urllib.error
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
DB = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
      r"\plugins\study_companion\data\study_companion.db")
BAK_DB = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
          r"\study_companion.db.bak-awareness")
BAK_ROW = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
           r"\study_companion.kv-config-row.bak.json")
EVID = (r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
        r"\study-runtime11-awareness-cadence.txt")
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


def read_ts():
    ok, data = call_entry("study_status", {}, timeout_s=90)
    if not ok:
        return None
    d = data.get("data", data)
    try:
        return (d.get("habit") or {}).get("supervision") or {}
    except Exception:
        return {}


def read_kv_row():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute("SELECT value FROM kv WHERE key='config'").fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else None


def write_kv_row(value):
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO kv (key, value, updated_at) VALUES ('config', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            (json.dumps(value, ensure_ascii=False, sort_keys=True), time.time()))
        conn.commit()
    finally:
        conn.close()


out("=" * 70)
out("Awareness probe 6 (cadence)  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        shutil.copyfile(DB + ext, BAK_DB + ext)
out("### 1. db backed up")

st, _ = http("/plugin/%s/stop" % PLUGIN, "POST", {})
out("### 2. stop -> %s" % st)
time.sleep(2)
row = read_kv_row()
json.dump(row, open(BAK_ROW, "w", encoding="utf-8"),
          ensure_ascii=False, sort_keys=True, indent=1)
out("    row backed up; awareness.enabled=%r"
    % ((row.get("awareness") or {}).get("enabled")))
row["awareness"]["enabled"] = True
write_kv_row(row)
st, _ = http("/plugin/%s/start" % PLUGIN, "POST", {})
out("    start -> %s" % st)
t0 = time.time()
while time.time() - t0 < 240:
    time.sleep(3)
    ok, _ = call_entry("study_status", {}, timeout_s=60)
    if ok:
        break
sup = read_ts() or {}
out("    ready; supervision.enabled=%s last_activity_at=%r"
    % (sup.get("enabled"), sup.get("last_activity_at")))

out("### 3. sampling 330 s (5 s interval)")
t_start = time.time()
prev, intervals, msgs_seen = None, [], []
while time.time() - t_start < 330:
    time.sleep(5)
    el = time.time() - t_start
    sup = read_ts() or {}
    la = sup.get("last_activity_at")
    delta = None
    if la and prev and la != prev:
        delta = la - prev
        intervals.append(delta)
    if la:
        prev = la
    st, b = http("/plugin/messages?plugin_id=%s&max_count=10" % PLUGIN)
    if st == 200:
        msgs = jbody(b).get("messages") or []
        for m in msgs:
            mid = m.get("id") or m.get("message_id") or id(m)
            if mid not in [x[0] for x in msgs_seen]:
                msgs_seen.append((mid, m))
    out("  t=%4.0fs enabled=%s sensor=%s level=%-6s last_act=%s %s"
        % (el, sup.get("enabled"), sup.get("sensor_available"),
           str(sup.get("reminder_level"))[:6],
           ("%.0f" % la) if isinstance(la, (int, float)) and la else la,
           ("tick delta %.1f s" % delta) if delta else ""))
out("")
if intervals:
    iv = sorted(intervals)
    out("TICKS: %d observed; interval min/median/max = %.1f / %.1f / %.1f s"
        % (len(iv), iv[0], iv[len(iv) // 2], iv[-1]))
else:
    out("TICKS: none observed (last_activity_at never moved)")
out("MESSAGES: %d distinct message(s) seen" % len(msgs_seen))
for mid, m in msgs_seen[:5]:
    out("  msg keys=%s" % sorted(m.keys()))
    out("  msg preview=%s" % json.dumps(m, ensure_ascii=False)[:300])

# revert
out("")
out("### 4. revert")
st, _ = http("/plugin/%s/stop" % PLUGIN, "POST", {})
out("    stop -> %s" % st)
time.sleep(2)
orig = json.load(open(BAK_ROW, encoding="utf-8"))
write_kv_row(orig)
st, _ = http("/plugin/%s/start" % PLUGIN, "POST", {})
out("    start -> %s" % st)
t0 = time.time()
while time.time() - t0 < 240:
    time.sleep(3)
    ok, _ = call_entry("study_status", {}, timeout_s=60)
    if ok:
        break
sup = read_ts() or {}
cfg_ok, data = call_entry("study_status", {}, timeout_s=90)
en = None
if cfg_ok:
    d = data.get("data", data)
    en = ((d.get("config") or {}).get("awareness") or {}).get("enabled")
out("    final awareness.enabled=%r" % en)
out("    REVERT %s" % ("OK" if en is False else "CHECK NEEDED"))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
