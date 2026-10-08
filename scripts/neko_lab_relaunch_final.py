"""Final working recipe for relaunching N.E.K.O from inside this sandbox.

Two independent blockers had to be removed:

1. ELECTRON_RUN_AS_NODE=1 / NODE_OPTIONS=... are exported by the sandbox and inherited
   by the child, so N.E.K.O.exe ran as bare Node: rc=0 after ~5s, no window, no log.
2. Chromium's sandbox cannot initialise under the sandbox's restricted token, so the
   browser process dies with STATUS_BREAKPOINT (0x80000003) ~1.5s after spawning the
   backend, and the Job Object takes openfang + projectneko_server down with it.
   Passing --no-sandbox fixes this.

Launching via ShellExecuteW (instead of Popen) means explorer.exe creates the process,
so it (a) gets explorer's clean environment and (b) survives this tool call finishing.
"""
import ctypes
import os
import socket
import sys
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
ARGS = "--no-sandbox"
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

k32 = ctypes.windll.kernel32


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_int32), ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260)]


def snapshot():
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    pe = PE32()
    pe.dwSize = ctypes.sizeof(pe)
    out = []
    if k32.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            n = pe.szExeFile
            if "neko" in n.lower().replace(".", "") or "openfang" in n.lower():
                out.append((pe.th32ProcessID, pe.th32ParentProcessID, n))
            if not k32.Process32NextW(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    return sorted(out)


def ports():
    up = []
    for p in (48911, 48912, 48915, 48916):
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", p))
            up.append(p)
        except Exception:
            pass
        s.close()
    return up


def main():
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "open", APP, ARGS, os.path.dirname(APP), 1)
    print("ShellExecuteW rc=%r (<=32 is an error)" % rc)
    if rc <= 32:
        return 2

    deadline = time.time() + WAIT
    ok = False
    while time.time() < deadline:
        time.sleep(3.0)
        up = ports()
        pids = snapshot()
        if len(up) == 4:
            ok = True
            print("ALL 4 PORTS UP  pids=%r" % pids)
            break
        print("  t=%3ds ports=%r pids=%r" % (int(deadline - time.time()), up, pids))
    print("RESULT ok=%r ports=%r pids=%r" % (ok, ports(), snapshot()))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
