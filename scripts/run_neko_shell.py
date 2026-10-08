#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch the N.E.K.O Electron desktop shell (neko-app/N.E.K.O.exe) detached, so it
outlives this script, and report the resulting process tree / listening ports.

This is the step the previous evaluation never completed: it concluded the exe was
an NSIS installer. Binary inspection shows it is the Electron shell
(..\electron\shell\common\node_bindings.cc, appSearchPathsOnlyLoadASAR).
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import subprocess
import sys
import time

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(BASE, "N.E.K.O.exe")
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
LOG = os.path.join(RAW, "neko-shell-launch.log")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

extra_args = sys.argv[1:]
print("exe      :", EXE, os.path.exists(EXE))
print("store    :", STORE)
print("exe args :", extra_args)

env = dict(os.environ)
env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
env["NEKO_STORAGE_CLOUDSAVE_ROOT"] = STORE
env["PYTHONIOENCODING"] = "utf-8"

lf = open(LOG, "wb")
p = subprocess.Popen(
    [EXE] + extra_args,
    cwd=BASE,
    env=env,
    stdout=lf,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
)
print("shell pid:", p.pid)
with open(os.path.join(RAW, "neko-shell.pid"), "w") as f:
    f.write(str(p.pid))

k32 = ctypes.windll.kernel32
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
            procs[pe.th32ProcessID] = (pe.th32ParentProcessID, pe.szExeFile.decode("ascii", "replace"))
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    return procs


def ports():
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    out = []
    for l in net.splitlines():
        if "LISTENING" in l and any(x in l for x in ("48911", "48912", "48915", "48916")):
            out.append(" ".join(l.split()))
    return out


def tree(root):
    procs = snapshot()
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        for q, (pp, _) in procs.items():
            if pp == c:
                stack.append(q)
    return seen, procs


print("\npolling ...")
for t in [3, 6, 10, 15, 22, 30, 45, 60]:
    time.sleep(t - (0 if t == 3 else prev) if t != 3 else 3)
    prev = t
    alive = p.poll() is None
    ps = ports()
    kids, procs = tree(p.pid)
    names = sorted({procs[q][1] for q in kids})
    print("t=%3ds alive=%-5s rc=%-5s procs=%-3d ports=%d %s"
          % (t, alive, p.returncode, len(kids), len(ps), names[:6]))
    for l in ps:
        print("      ", l)
    if not alive:
        break

print("\nfinal shell pid", p.pid, "alive:", p.poll() is None, "rc:", p.returncode)
if p.poll() is not None:
    print("--- launch log ---")
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            print("".join(f.readlines()[-60:])[:4000])
    except Exception as e:
        print("log read failed", e)
