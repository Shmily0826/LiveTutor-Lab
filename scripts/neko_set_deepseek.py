#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Point N.E.K.O's ASSIST API at DeepSeek, using the key the user left in a local
file.  The key is read inside this process and POSTed to the backend; it is
NEVER printed, logged, or written anywhere.  Every diagnostic line masks it.

Why the ASSIST side only: Study Companion's semantic routing and knowledge
guidance run on the assist (text) channel.  The CORE channel is the realtime
voice websocket and is deliberately left on `free` until voice is tested.
"""
import json
import os
import sys
import urllib.error
import urllib.request

KEY_FILE = r"D:\CODE\API\new api.txt"
BASE = "http://127.0.0.1:48911"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def mask(s):
    if not s:
        return "(empty)"
    return "%s...%s(len=%d)" % (s[:6], s[-4:], len(s))


def api(path, method="GET", data=None, timeout=20):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode() if data is not None else None
    try:
        with OPENER.open(req, data=body, timeout=timeout) as r:
            return r.status, r.read(8000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


# ---------------------------------------------------------------- read key
raw = open(KEY_FILE, "r", encoding="utf-8", errors="replace").read()
candidates = [l.strip() for l in raw.splitlines() if l.strip().startswith("sk-")]
if not candidates:
    print("no sk- line found in key file; aborting without changing anything")
    sys.exit(1)
key = candidates[0]
print("key loaded: %s (value never shown)" % mask(key))

# ---------------------------------------------------------------- current
st, body = api("/api/config/core_api")
try:
    cur = json.loads(body)
except Exception:
    cur = {}
print("before: coreApi=%r assistApi=%r enableCustomApi=%r" % (
    cur.get("coreApi"), cur.get("assistApi"), cur.get("enableCustomApi")))

# ---------------------------------------------------------------- set
payload = {
    "assistApi": "deepseek",
    "assistApiKeyDeepseek": key,
}
st, body = api("/api/config/core_api", method="POST", data=payload, timeout=30)
print("POST /api/config/core_api -> %s" % st)
print("  %s" % (body or "")[:600].replace("\n", " "))

# ---------------------------------------------------------------- verify
st, body = api("/api/config/core_api")
try:
    now = json.loads(body)
except Exception:
    now = {}
print("after:  coreApi=%r assistApi=%r enableCustomApi=%r" % (
    now.get("coreApi"), now.get("assistApi"), now.get("enableCustomApi")))
print("after:  assistApiKeyDeepseek=%s" % mask(now.get("assistApiKeyDeepseek") or ""))
