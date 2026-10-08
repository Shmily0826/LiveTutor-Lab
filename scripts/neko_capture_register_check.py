#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify whether the Electron renderer's desktop-capture bridge registers with
the backend: GET the page, then re-read /api/capture/health.
"""
import json
import time
import urllib.request
import urllib.error

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MBASE = "http://127.0.0.1:48911"


def get(path, t=45):
    try:
        with OPENER.open(MBASE + path, timeout=t) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


def health():
    st, b = get("/api/capture/health", 30)
    return st, b.decode("utf-8", "replace")[:200]


print("=" * 70)
print("capture bridge registration check")
print("=" * 70)
print("before page fetch : /api/capture/health -> %s %s" % health())

for page in ("/", "/web_chat_compact"):
    st, b = get(page, 45)
    print("GET %-18s -> %s  (%d bytes)" % (page, st, len(b) if b else 0))

for i in range(8):
    time.sleep(3)
    st, body = health()
    print("t+%2ds  /api/capture/health -> %s %s" % ((i + 1) * 3, st, body))
    if st == 200:
        break

print("")
print("=== health summary ===")
for p in ("/api/capture/health", "/api/get_window_title", "/api/system/status"):
    st, b = get(p, 30)
    print("%-26s %s  %s" % (p, st, b.decode("utf-8", "replace")[:260]))
