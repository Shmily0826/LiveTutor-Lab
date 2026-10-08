#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Awareness probe 5 - the DB kv row is the config layer that actually wins.

Evidence chain:
  startup(): cfg = build_config(toml dump)  ->  cfg = store.load_config(cfg)
  store.load_config: merges kv row 'config' OVER the toml values
  _persist_state() runs on EVERY startup and save_config()s the full cfg
    => the DB row contains awareness.enabled=False from the first run on,
       and overrides every toml (base AND user override) forever after.
  (probe 4 proved even the shipped base toml flip is nullified.)

Steps (DB edited only while plugin is STOPPED; file-level backup first):
  1. copy study_companion.db (+ -wal/-shm) to evidence
  2. stop plugin; read kv['config']; verify awareness key; backup row JSON
  3. UPDATE row with awareness.enabled=true; start plugin
  4. verify runtime echo True; sample 90 s tick cadence via
     supervision.last_activity_at deltas; grab awareness log lines
  5. REVERT: stop, restore original row JSON, start, verify False
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
        r"\study-runtime10-awareness-dbrow.txt")
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
        pass
    return aw.get("enabled"), sup.get("last_activity_at")


def restart_plugin():
    st, _ = http("/plugin/%s/stop" % PLUGIN, "POST", {})
    out("  stop -> %s" % st)
    time.sleep(2)
    st, _ = http("/plugin/%s/start" % PLUGIN, "POST", {})
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


def read_kv_row():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT value FROM kv WHERE key='config'").fetchone()
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
out("Awareness probe 5 (DB kv row path)  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

# 1. file-level backup
for ext in ("", "-wal", "-shm"):
    src = DB + ext
    if os.path.exists(src):
        shutil.copyfile(src, BAK_DB + ext)
out("### 1. db files backed up -> %s*" % BAK_DB)

# 2. stop + read + backup row
st, _ = http("/plugin/%s/stop" % PLUGIN, "POST", {})
out("### 2. stop -> %s" % st)
time.sleep(2)
row = read_kv_row()
if row is None:
    out("FATAL: kv row 'config' missing")
    raise SystemExit(1)
json.dump(row, open(BAK_ROW, "w", encoding="utf-8"),
          ensure_ascii=False, sort_keys=True, indent=1)
out("    row backed up (%d top keys) -> %s" % (len(row), BAK_ROW))
out("    row awareness.enabled = %r" % ((row.get("awareness") or {}).get("enabled")))
row["awareness"]["enabled"] = True
write_kv_row(row)
out("    row updated: awareness.enabled=True")

# 3. start + verify
st, _ = http("/plugin/%s/start" % PLUGIN, "POST", {})
out("### 3. start -> %s" % st)
t0 = time.time()
while time.time() - t0 < 240:
    time.sleep(3)
    ok, _ = call_entry("study_status", {}, timeout_s=60)
    if ok:
        break
out("    ready after %.0f s" % (time.time() - t0))
en, ts = runtime_state()
out("    runtime echo: awareness.enabled=%r last_activity_at=%r" % (en, ts))

if en is True:
    out("### 4. sampling 90 s (tick deltas via supervision.last_activity_at)")
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
        if ts2:
            prev = ts2
        out("  t=%4.0fs enabled=%s last_activity_at=%s %s"
            % (el, en2, ts2, ("tick delta %.1f s" % delta) if delta else ""))
    if intervals:
        intervals.sort()
        out("    ticks: %d  interval min/median/max = %.1f / %.1f / %.1f s"
            % (len(intervals), intervals[0],
               intervals[len(intervals) // 2], intervals[-1]))
    else:
        out("    NO tick deltas in 90 s")
    st, b = http("/plugin/%s/logs?tail=200" % PLUGIN, timeout=60)
    if st == 200:
        hits = [ln for ln in b.decode("utf-8", "replace").splitlines()
                if "awareness" in ln.lower()]
        out("    log lines mentioning awareness: %d" % len(hits))
        for ln in hits[-8:]:
            out("      " + ln[:170])
else:
    out("### 4. skipped (enable failed again)")

# 5. revert
out("### 5. revert")
st, _ = http("/plugin/%s/stop" % PLUGIN, "POST", {})
out("    stop -> %s" % st)
time.sleep(2)
orig = json.load(open(BAK_ROW, encoding="utf-8"))
write_kv_row(orig)
out("    kv row restored (awareness.enabled=%r)"
    % ((orig.get("awareness") or {}).get("enabled")))
st, _ = http("/plugin/%s/start" % PLUGIN, "POST", {})
out("    start -> %s" % st)
t0 = time.time()
while time.time() - t0 < 240:
    time.sleep(3)
    ok, _ = call_entry("study_status", {}, timeout_s=60)
    if ok:
        break
en3, ts3 = runtime_state()
out("    runtime echo after revert: enabled=%r" % en3)
out("    REVERT %s" % ("OK" if en3 is False else "CHECK NEEDED"))

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence -> %s" % EVID)
