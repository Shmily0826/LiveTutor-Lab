#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Decisive experiment: does the study_companion PLUGIN PROCESS ever see the
user-override config (neko-store/.../config/plugin.toml)?

Facts so far:
  - PUT /plugin/{id}/config persists the override file (mtime + content proof)
    and GET /config returns the merged view (server side).
  - PUT + POST reload -> running cfg echo still enabled=False.
      => reload start reads BASE toml only (or the override never reaches it).
  - hot-update permanent persistence is NOT implemented (binary strings).
      => only temporary (in-memory, running process) hot-apply exists.

This probe:
  1. baseline echo
  2. PUT override enabled=true  -> POST stop -> POST start  -> echo
  3. if still False: hot-update temporary {study.awareness.enabled=true}
     -> echo immediately (running process, no restart)
  4. REVERT: PUT override enabled=false -> stop -> start -> verify
Prints only booleans/timings; never touches screen content.
"""
import copy
import json
import time
import urllib.error
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PBASE = "http://127.0.0.1:48916"
PLUGIN = "study_companion"
FRAMEWORK = ("plugin", "plugin_runtime", "plugin_state")


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


def cfg_of(b):
    return jbody(b).get("config") or {}


def awareness_enabled(cfg):
    return ((cfg.get("study") or {}).get("awareness") or {}).get("enabled")


def user_cfg(cfg):
    return {k: copy.deepcopy(v) for k, v in cfg.items() if k not in FRAMEWORK}


def set_awareness(cfg, value):
    c = user_cfg(cfg)
    c.setdefault("study", {})["awareness"]["enabled"] = value
    return c


def stop_start():
    st, b = http("/plugin/%s/stop" % PLUGIN, "POST", {})
    print("  stop -> %s %s" % (st, b[:120].decode("utf-8", "replace")))
    time.sleep(2)
    st, b = http("/plugin/%s/start" % PLUGIN, "POST", {})
    print("  start -> %s %s" % (st, b[:120].decode("utf-8", "replace")))
    t0 = time.time()
    ok = False
    while time.time() - t0 < 240:
        time.sleep(3)
        st, b = http("/plugin/%s/config" % PLUGIN, timeout=15)
        if st != 200:
            continue
        okS, _data = call_entry("study_status", {}, timeout_s=60)
        if okS:
            ok = True
            break
    print("  ready=%s (%.0f s)" % (ok, time.time() - t0))
    return ok


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


def runtime_echo():
    """awareness.enabled as seen INSIDE the running plugin (status cfg echo)."""
    ok, data = call_entry("study_status", {}, timeout_s=90)
    if not ok:
        return None
    d = data.get("data", data)
    aw = ((d.get("config") or {}).get("awareness")) or {}
    return aw.get("enabled")


print("=" * 70)
print("stop/start + hot-update experiment  %s" % time.strftime("%H:%M:%S"))

st, b = http("/plugin/%s/config" % PLUGIN)
pristine = cfg_of(b)
base_enabled = awareness_enabled(pristine)
print("### 0. merged cfg enabled=%r" % base_enabled)
print("    runtime echo before anything: %r" % runtime_echo())

# --- 2. override true + stop/start
st, b = http("/plugin/%s/config" % PLUGIN, "PUT",
             {"config": set_awareness(pristine, True)})
print("### 2. PUT enabled=true -> %s" % st)
if stop_start():
    print("    runtime echo after PUT+stop/start: %r" % runtime_echo())

st, b = http("/plugin/%s/config" % PLUGIN)
print("    merged GET now: %r" % awareness_enabled(cfg_of(b)))

# --- 3. hot-update temporary
st, b = http("/plugin/%s/config/hot-update" % PLUGIN, "POST",
             {"config": {"study": {"awareness": {"enabled": True}}},
              "mode": "temporary"})
print("### 3. hot-update temporary -> %s  %s"
      % (st, b[:300].decode("utf-8", "replace")))
print("    runtime echo after hot-update: %r" % runtime_echo())

# --- 4. revert
st, b = http("/plugin/%s/config" % PLUGIN, "PUT",
             {"config": set_awareness(pristine, False)})
print("### 4. revert PUT enabled=false -> %s" % st)
if stop_start():
    print("    runtime echo after revert+stop/start: %r" % runtime_echo())
st, b = http("/plugin/%s/config" % PLUGIN)
print("    final merged GET: %r (pristine %r)"
      % (awareness_enabled(cfg_of(b)), base_enabled))
