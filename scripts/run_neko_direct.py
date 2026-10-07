"""Bypass the NSIS wrapper: run the Electron runtime directly against the extracted
asar, which is the real N.E.K.O application. Mirrors what the installed app does.
Records startup wall time, window appearance, ports, and log output.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, shutil

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32

APPDIR = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
EXE = os.path.join(APPDIR, "N.E.K.O.exe")
ASAR = os.path.join(APPDIR, "resources", "app.asar")
UD = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-userdata2"

print("electron runtime :", EXE)
print("app.asar         :", ASAR, os.path.getsize(ASAR), "bytes")
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
            b = ctypes.create_unicode_buffer(512); u32.GetWindowTextW(h, b, 512)
            c = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, c, 256)
            r = wintypes.RECT(); u32.GetWindowRect(h, ctypes.byref(r))
            out.append((h, c.value, b.value, (r.left, r.top, r.right - r.left, r.bottom - r.top),
                        bool(u32.IsWindowVisible(h))))
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
    s = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE(); pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(s, ctypes.byref(pe)):
        while True:
            path = ctypes.create_unicode_buffer(600)
            h = k32.OpenProcess(0x1000, False, pe.th32ProcessID)
            if h:
                k32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(wintypes.DWORD(600)))
                k32.CloseHandle(h)
            procs[pe.th32ProcessID] = (pe.th32ParentProcessID, path.value)
            if not k32.Process32Next(s, ctypes.byref(pe)):
                break
    k32.CloseHandle(s)
    out, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in out: continue
        out.add(c)
        for pid, (ppid, _) in procs.items():
            if ppid == c: stack.append(pid)
    return {p: procs[p] for p in out if p in procs}

env = dict(os.environ)
env["NEKO_USER_DATA_DIR"] = UD
env["ELECTRON_ENABLE_LOGGING"] = "1"
# Electron switches must precede the app path
cmd = [EXE,
       "--no-sandbox",
       "--enable-logging",
       "--log-file=" + os.path.join(UD, "electron-main.log"),
       ASAR]

LOG = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-direct.log"
lf = open(LOG, "wb")
t0 = time.time()
p = subprocess.Popen(cmd, cwd=APPDIR, env=env, stdout=lf, stderr=subprocess.STDOUT)
print("root pid:", p.pid)
print("cmd:", " ".join(cmd[:1] + cmd[1:])[:200], "... + asar")
print()

appeared = None
SCHEDULE = [3, 6, 10, 15, 20, 30, 45, 60, 80]
prev = 0
for t in SCHEDULE:
    time.sleep(t - prev)
    prev = t
    tr = tree(p.pid)
    allw = []
    for q in tr: allw += wins_for(q)
    vis = [w for w in allw if w[4]]
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    ports = [l for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]
    print("t=%3ds alive=%-5s procs=%-3d wins=%-3d vis=%-3d ports=%d" %
          (t, p.poll() is None, len(tr), len(allw), len(vis), len(ports)))
    for w in vis[:8]:
        print("    VIS hwnd=%-9d cls=%-24s %dx%d  %s" % (w[0], w[1][:24], w[3][2], w[3][3], w[2][:45]))
    for l in ports[:5]:
        print("    PORT", l.strip()[:72])
    if vis:
        appeared = time.time() - t0
        print("    >>> SURFACE UP at ~%.1fs" % appeared)
        break
    if p.poll() is not None and not tr:
        print("    >>> EXITED at ~%.1fs, code=%s" % (time.time() - t0, p.returncode))
        break

print("\n=== userData tree ===")
for root, dirs, files in os.walk(UD):
    rel = os.path.relpath(root, UD)
    for f in files[:60]:
        fp = os.path.join(root, f)
        try:
            print("  %10d  %s" % (os.path.getsize(fp), os.path.join(rel, f).replace("\\", "/")))
        except Exception:
            pass

for name in ("neko-electron-debug.log", "electron-main.log"):
    lp = os.path.join(UD, name)
    if os.path.exists(lp):
        print("\n=== %s (last 100 lines) ===" % name)
        with open(lp, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        print("  total lines:", len(lines))
        for l in lines[-100:]:
            print("   ", l.rstrip()[:230])

print("\n=== stdout/stderr ===")
print("  bytes:", os.path.getsize(LOG) if os.path.exists(LOG) else 0)
if os.path.exists(LOG):
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-80:])[:4000])
