#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch N.E.K.O.exe the way a user does: shell32.ShellExecuteW('open', exe).
This gives the process the shell's own context rather than a console child's.
Then watch for windows / backend for `watch` seconds.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import subprocess
import sys
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
WATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 60

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

shell32 = ctypes.windll.shell32
shell32.ShellExecuteW.restype = wintypes.HINSTANCE
shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                  wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]

for var, val in (("NEKO_STORAGE_SELECTED_ROOT", r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"),
                 ("NEKO_STORAGE_ANCHOR_ROOT", r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"),
                 ("NEKO_STORAGE_CLOUDSAVE_ROOT", r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store")):
    os.environ[var] = val

rc = shell32.ShellExecuteW(None, "open", EXE, None, BASE, 1)  # SW_SHOWNORMAL
print("ShellExecuteW rc =", rc, "(>32 means success)")
print("GetLastError =", ctypes.windll.kernel32.GetLastError())

TH32CS_SNAPPROCESS = 0x2


class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]


def neko_pids():
    out = []
    s = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(s, ctypes.byref(pe)):
        while True:
            n = pe.szExeFile.decode("ascii", "replace")
            if n.lower().startswith("n.e.k.o") or "projectneko" in n.lower():
                out.append((pe.th32ProcessID, pe.th32ParentProcessID, n, pe.cntThreads))
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    return out


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
_w = []


def _enum(hwnd, lparam):
    if u32.IsWindowVisible(hwnd):
        n = u32.GetWindowTextLengthW(hwnd)
        b = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(hwnd, b, n + 1)
        c = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, c, 256)
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        _w.append((pid.value, hwnd, c.value, b.value, [r.left, r.top, r.right - r.left, r.bottom - r.top]))
    return True


def wins():
    _w.clear()
    u32.EnumWindows(EnumWindowsProc(_enum), 0)
    return list(_w)


print("\nwatching %ds ..." % WATCH)
t0 = time.time()
seen_pids = set()
seen_hwnds = set()
while time.time() - t0 < WATCH:
    el = int(time.time() - t0)
    ps = neko_pids()
    for pid, ppid, name, th in ps:
        if pid not in seen_pids:
            seen_pids.add(pid)
            print("[%3ds] PROCESS pid=%d ppid=%d threads=%d %s" % (el, pid, ppid, th, name))
    own = {p[0] for p in ps}
    for pid, hwnd, cls, title, rect in wins():
        if pid in own and hwnd not in seen_hwnds:
            seen_hwnds.add(hwnd)
            print("[%3ds] WINDOW hwnd=%d pid=%d class=%s rect=%s title=%r"
                  % (el, hwnd, pid, cls, "%d,%d %dx%d" % tuple(rect), title[:70]))
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    listening = [l.split()[1] for l in net.splitlines()
                 if "LISTENING" in l and "48911" in l]
    if listening:
        print("[%3ds] PORT 48911 LISTENING" % el)
    time.sleep(3)

print("\nfinal N.E.K.O processes:", neko_pids())
print("windows owned by them:", [w for w in wins() if w[0] in {p[0] for p in neko_pids()}])
