#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run the shell with no args, wait up to N seconds, report exit code + output."""
import os
import subprocess
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
WAIT = int(os.environ.get("NEKO_WAIT", "70"))

env = dict(os.environ)
env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
env["NEKO_STORAGE_CLOUDSAVE_ROOT"] = STORE
env["PYTHONIOENCODING"] = "utf-8"

t0 = time.time()
try:
    p = subprocess.run([EXE], cwd=BASE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=WAIT)
    dt = time.time() - t0
    out = p.stdout.decode("utf-8", "replace")
    print("EXITED rc=%s after %.1fs, output %d bytes" % (p.returncode, dt, len(out)))
    print(out[:5000])
except subprocess.TimeoutExpired as e:
    print("STILL RUNNING after %ds (good)" % WAIT)
    out = (e.stdout or b"").decode("utf-8", "replace")
    print("partial output %d bytes:" % len(out))
    print(out[:5000])
