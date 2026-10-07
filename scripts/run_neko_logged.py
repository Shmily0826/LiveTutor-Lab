"""Relaunch N.E.K.O with a redirected userData dir so we can read its own debug log,
and with GPU disabled (common Electron-in-constrained-session blocker).
Records: startup wall time, whether a window appeared, log contents, exit behaviour.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, shutil, json

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
CWD = os.path.dirname(APP)
UD = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-userdata"

if os.path.isdir(UD):
    shutil.rmtree(UD, ignore_errors=True)
os.makedirs(UD, exist_ok=True)

def wins_for(pid):
    out = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            b = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(h, b, 512)
            c = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(h, c, 256)
            r = wintypes.RECT(); u32.GetWindowRect(h, ctypes.byref(r))
            out.append((h, c.value, b.value, (r.left, r.top, r.right - r.left, r.bottom - r.top), bool(u32.IsWindowVisible(h))))
        return True
    u32.EnumWindows(cb, 0)
    return out

def tree(root):
    TH32CS_SNAPPROCESS = 0x2
    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]
    procs = {}
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE(); pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(snap, ctypes.byref(pe)):
        while True:
            path = ctypes.create_unicode_buffer(600)
            h = k32.OpenProcess(0x1000, False, pe.th32ProcessID)
            if h:
                k32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(wintypes.DWORD(600)))
                k32.CloseHandle(h)
            procs[pe.th32ProcessID] = (pe.th32ParentProcessID, path.value)
            if not k32.Process32Next(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    out, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in out: continue
        out.add(c)
        for pid, (ppid, _) in procs.items():
            if ppid == c:
                stack.append(pid)
    return {p: procs[p] for p in out if p in procs}

env = dict(os.environ)
env["NEKO_USER_DATA_DIR"] = UD
env["ELECTRON_ENABLE_LOGGING"] = "1"
env["ELECTRON_ENABLE_STACK_DUMPING"] = "1"

LOG = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-run2.log"
lf = open(LOG, "wb")
t0 = time.time()
p = subprocess.Popen([APP], cwd=CWD, env=env, stdout=lf, stderr=subprocess.STDOUT)
print("root pid:", p.pid, " userData:", UD)
print("switches: NEKO_USER_DATA_DIR + ELECTRON_ENABLE_LOGGING")

appeared = None
for t in (5, 10, 20, 35, 50, 70, 90):
    time.sleep(t - (0 if t == 5 else (5 if t == 10 else (10 if t == 20 else (15 if t == 35 else (20 if t == 50 else (20 if t == 70 else 20)))))))
    tr = tree(p.pid)
    alive = p.poll() is None
    allw = []
    for q in tr:
        allw += wins_for(q)
    vis = [w for w in allw if w[4]]
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    ports = [l for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]
    print("t=%3ds alive=%-5s procs=%-3d wins=%-3d visible=%-3d ports=%d" %
          (t, alive, len(tr), len(allw), len(vis), len(ports)))
    for w in vis[:6]:
        print("    VIS hwnd=%-9d cls=%-26s %dx%d %s" % (w[0], w[1][:26], w[3][2], w[3][3], w[2][:40]))
    for l in ports[:4]:
        print("    PORT", l.strip()[:70])
    if vis:
        appeared = time.time() - t0
        print("    >>> WINDOW APPEARED at ~%.1fs" % appeared)
        break
    if not alive and not tr:
        print("    >>> ALL PROCESSES EXITED at ~%.1fs" % (time.time() - t0))
        break

print("\n=== userData contents ===")
for root, dirs, files in os.walk(UD):
    rel = os.path.relpath(root, UD)
    for f in files[:40]:
        fp = os.path.join(root, f)
        try:
            print("  %10d  %s" % (os.path.getsize(fp), os.path.join(rel, f)))
        except Exception:
            pass

print("\n=== neko-electron-debug.log (tail 120) ===")
lp = os.path.join(UD, "neko-electron-debug.log")
if os.path.exists(lp):
    with open(lp, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print("  total lines:", len(lines))
    for l in lines[-120:]:
        print("   ", l.rstrip()[:220])
else:
    print("  NOT FOUND at", lp)
    print("  userData top-level:", os.listdir(UD) if os.path.isdir(UD) else "missing")

print("\n=== stdout/stderr capture ===")
try:
    lf.flush()
except Exception:
    pass
print("  size:", os.path.getsize(LOG) if os.path.exists(LOG) else "n/a")
if os.path.exists(LOG):
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-60:])[:3000])
