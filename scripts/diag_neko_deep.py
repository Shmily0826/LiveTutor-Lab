"""Diagnose why N.E.K.O.exe sits with no window: inspect the live process's threads,
loaded modules, and any crash artifacts. Also test whether a *minimal* Electron app
can open a window in this environment at all — that separates "N.E.K.O is broken on
Windows" from "this sandbox cannot show GUI windows".
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, glob

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
psapi = ctypes.windll.psapi

# ---- find the running N.E.K.O pid (do NOT kill by name) ----
TH32CS_SNAPPROCESS = 0x2
class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]

def neko_pids():
    out = []
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE(); pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(snap, ctypes.byref(pe)):
        while True:
            pid = pe.th32ProcessID
            path = ctypes.create_unicode_buffer(600)
            h = k32.OpenProcess(0x1000, False, pid)
            if h:
                k32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(wintypes.DWORD(600)))
                k32.CloseHandle(h)
                if "neko" in path.value.lower():
                    out.append((pid, pe.th32ParentProcessID, pe.cntThreads, path.value))
                k32.CloseHandle(h)
            if not k32.Process32Next(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    return out

found = neko_pids()
print("=== running N.E.K.O processes ===")
for pid, ppid, nthreads, path in found:
    print("  pid=%-7d ppid=%-7d threads=%-4d %s" % (pid, ppid, nthreads, path))
if not found:
    print("  none — process exited")
else:
    pid = found[0][0]
    h = k32.OpenProcess(0x0400 | 0x0010 | 0x1000, False, pid)  # QUERY_INFO|VM_READ|VM_WRITE? use 0x0410
    if not h:
        h = k32.OpenProcess(0x0410, False, pid)
    print("\n=== open handle ok:", bool(h), "===")
    if h:
        # CPU time
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
        ct, et, kt = FILETIME(), FILETIME(), FILETIME()
        if k32.GetProcessTimes(h, ctypes.byref(ct), ctypes.byref(et), ctypes.byref(kt), ctypes.byref(kt)):
            def ft(v):
                return ((v.dwHighDateTime << 32) | v.dwLowDateTime) / 1e7
            print("  cpu_user=%.2fs kernel=%.2fs" % (ft(ct), ft(et)))
        # working set
        class PMEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = PMEMORYSTATUSEX(); st.dwLength = ctypes.sizeof(PMEMORYSTATUSEX)
        psapi.GetProcessMemoryInfo(h, ctypes.byref(st), st.dwLength)
        print("  workingSet=%.0f MB  systemPhysLoad=%d%%" % (st.ullTotalPageFile and 0 or 0, st.dwMemoryLoad))
        k32.CloseHandle(h)

    # thread states / wait reasons
    TH32CS_SNAPTHREAD = 0x4
    class TE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
                    ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long), ("dwFlags", wintypes.DWORD)]
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    te = TE(); te.dwSize = ctypes.sizeof(TE)
    n = 0
    if k32.Thread32First(snap, ctypes.byref(te)):
        while True:
            if te.th32OwnerProcessID == pid:
                n += 1
            if not k32.Thread32Next(snap, ctypes.byref(te)):
                break
    k32.CloseHandle(snap)
    print("  live threads:", n)

# ---- crash artifacts ----
print("\n=== crash / log artifacts in app dir and temp ===")
appdir = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
for pat in ("**/*.dmp", "**/*.log", "logs/**", "*.log"):
    for f in glob.glob(os.path.join(appdir, pat), recursive=True)[:20]:
        try:
            print("   %s  %d bytes  mtime=%s" % (f, os.path.getsize(f),
                  time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(f)))))
        except Exception:
            pass
tmp = os.environ.get("TEMP", "")
for f in glob.glob(os.path.join(tmp, "*neko*")) + glob.glob(os.path.join(tmp, "*.dmp"))[:10]:
    print("   TEMP:", f)

# ---- control: can ANY Electron/GUI window open here? ----
print("\n=== CONTROL TEST: minimal GUI window from python (tkinter) ===")
tk_script = r'''
import tkinter as tk
r = tk.Tk(); r.title("NEKO_LAB_CONTROL_PROBE"); r.geometry("300x120+50+50")
tk.Label(r, text="GUI OK").pack(pady=40)
r.after(2500, r.destroy); r.mainloop()
print("TK_OK")
'''
open(os.path.join(appdir, "_probe_tk.py"), "w").write(tk_script)
r = subprocess.run(["python", os.path.join(appdir, "_probe_tk.py")],
                   capture_output=True, text=True, timeout=40)
print("  tkinter rc=%s out=%r err=%r" % (r.returncode, r.stdout.strip()[:80], r.stderr.strip()[:200]))

print("\n=== CONTROL TEST: does enumerating a new top-level window work at all? ===")
print("  (if tkinter above printed TK_OK, GUI subsystem is functional in this session)")
