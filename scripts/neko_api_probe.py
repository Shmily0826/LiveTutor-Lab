#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fetch the live OpenAPI route inventory from the running N.E.K.O backend and
bucket it by capability area. Writes benchmarks/raw/neko-routes-live.txt.
"""
import json
import os
import time
import urllib.request
import urllib.error

RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:48911"

BUCKETS = {
    "study/tutor": ["study", "tutor", "lesson", "quiz", "exercise", "master", "concept"],
    "plugin": ["plugin"],
    "screen/capture/ocr": ["screen", "capture", "screenshot", "ocr", "window"],
    "voice/audio/tts": ["voice", "audio", "tts", "asr", "microphone", "speech"],
    "avatar/live2d": ["avatar", "live2d", "vrm", "pet", "model"],
    "memory": ["memory"],
    "proactive": ["proactive", "activity"],
    "agent/tools": ["agent", "tool", "mcp"],
    "config/provider": ["config"],
}


def get(path, timeout=30):
    t = time.time()
    try:
        with OPENER.open(BASE + path, timeout=timeout) as r:
            return r.status, r.read(), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(), (time.time() - t) * 1000
    except Exception as e:
        return None, str(e).encode(), (time.time() - t) * 1000


st, body, ms = get("/openapi.json")
print("/openapi.json ->", st, "%d bytes in %.0fms" % (len(body), ms))
if st != 200:
    raise SystemExit(1)

spec = json.loads(body)
paths = sorted(spec.get("paths", {}).keys())
with open(os.path.join(RAW, "neko-routes-live.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(paths))
with open(os.path.join(RAW, "neko-openapi-live.json"), "wb") as f:
    f.write(body)

print("TOTAL ROUTES:", len(paths))

counts = {k: [] for k in BUCKETS}
for p in paths:
    lp = p.lower()
    for b, keys in BUCKETS.items():
        if any(k in lp for k in keys):
            counts[b].append(p)

for b in BUCKETS:
    print("\n=== %s : %d ===" % (b, len(counts[b])))
    for p in counts[b][:60]:
        print("   ", p)
    if len(counts[b]) > 60:
        print("    ... %d more" % (len(counts[b]) - 60))
