"""Launch N.E.K.O with a clean env and TRACE every child process that appears/disappears.

Goal: find which process actually dies with 0xC0000135 (STATUS_DLL_NOT_FOUND).
Polls at 0.3s and reads each N.E.K.O-related pid's live exit code, so a child that
appears and dies within a second is still captured.
"""
import ctypes
import os
import socket
import subprocess
import sys
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
EVIDENCE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0

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
    out = {}
    if k32.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            n = pe.szExeFile
            if "neko" in n.lower().replace(".", "") or "openfang" in n.lower():
                out[pe.th32ProcessID] = (n, pe.th32ParentProcessID)
            if not k32.Process32NextW(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    return out


def exit_code(pid):
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    code = wintypes.DWORD()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return code.value if ok else None


def ports():
    out = []
    for p in (48911, 48912, 48915, 48916):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", p))
            out.append(p)
        except Exception:
            pass
        s.close()
    return out


def clean_env():
    env = os.environ.copy()
    env.pop("ELECTRON_RUN_AS_NODE", None)
    env.pop("NODE_OPTIONS", None)
    env["USERPROFILE"] = r"C:\Users\Shmily"
    env["APPDATA"] = r"C:\Users\Shmily\AppData\Roaming"
    env["LOCALAPPDATA"] = r"C:\Users\Shmily\AppData\Local"
    return env


def main():
    out = open(os.path.join(EVIDENCE, "desktop-trace-stdout.log"), "wb")
    proc = subprocess.Popen([APP], cwd=os.path.dirname(APP), env=clean_env(),
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                            stdout=out, stderr=subprocess.STDOUT)
    print("desktop pid", proc.pid)
    known = {}
    t0 = time.time()
    while time.time() - t0 < WAIT:
        cur = snapshot()
        for pid, (name, ppid) in cur.items():
            if pid not in known:
                known[pid] = (name, ppid)
                print("[%6.2f] + pid=%d ppid=%d %s" % (time.time() - t0, pid, ppid, name))
        for pid in list(known):
            if pid not in cur:
                print("[%6.2f] - pid=%d died rc=%r %s"
                      % (time.time() - t0, pid, exit_code(pid), known[pid][0]))
                del known[pid]
        drc = proc.poll()
        if drc is not None:
            print("[%6.2f] DESKTOP exited rc=%r (0x%08X)" % (time.time() - t0, drc, drc & 0xFFFFFFFF))
            break
        up = ports()
        if len(up) == 4:
            print("[%6.2f] ALL PORTS UP %r" % (time.time() - t0, up))
            break
        time.sleep(0.3)
    else:
        print("timeout; ports=%r rc=%r" % (ports(), proc.poll()))
    out.flush()
    out.close()
    print("final ports=%r desktop_rc=%r" % (ports(), proc.poll()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
