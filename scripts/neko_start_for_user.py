#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Start N.E.K.O for a HUMAN to use: backend first, then the Electron shell.

Two hard-won constraints baked in here:

1. ELECTRON_RUN_AS_NODE is exported by the ambient shell.  Every launch that
   inherits it silently degrades into bare `node` mode (no windows, rc=9 on
   Chromium flags).  Drop it from the child env.
2. The GPU process crashes with 0xC0000005 on this box, so Chromium needs
   --disable-gpu --disable-gpu-sandbox --no-sandbox.

Prints both PIDs.  Those PIDs are the ONLY things allowed to be terminated
later; quit the app from its tray icon instead whenever possible, because
killing it mid-tutorial skips the cursor-restore finally block and leaves all
18 system cursors transparent.
"""
import ctypes
import ctypes.wintypes as wintypes
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
APP = os.path.join(RAW, "neko-app")
BIN = os.path.join(APP, "resources", "bin")
SERVER = os.path.join(BIN, "projectneko_server.exe")
EXE = os.path.join(APP, "N.E.K.O.exe")
STORE = os.path.join(RAW, "neko-store")
EVID = os.path.join(RAW, "evidence")
PIDFILE = os.path.join(EVID, "neko-pids.txt")

ARGS = ["--disable-gpu", "--disable-gpu-sandbox", "--no-sandbox"]

os.makedirs(STORE, exist_ok=True)
os.makedirs(EVID, exist_ok=True)


def get(path, timeout=6):
    url = "http://127.0.0.1:48911" + path
    req = urllib.request.Request(url)
    req.add_header("Connection", "close")
    # avoid the ~2s proxy stall
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t = time.time()
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read(2000).decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000


# ---------------------------------------------------------------- backend
env = dict(os.environ)
env.pop("ELECTRON_RUN_AS_NODE", None)
env.update({
    "NEKO_STORAGE_SELECTED_ROOT": STORE,
    "NEKO_STORAGE_ANCHOR_ROOT": STORE,
    "NEKO_STORAGE_CLOUDSAVE_ROOT": os.path.join(STORE, "cloudsave"),
    "PYTHONIOENCODING": "utf-8",
})

st, body, ms = get("/health", timeout=3)
if st == 200:
    print("backend already listening, not starting a second one")
    backend_pid = None
else:
    blf = open(os.path.join(RAW, "neko-backend-user.log"), "wb")
    bp = subprocess.Popen([SERVER], cwd=BIN, env=env, stdout=blf, stderr=subprocess.STDOUT)
    backend_pid = bp.pid
    print("backend starting pid=%d" % backend_pid)
    up = None
    for t in (5, 10, 15, 20, 28, 38, 50, 65, 80):
        time.sleep(t - (0 if up is None else 999))
        st, body, ms = get("/health", timeout=5)
        print("  t=%2ds /health -> %s (%.0f ms)" % (t, st, ms))
        if st == 200:
            up = t
            break
        if bp.poll() is not None:
            print("  backend exited rc=%s" % bp.returncode)
            break
    if up is None:
        print("BACKEND DID NOT COME UP; aborting before touching the shell")
        sys.exit(1)
    print("backend up in ~%ds" % up)

st, body, ms = get("/api/system/status", timeout=8)
print("storage gate: %s" % (body or "").replace("\n", " ")[:300])

# ---------------------------------------------------------------- shell
logf = open(os.path.join(EVID, "shell-user.log"), "w", encoding="utf-8")
sp = subprocess.Popen([EXE] + ARGS, cwd=APP, env=env, stdout=logf,
                      stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
shell_pid = sp.pid
print("shell starting pid=%d args=%s" % (shell_pid, " ".join(ARGS)))

# ---------------------------------------------------------------- windows
u32 = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows_of(pid):
    found = []

    def cb(hwnd, _l):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(hwnd):
            ln = u32.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(ln + 1)
            u32.GetWindowTextW(hwnd, b, ln + 1)
            c = ctypes.create_unicode_buffer(200)
            u32.GetClassNameW(hwnd, c, 200)
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((c.value, r.right - r.left, r.bottom - r.top, b.value))
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return found


t0 = time.time()
seen = []
while time.time() - t0 < 90:
    time.sleep(3)
    for w in windows_of(shell_pid):
        if w not in seen:
            seen.append(w)
            print("  @%5.1fs  %-26s %4dx%-4d  %r" % (time.time() - t0, w[0], w[1], w[2], w[3]))
    if sp.poll() is not None:
        print("shell exited rc=%s at %.1fs" % (sp.returncode, time.time() - t0))
        break

with open(PIDFILE, "w", encoding="utf-8") as f:
    f.write("backend_pid=%s\n" % backend_pid)
    f.write("shell_pid=%s\n" % shell_pid)
print("")
print("pids written to %s" % PIDFILE)
print("shell alive:", sp.poll() is None)
