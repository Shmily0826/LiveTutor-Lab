#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch N.E.K.O so that it SURVIVES the agent's tool call.

Why this file exists
--------------------
Launching with subprocess.Popen from a script that runs inside the agent's Bash
tool call puts the app inside the harness' job object.  When the tool call
returns, the job is torn down and every descendant dies.  That is what killed
the app mid-tutorial twice: the launch script finished, the call returned, the
app was reaped, and because the tutorial was still holding the hidden system
cursor, the user was left with no mouse pointer.

shell32.ShellExecuteW hands the launch to explorer.exe, so the new process is
NOT a descendant of anything the harness can reap.

Env caveat: ShellExecute inherits explorer's environment, not ours.  That is
fine here because (a) it also means ELECTRON_RUN_AS_NODE is absent, which is
what we want, and (b) NEKO_STORAGE_* is only read by the backend (and by
src__feedback.js for the feedback path).  The backend is already up.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
ARGS = "--disable-gpu --disable-gpu-sandbox --no-sandbox"
WATCH = 25

shell32 = ctypes.windll.shell32
shell32.ShellExecuteW.restype = wintypes.HINSTANCE
shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                  wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]

rc = shell32.ShellExecuteW(None, "open", EXE, ARGS, BASE, 1)  # SW_SHOWNORMAL
print("ShellExecuteW rc=%d (%s)" % (rc, "ok" if rc > 32 else "FAILED"))
if rc <= 32:
    raise SystemExit(1)

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def visible_windows():
    out = []

    def cb(hwnd, _l):
        if u32.IsWindowVisible(hwnd):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            n = u32.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, b, n + 1)
            if "N.E.K.O" in b.value or "Project" in b.value:
                out.append((p.value, b.value))
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return out


t0 = time.time()
seen = set()
while time.time() - t0 < WATCH:
    time.sleep(3)
    for item in visible_windows():
        if item not in seen:
            seen.add(item)
            print("  @%5.1fs pid=%-7d %r" % (time.time() - t0, item[0], item[1]))

print("\nwindows: %d" % len(seen))
print("these belong to explorer-spawned processes; they are NOT in this call's job")
