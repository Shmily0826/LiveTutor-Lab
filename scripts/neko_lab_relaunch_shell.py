"""Launch N.E.K.O through the shell (ShellExecuteW) so the child is created by the
user-session explorer.exe with ITS environment, not the sandbox's poisoned one.

Why: the sandbox exports ELECTRON_RUN_AS_NODE=1 / NODE_OPTIONS=..., which turns
N.E.K.O.exe into a bare Node process (rc=0, no window). ShellExecuteW hands the
request to the running explorer.exe, so the new process inherits explorer's clean
environment and correct window station.

Also clears stale launcher records first (they point at dead pids and make the
desktop's "Step A" runtime-record probe mis-resolve).
"""
import ctypes
import os
import shutil
import socket
import sys
import time
from ctypes import wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
RUNTIME = r"C:\Users\Shmily\AppData\Local\N.E.K.O.runtime"
EVIDENCE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32


def clear_stale_runtime():
    removed = []
    for name in ("launcher.json", "launcher.lock"):
        p = os.path.join(RUNTIME, name)
        if os.path.exists(p):
            bak = os.path.join(EVIDENCE, "stale-%s" % name)
            shutil.copy2(p, bak)
            os.remove(p)
            removed.append(name)
    return removed


def neko_pids():
    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_int32), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]

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


def windows():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, buf, 256)
        if not buf.value:
            return True
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((hwnd, pid.value, buf.value))
        return True

    u32.EnumWindows(cb, 0)
    return out


def main():
    print("cleared stale runtime records:", clear_stale_runtime())
    print("before pids=%r ports=%r" % (neko_pids(), [p for p, v in ports().items() if v]))

    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "open", APP, None, os.path.dirname(APP), 1)  # SW_SHOWNORMAL
    print("ShellExecuteW rc =", rc, "(>32 means ok)")
    if rc <= 32:
        return 2

    deadline = time.time() + WAIT
    ok = False
    seen = set()
    while time.time() < deadline:
        time.sleep(3.0)
        pids = neko_pids()
        st = ports()
        up = [p for p, v in st.items() if v]
        print("  t=%3ds ports=%r pids=%r" % (int(deadline - time.time()), up, pids))
        for pid, _, name in pids:
            seen.add(pid)
        if len(up) == 4:
            ok = True
            print("  ALL PORTS UP")
            break

    print("neko windows:")
    for hwnd, pid, title in windows():
        if "neko" in title.lower() or "n.e.k.o" in title.lower():
            print("   hwnd=%d pid=%d %r" % (hwnd, pid, title))
    print("RESULT ok=%r" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
