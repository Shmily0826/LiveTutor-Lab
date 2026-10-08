#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Read-only snapshot of a running N.E.K.O instance: process tree, listening ports,
visible top-level windows (desktop/avatar evidence), and backend HTTP surface.

Usage: neko_watch.py [--routes]
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

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

NO_PROXY = urllib.request.ProxyHandler({})
OPENER = urllib.request.build_opener(NO_PROXY)
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"

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
                                       pe.szExeFile.decode("ascii", "replace"))
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    return procs


def listening_ports():
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    out = []
    for l in net.splitlines():
        if "LISTENING" in l and any(x in l for x in ("48911", "48912", "48915", "48916", "48917", "48918")):
            p = l.split()
            out.append("%-24s %-6s pid=%s" % (p[1], p[0], p[-1]))
    return out


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
        ex = u32.GetWindowLongW(hwnd, -20)
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        _wins.append({"hwnd": hwnd, "title": buf.value, "class": cls.value,
                      "rect": [r.left, r.top, r.right - r.left, r.bottom - r.top],
                      "topmost": bool(ex & 0x8), "layered": bool(ex & 0x80000),
                      "transparent": bool(ex & 0x20), "pid": pid.value})
    return True


def windows():
    _wins.clear()
    u32.EnumWindows(EnumWindowsProc(_enum), 0)
    return list(_wins)


def http(path, timeout=6, method="GET", data=None):
    url = "http://127.0.0.1:48911" + path
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    t = time.time()
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read(2000).decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(600).decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000


def main():
    procs = snapshot()
    neko = [q for q, (_, n) in procs.items() if n.lower().startswith("n.e.k.o") or "projectneko" in n.lower()]
    print("=== N.E.K.O processes: %d ===" % len(neko))
    roots = [q for q in neko if procs[q][0] not in procs or procs[procs[q][0]][1].lower() not in
             ("n.e.k.o.exe", "projectneko_server.exe")]
    tree = set()
    stack = list(roots or neko)
    while stack:
        c = stack.pop()
        if c in tree:
            continue
        tree.add(c)
        for q, (pp, _) in procs.items():
            if pp == c:
                stack.append(q)
    for q in sorted(tree):
        print("   pid=%-7d ppid=%-7d %s" % (q, procs[q][0], procs[q][1]))

    print("\n=== listening ports ===")
    for l in listening_ports():
        print("   ", l)

    print("\n=== visible windows owned by N.E.K.O tree ===")
    for w in sorted(windows(), key=lambda x: x["hwnd"]):
        if w["pid"] in tree:
            print("   hwnd=%-9d topmost=%-5s layered=%-5s transparent=%-5s rect=%-22s class=%-28s title=%r"
                  % (w["hwnd"], w["topmost"], w["layered"], w["transparent"],
                     "%d,%d %dx%d" % tuple(w["rect"]), w["class"], w["title"][:70]))

    print("\n=== backend HTTP ===")
    for path in ("/health", "/api/system/status", "/api/status", "/api/plugins",
                 "/api/characters", "/api/capture/health", "/api/screen/sources"):
        st, body, ms = http(path)
        print("   %-24s %-5s %6.0fms  %s" % (path, st, ms, (body or "").replace("\n", " ")[:170]))

    if "--routes" in sys.argv:
        st, body, ms = http("/openapi.json", timeout=25)
        if st == 200:
            try:
                paths = sorted(json.loads(body).get("paths", {}).keys())
                print("\n=== routes: %d ===" % len(paths))
                with open(os.path.join(RAW, "neko-routes-live.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(paths))
                print("   written -> benchmarks/raw/neko-routes-live.txt")
            except Exception as e:
                print("   parse failed:", e, body[:200])
        else:
            print("\n   /openapi.json ->", st, (body or "")[:200])


if __name__ == "__main__":
    main()
