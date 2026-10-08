#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proper first launch: attach to the already-running backend, let the shell
create its own pet/main/terminal windows, and verify them by enumeration.

Drops ELECTRON_RUN_AS_NODE (the ambient shell exports it, which made every
earlier launch silently degrade into `node` mode).
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(APP, "N.E.K.O.exe")
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
ARGS = os.environ.get("NEKO_ARGS", "").split() if os.environ.get("NEKO_ARGS") else []
LOG = os.environ.get("NEKO_LOG", "shell-console.log")
WAIT = int(os.environ.get("NEKO_WAIT", "120"))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def snapshot():
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == -1:
        return {}
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    res = {}
    ok = k32.Process32FirstW(h, ctypes.byref(pe))
    while ok:
        res[pe.th32ProcessID] = (pe.th32ParentProcessID, pe.szExeFile, pe.cntThreads)
        ok = k32.Process32NextW(h, ctypes.byref(pe))
    k32.CloseHandle(h)
    return res


EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows_of(pid):
    found = []

    def cb(hwnd, _l):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            ln = u32.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(ln + 1)
            u32.GetWindowTextW(hwnd, b, ln + 1)
            c = ctypes.create_unicode_buffer(200)
            u32.GetClassNameW(hwnd, c, 200)
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((bool(u32.IsWindowVisible(hwnd)), c.value,
                          r.right - r.left, r.bottom - r.top, b.value))
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return found


def alive(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if h:
        k32.CloseHandle(h)
        return True
    return False


env = dict(os.environ)
env.pop("ELECTRON_RUN_AS_NODE", None)
env.update({
    "NEKO_STORAGE_SELECTED_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_ANCHOR_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_CLOUDSAVE_ROOT": os.path.join(RAW, "neko-store", "cloudsave"),
    "PYTHONIOENCODING": "utf-8",
})

logf = open(os.path.join(RAW, "evidence", LOG), "w", encoding="utf-8")
p = subprocess.Popen([EXE] + ARGS, cwd=APP, env=env, stdout=logf,
                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
pid = p.pid
print("launched pid=%d args=%s at %s" % (pid, ARGS, time.strftime("%H:%M:%S")))

t0 = time.time()
last = {}
while time.time() - t0 < WAIT:
    time.sleep(2.0)
    if not alive(pid):
        print("pid %d gone after %.1fs rc=%s" % (pid, time.time() - t0, p.poll()))
        break
    for w in windows_of(pid):
        last[w] = time.time() - t0
        if list(last).count(w) == 1:
            pass

print("")
print("alive: %s" % alive(pid))
print("windows seen for pid %d (%d):" % (pid, len(last)))
for (vis, cls, w, h, title), at in sorted(last.items(), key=lambda x: x[1]):
    print("   @%5.1fs visible=%-5s %-28s %4dx%-4d  %r" % (at, vis, cls, w, h, title))
if not last:
    print("   NONE")

logf.close()
lp = os.path.join(RAW, "evidence", LOG)
print("")
print("log: %s (%d bytes)" % (lp, os.path.getsize(lp)))
