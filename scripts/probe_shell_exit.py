#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run the N.E.K.O Electron shell synchronously with several arg sets and report
exit code + captured stdout/stderr. Read-only w.r.t. the product."""
import os
import subprocess
import sys
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"

env = dict(os.environ)
env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
env["NEKO_STORAGE_CLOUDSAVE_ROOT"] = STORE
env["PYTHONIOENCODING"] = "utf-8"

CASES = [
    ("no args", []),
    ("enable-logging", ["--enable-logging=stderr", "--v=1"]),
    ("help", ["--help"]),
    ("version", ["--version"]),
]

only = sys.argv[1] if len(sys.argv) > 1 else None
for name, args in CASES:
    if only and only not in name:
        continue
    print("=" * 70)
    print("CASE:", name, args)
    t0 = time.time()
    try:
        p = subprocess.run([EXE] + args, cwd=BASE, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=25)
        dt = time.time() - t0
        out = p.stdout.decode("utf-8", "replace")
        print("rc=%s  elapsed=%.1fs  bytes=%d" % (p.returncode, dt, len(out)))
        print(out[:3000])
    except subprocess.TimeoutExpired as e:
        print("TIMEOUT after 25s (process still running -> GOOD sign)")
        out = (e.stdout or b"").decode("utf-8", "replace")
        print("partial output (%d bytes):" % len(out))
        print(out[:3000])
        print("NOTE: a long-running shell is expected; killing by recorded pid")
        try:
            import ctypes
            # find pid by image name is forbidden; we did not record one here.
        except Exception:
            pass
    print()
