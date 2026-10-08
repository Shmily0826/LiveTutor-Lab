#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch the N.E.K.O Electron shell detached and supervise it: process tree,
listening ports, visible top-level windows (desktop/avatar evidence), and the
backend HTTP surface. Runs for a fixed wall-clock budget, appending to a log.

Usage: neko_shell_supervise.py [seconds]
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

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
MON = os.path.join(RAW, "neko-shell-monitor.log")
SPAWN = os.path.join(RAW, "neko-shell-spawn.log")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 600

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(MON, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- process helpers ----------------
TH32CS_SNAPPROCESS = 0x2


class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]


def snapshot():
    procs = {}
    s = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(s, ctypes.byref(pe)):
        while True:
            procs[pe.th32ProcessID] = (pe.th32ParentProcessID,
                                       pe.szExeFile.decode("ascii", "replace"),
                                       pe.cntThreads)
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    return procs


def ptree(root, procs):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        for q, (pp, _, _) in procs.items():
            if pp == c:
                stack.append(q)
    return seen


def listening_ports():
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    out = []
    for l in net.splitlines():
        if "LISTENING" in l and any(x in l for x in ("48911", "48912", "48915", "48916", "48917")):
            parts = l.split()
            out.append("%s %s pid=%s" % (parts[1], parts[0], parts[-1]))
    return out


# ---------------- window helpers ----------------
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
_wins = []


def _enum(hwnd, lparam):
    if u32.IsWindowVisible(hwnd):
        ln = u32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(ln + 1)
        u32.GetWindowTextW(hwnd, buf, ln + 1)
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        ex = u32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        _wins.append({
            "hwnd": hwnd, "title": buf.value, "class": cls.value,
            "rect": [r.left, r.top, r.right - r.left, r.bottom - r.top],
            "topmost": bool(ex & 0x8), "layered": bool(ex & 0x80000),
            "transparent": bool(ex & 0x20), "toolwindow": bool(ex & 0x80),
            "pid": pid.value,
        })
    return True


def windows():
    _wins.clear()
    u32.EnumWindows(EnumWindowsProc(_enum), 0)
    return list(_wins)


def http(path, timeout=5, method="GET", data=None):
    url = "http://127.0.0.1:48911" + path
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(1200).decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000


# ---------------- main ----------------
def main():
    with open(MON, "w", encoding="utf-8") as f:
        f.write("")
    env = dict(os.environ)
    env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
    env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
    env["NEKO_STORAGE_CLOUDSAVE_ROOT"] = STORE
    env["PYTHONIOENCODING"] = "utf-8"

    lf = open(SPAWN, "wb")
    p = subprocess.Popen([EXE], cwd=BASE, env=env, stdout=lf, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL,
                         creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    with open(os.path.join(RAW, "neko-shell.pid"), "w") as f:
        f.write(str(p.pid))
    log("LAUNCHED shell pid=%d  exe=%s" % (p.pid, EXE))

    t0 = time.time()
    next_poll = 0
    reported_wins = set()
    while time.time() - t0 < BUDGET:
        elapsed = int(time.time() - t0)
        if elapsed >= next_poll:
            next_poll = elapsed + 10
            procs = snapshot()
            kids = ptree(p.pid, procs) if p.pid in procs else set()
            alive = p.pid in procs
            names = {}
            for q in kids:
                names[procs[q][1]] = names.get(procs[q][1], 0) + 1
            ports = listening_ports()
            st, body, ms = http("/health")
            log("t=%3ds shell_alive=%s procs=%d %s | ports=%d | /health=%s (%.0fms)"
                % (elapsed, alive, len(kids), names, len(ports), st, ms))
            for l in ports:
                log("      port %s" % l)
            wins = windows()
            own = [w for w in wins if w["pid"] in kids]
            for w in own:
                key = (w["title"], w["class"], tuple(w["rect"]))
                if key not in reported_wins:
                    reported_wins.add(key)
                    log("      WIN hwnd=%d pid=%d topmost=%s layered=%s transparent=%s "
                        "rect=%s class=%s title=%r"
                        % (w["hwnd"], w["pid"], w["topmost"], w["layered"], w["transparent"],
                           w["rect"], w["class"], w["title"][:80]))
            if st == 200:
                st2, b2, _ = http("/api/system/status")
                log("      /api/system/status=%s %s" % (st2, b2.replace("\n", " ")[:260]))
        time.sleep(2)

    log("SUPERVISOR budget %ds exhausted; shell pid %d left running" % (BUDGET, p.pid))


if __name__ == "__main__":
    main()
