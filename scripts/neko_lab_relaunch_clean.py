"""Relaunch the N.E.K.O desktop with a CLEAN environment.

Root cause found 2026-10-08 23:36 NZDT: the WorkBuddy sandbox exports
  ELECTRON_RUN_AS_NODE=1
  NODE_OPTIONS=--require ".../node-language-shim.cjs"
A child N.E.K.O.exe inherits both, so Electron runs as bare Node instead of a GUI
app: it never opens a window, never writes neko-electron-debug.log, and exits rc=0
after ~5s. Every previous relaunch attempt inherited these and silently failed.

This script strips them (and points USERPROFILE at the real profile) before spawn.
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()


def clean_env():
    env = os.environ.copy()
    for bad in ("ELECTRON_RUN_AS_NODE", "NODE_OPTIONS"):
        env.pop(bad, None)
    env["USERPROFILE"] = r"C:\Users\Shmily"
    env["APPDATA"] = r"C:\Users\Shmily\AppData\Roaming"
    env["LOCALAPPDATA"] = r"C:\Users\Shmily\AppData\Local"
    env["HOME"] = r"C:\Users\Shmily"
    return env


def ports():
    import socket
    out = {}
    for p in (48911, 48912, 48915, 48916):
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", p))
            out[p] = True
        except Exception:
            out[p] = False
        s.close()
    return out


def neko_pids():
    k = ctypes.windll.kernel32

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_int32), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]

    snap = k.CreateToolhelp32Snapshot(0x2, 0)
    pe = PE32()
    pe.dwSize = ctypes.sizeof(pe)
    out = []
    if k.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            n = pe.szExeFile
            if "neko" in n.lower().replace(".", ""):
                out.append((pe.th32ProcessID, n))
            if not k.Process32NextW(snap, ctypes.byref(pe)):
                break
    k.CloseHandle(snap)
    return out


def main():
    print("before: pids=%r ports=%r" % (neko_pids(), ports()))
    env = clean_env()
    print("stripped ELECTRON_RUN_AS_NODE=%r NODE_OPTIONS=%r" % (
        "ELECTRON_RUN_AS_NODE" in env, "NODE_OPTIONS" in env))

    proc = subprocess.Popen(
        [APP],
        cwd=os.path.dirname(APP),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    print("spawned desktop pid", proc.pid)

    deadline = time.time() + WAIT
    ok = False
    while time.time() < deadline:
        time.sleep(2.0)
        st = ports()
        pids = neko_pids()
        rc = proc.poll()
        print("  t=%4ds rc=%r ports=%r pids=%r" % (
            int(deadline - time.time()), rc,
            [p for p, v in st.items() if v], [p for p, _ in pids]))
        if rc is not None:
            print("  !! desktop exited rc=%r" % rc)
            break
        if all(st.values()):
            ok = True
            print("  all four ports up")
            break

    print("RESULT ok=%r" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
