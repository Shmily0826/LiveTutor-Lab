#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch N.E.K.O.exe as a REAL Electron GUI app.
Root cause of all previous 'hangs': the ambient shell exports
ELECTRON_RUN_AS_NODE=1, which makes the Electron binary run as bare Node.
This script removes that variable from the child environment.
"""
import ctypes
import os
import subprocess
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(APP, "N.E.K.O.exe")
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "shell-real.txt")
os.makedirs(os.path.dirname(EVID), exist_ok=True)
_lines = []

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_TERMINATE = 0x0001


def out(m=""):
    print(m)
    _lines.append(str(m))


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


def children_of(root, snap=None):
    snap = snap or snapshot()
    return {pid: v for pid, v in snap.items() if v[0] == root}


EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows_of(pids):
    found = []

    def cb(hwnd, _l):
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            ln = u32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(ln + 1)
            u32.GetWindowTextW(hwnd, buf, ln + 1)
            cn = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(hwnd, cn, 256)
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((pid.value, bool(u32.IsWindowVisible(hwnd)),
                          buf.value[:140], cn.value[:60],
                          (r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def kill(pid):
    h = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if h:
        k32.TerminateProcess(h, 1)
        k32.CloseHandle(h)


env = dict(os.environ)
for k in ("ELECTRON_RUN_AS_NODE", "ELECTRON_NO_ATTACH_CONSOLE"):
    env.pop(k, None)
env.update({
    "NEKO_STORAGE_SELECTED_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_ANCHOR_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_CLOUDSAVE_ROOT": os.path.join(RAW, "neko-store", "cloudsave"),
    "PYTHONIOENCODING": "utf-8",
    "ELECTRON_ENABLE_LOGGING": "1",
})
out("ELECTRON_RUN_AS_NODE removed: %r" % env.get("ELECTRON_RUN_AS_NODE"))

logf = open(os.path.join(RAW, "evidence", "shell-real.log"), "w", encoding="utf-8")
p = subprocess.Popen([EXE], cwd=APP, env=env, stdout=logf, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
root = p.pid
out("launched pid=%d at %s" % (root, time.strftime("%H:%M:%S")))
out("")

WAIT = int(os.environ.get("NEKO_WAIT", "90"))
t0 = time.time()
seen_children, seen_windows = {}, {}
while time.time() - t0 < WAIT:
    time.sleep(1.0)
    snap = snapshot()
    tree = {root} | set(children_of(root, snap).keys())
    for pid in tree - {root}:
        if pid not in seen_children:
            seen_children[pid] = (snap[pid][1], snap[pid][2], time.time() - t0)
    for (pid, vis, title, cls, size) in windows_of(tree):
        seen_windows.setdefault((pid, cls, title), (vis, size, time.time() - t0))
    if p.poll() is not None:
        out("EXITED at %.1fs rc=%s" % (time.time() - t0, p.returncode))
        break

out("alive after %ds: %s rc=%s" % (WAIT, p.poll() is None, p.returncode))
snap = snapshot()
if root in snap:
    out("root threads=%d" % snap[root][2])
out("")
out("child processes (%d):" % len(seen_children))
for pid, (exe, th, at) in sorted(seen_children.items(), key=lambda x: x[1][2]):
    out("   pid=%-7d %-28s threads=%-4d  appeared@%.1fs" % (pid, exe, th, at))
out("")
out("windows (%d):" % len(seen_windows))
for (pid, cls, title), (vis, size, at) in seen_windows.items():
    out("   pid=%-7d visible=%-5s class=%-24s %dx%d  @%.1fs  title=%r"
        % (pid, vis, cls, size[0], size[1], at, title))
if not seen_windows:
    out("   NONE")

logf.close()
lp = os.path.join(RAW, "evidence", "shell-real.log")
sz = os.path.getsize(lp)
out("")
out("stdout/stderr log: %d bytes" % sz)
if sz:
    with open(lp, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    out("---- first 4000 chars ----")
    out(txt[:4000])

out("")
out("NOTE: process left running=%s (pid %d)" % (p.poll() is None, root))
out("kill it with: taskkill /PID %d /T /F  (only this pid)" % root)

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
print("\nevidence ->", EVID)
