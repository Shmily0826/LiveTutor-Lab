#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch the shell via ShellExecuteW and poll every 0.4s for N.E.K.O processes
(main, gpu, utility, renderer) and any window they create.
Goal: catch short-lived child processes that explain the silent hang.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
WATCH = float(os.environ.get("NEKO_WATCH", "45"))

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

os.environ["NEKO_STORAGE_SELECTED_ROOT"] = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
os.environ["NEKO_STORAGE_ANCHOR_ROOT"] = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
os.environ["NEKO_STORAGE_CLOUDSAVE_ROOT"] = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"

shell32 = ctypes.windll.shell32
shell32.ShellExecuteW.restype = wintypes.HINSTANCE
shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                  wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]

TH32CS_SNAPPROCESS = 0x2


class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]


def neko():
    out = {}
    s = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(s, ctypes.byref(pe)):
        while True:
            n = pe.szExeFile.decode("ascii", "replace")
            if n.lower().startswith("n.e.k.o"):
                out[pe.th32ProcessID] = (pe.th32ParentProcessID, pe.cntThreads)
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    return out


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
_w = []


def _enum(hwnd, lparam):
    n = u32.GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(hwnd, b, n + 1)
    c = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, c, 256)
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    _w.append((pid.value, hwnd, c.value, b.value, u32.IsWindowVisible(hwnd)))
    return True


def wins():
    _w.clear()
    u32.EnumWindows(EnumWindowsProc(_enum), 0)
    return list(_w)


print("launching via ShellExecuteW ...")
rc = shell32.ShellExecuteW(None, "open", EXE, None, BASE, 1)
print("ShellExecuteW rc =", rc)

known = {}
alive_log = {}
t0 = time.time()
while time.time() - t0 < WATCH:
    el = time.time() - t0
    cur = neko()
    for pid, (ppid, th) in cur.items():
        if pid not in known:
            known[pid] = (el, ppid, th)
            print("[%6.1fs] + PROCESS pid=%-7d ppid=%-7d threads=%d" % (el, pid, ppid, th))
        else:
            alive_log[pid] = th
    for pid in list(known):
        if pid not in cur:
            print("[%6.1fs] - EXIT    pid=%-7d (last threads=%s) lived %.1fs"
                  % (el, pid, alive_log.get(pid, known[pid][2]), el - known[pid][0]))
            del known[pid]
    for pid, hwnd, cls, title, vis in wins():
        if pid in cur:
            print("[%6.1fs]   WINDOW hwnd=%-9d pid=%-7d vis=%-5s class=%-24s title=%r"
                  % (el, hwnd, pid, vis, cls, title[:60]))
    time.sleep(0.4)

print("\nalive at end:", known)
