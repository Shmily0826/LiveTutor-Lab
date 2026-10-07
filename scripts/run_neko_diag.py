"""Launch N.E.K.O, wait, then do a full diagnostic of what actually exists:
processes (by path), ALL windows (including invisible/zero-size), listening ports,
and any files it created. Read-only enumeration, kills only the exact PID we started.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, glob

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
CWD = os.path.dirname(APP)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
TH32CS_SNAPPROCESS = 0x2

class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]

def all_procs():
    out = {}
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
            out[pid] = (pe.th32ParentProcessID, pe.szExeFile.decode(errors="replace"), path.value)
            if not k32.Process32Next(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    return out

def all_windows(only_visible=False):
    out = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        vis = bool(u32.IsWindowVisible(hwnd))
        if only_visible and not vis:
            return True
        buf = ctypes.create_unicode_buffer(512)
        u32.GetWindowTextW(hwnd, buf, 512)
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        out.append(dict(hwnd=hwnd, title=buf.value, cls=cls.value, pid=pid.value,
                        vis=vis, iconic=bool(u32.IsIconic(hwnd)),
                        rect=(r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True
    u32.EnumWindows(cb, 0)
    return out

def neko_tree(root_pid):
    """All PIDs whose exe path or ancestry points at N.E.K.O."""
    procs = all_procs()
    kids = {}
    for pid, (ppid, exe, path) in procs.items():
        kids.setdefault(ppid, []).append(pid)
    hit, stack = set(), [root_pid]
    while stack:
        cur = stack.pop()
        if cur in hit:
            continue
        hit.add(cur)
        stack.extend(kids.get(cur, []))
    return {pid: procs[pid] for pid in hit if pid in procs}

baseline = set(all_procs().keys())
print("baseline pids:", len(baseline))

print("\n=== launching ===")
p = subprocess.Popen([APP], cwd=CWD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ROOT = p.pid
print("root pid:", ROOT)

for t in (10, 20, 35, 50, 70):
    time.sleep(t if t == 10 else (10 if t == 20 else (15 if t == 35 else (15 if t == 50 else 20))))
    tree = neko_tree(ROOT)
    new = {pid: v for pid, v in tree.items() if pid not in baseline}
    wins = [w for w in all_windows() if w["pid"] in new]
    visible = [w for w in wins if w["vis"]]
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    ports = [l for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]
    print("\n--- t~%ds : new procs=%d windows=%d visible=%d ports=%d" % (t, len(new), len(wins), len(visible), len(ports)))
    for pid, (ppid, exe, path) in sorted(new.items())[:12]:
        print("    pid=%-7d ppid=%-7d %-22s %s" % (pid, ppid, exe[:22], os.path.basename(path)))
    for w in visible[:10]:
        print("    VISWIN hwnd=%-10s pid=%-7d cls=%-28s %sx%s %s" % (w["hwnd"], w["pid"], w["cls"][:28], w["rect"][2], w["rect"][3], w["title"][:40]))
    for w in [x for x in wins if not x["vis"]][:6]:
        print("    hidwin hwnd=%-10s pid=%-7d cls=%-28s rect=%s %s" % (w["hwnd"], w["pid"], w["cls"][:28], w["rect"], w["title"][:30]))
    for l in ports[:6]:
        print("    PORT", l.strip()[:75])
    if visible or ports:
        print("    >>> SURFACE UP")
        break

print("\n=== files created under user profile (neko-ish, last 30 min) ===")
now = time.time()
for base in (os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA"), os.path.expanduser("~")):
    if not base or not os.path.isdir(base):
        continue
    for d in os.listdir(base):
        if "neko" not in d.lower():
            continue
        full = os.path.join(base, d)
        try:
            st = os.stat(full)
            age = (now - st.st_mtime) / 60
            n = len(os.listdir(full)) if os.path.isdir(full) else 0
            print("   %-70s age=%.1fmin entries=%d" % (full, age, n))
        except Exception as e:
            print("   ERR", full, e)

print("\nNOTE: leaving process running for manual inspection. root pid =", ROOT)
