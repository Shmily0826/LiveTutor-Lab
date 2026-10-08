#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bounded retry of the Electron desktop shell with several flag variants.
For each variant: launch, poll for windows / child processes / new ports,
then capture stdout+stderr and terminate ONLY the pid tree we started.
"""
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(APP, "N.E.K.O.exe")
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EVID = os.path.join(RAW, "evidence", "shell-retry.txt")
os.makedirs(os.path.dirname(EVID), exist_ok=True)
_lines = []


def out(m=""):
    print(m)
    _lines.append(str(m))


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
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
            vis = u32.IsWindowVisible(hwnd)
            found.append((pid.value, hwnd, vis, buf.value[:120], cn.value[:80]))
        return True

    u32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def kill(pid):
    h = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if h:
        k32.TerminateProcess(h, 1)
        k32.CloseHandle(h)


def listening_ports():
    r = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True)
    res = set()
    for line in r.stdout.splitlines():
        if "LISTENING" in line:
            parts = line.split()
            if len(parts) >= 2:
                res.add(parts[1])
    return res


BASE_ENV = dict(os.environ)
BASE_ENV.update({
    "NEKO_STORAGE_SELECTED_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_ANCHOR_ROOT": os.path.join(RAW, "neko-store"),
    "NEKO_STORAGE_CLOUDSAVE_ROOT": os.path.join(RAW, "neko-store", "cloudsave"),
    "PYTHONIOENCODING": "utf-8",
    "ELECTRON_ENABLE_LOGGING": "1",
    "ELECTRON_LOG_FILE": os.path.join(RAW, "evidence", "electron-retry.log"),
})

VARIANTS = [
    ("no-args", [], {}),
    ("disable-gpu", ["--disable-gpu"], {}),
    ("no-sandbox", ["--no-sandbox"], {}),
    ("gpu+swrast", ["--disable-gpu", "--no-sandbox", "--disable-software-rasterizer"], {}),
    ("in-process-gpu", ["--in-process-gpu"], {}),
]

WAIT = 25

for name, args, extra_env in VARIANTS:
    out("")
    out("=" * 74)
    out("VARIANT %s   args=%s" % (name, args))
    out("=" * 74)
    env = dict(BASE_ENV)
    env.update(extra_env)
    before = snapshot()
    ports_before = listening_ports()
    logf = open(os.path.join(RAW, "evidence", "shell-retry-%s.log" % name), "w", encoding="utf-8")
    try:
        p = subprocess.Popen([EXE] + args, cwd=APP, env=env,
                             stdout=logf, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL)
    except Exception as e:
        out("  LAUNCH FAILED: %s" % e)
        continue
    out("  launched pid=%d" % p.pid)
    root = p.pid
    t0 = time.time()
    seen_children = {}
    seen_windows = {}
    while time.time() - t0 < WAIT:
        time.sleep(1.0)
        snap = snapshot()
        tree = set()
        for pid, (ppid, exe, th) in snap.items():
            if pid == root or ppid == root:
                tree.add(pid)
        for pid in tree:
            if pid != root and pid not in seen_children:
                seen_children[pid] = (snap[pid][1], snap[pid][2])
        for (pid, hwnd, vis, title, cls) in windows_of(tree):
            seen_windows[hwnd] = (pid, vis, title, cls)
        if p.poll() is not None:
            out("  EXITED at %.1fs rc=%s" % (time.time() - t0, p.returncode))
            break
    alive = p.poll() is None
    out("  alive after %ds: %s   rc=%s" % (WAIT, alive, p.returncode))
    snap = snapshot()
    if root in snap:
        out("  root threads=%d" % snap[root][2])
    out("  child processes: %s" % (seen_children or "NONE"))
    out("  windows: %s" % ("NONE" if not seen_windows else ""))
    for hwnd, (pid, vis, title, cls) in seen_windows.items():
        out("     pid=%d visible=%s class=%r title=%r" % (pid, vis, cls, title))
    new_ports = sorted(listening_ports() - ports_before)
    out("  new listening ports: %s" % (new_ports or "NONE"))
    logf.close()
    # terminate only our own tree
    if alive:
        kill(root)
        time.sleep(1.0)
        snap2 = snapshot()
        for pid, (ppid, exe, th) in snap2.items():
            if ppid == root:
                kill(pid)
        out("  terminated pid=%d and its children" % root)
    logpath = os.path.join(RAW, "evidence", "shell-retry-%s.log" % name)
    try:
        sz = os.path.getsize(logpath)
        out("  stdout/stderr log: %d bytes" % sz)
        if sz:
            with open(logpath, encoding="utf-8", errors="replace") as f:
                txt = f.read()[:1500]
            out("  ---- log head ----")
            for ln in txt.splitlines()[:25]:
                out("     " + ln)
    except Exception as e:
        out("  log err %s" % e)

with open(EVID, "w", encoding="utf-8") as f:
    f.write("\n".join(_lines))
out("\nevidence -> %s" % EVID)
