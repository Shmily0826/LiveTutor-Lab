# Launch N.E.K.O via ShellExecuteW (goes through Explorer/user session, not a child of this
# sandboxed process), then poll for its windows and backend port.
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

def windows():
    out = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        u32.GetWindowTextW(hwnd, buf, 512)
        if not buf.value:
            return True
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        path = ctypes.create_unicode_buffer(512)
        h = k32.OpenProcess(0x1000, False, pid.value)
        if h:
            k32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(wintypes.DWORD(512)))
            k32.CloseHandle(h)
        out.append(dict(hwnd=hwnd, title=buf.value, pid=pid.value,
                        rect=(r.left, r.top, r.right - r.left, r.bottom - r.top),
                        iconic=bool(u32.IsIconic(hwnd)), path=path.value))
        return True
    u32.EnumWindows(cb, 0)
    return out

def neko_procs():
    """Enumerate running processes by executable path — no name-based kill, read only."""
    found = []
    TH32CS_SNAPPROCESS = 0x2
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]
    pe = PE(); pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32First(snap, ctypes.byref(pe)):
        while True:
            exe = pe.szExeFile.decode(errors="replace")
            if "neko" in exe.lower():
                pid = pe.th32ProcessID
                path = ctypes.create_unicode_buffer(512)
                h = k32.OpenProcess(0x1000, False, pid)
                if h:
                    k32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(wintypes.DWORD(512)))
                    k32.CloseHandle(h)
                found.append((pid, pe.th32ParentProcessID, exe, path.value))
            if not k32.Process32Next(snap, ctypes.byref(pe)):
                break
    k32.CloseHandle(snap)
    return found

print("=== ShellExecuteW launch ===")
rc = shell32.ShellExecuteW(None, "open", APP, None, os.path.dirname(APP), 1)
print("ShellExecuteW returned:", rc, "(>32 = success)")

for t in range(1, 13):
    time.sleep(5)
    procs = neko_procs()
    wins = [w for w in windows() if "neko" in w["path"].lower()]
    ports = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    live_ports = [l for l in ports.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]
    print("t=%2ds procs=%d wins=%d ports=%d" % (t * 5, len(procs), len(wins), len(live_ports)))
    for p in procs[:8]:
        print("     pid=%-7d ppid=%-7d %s" % (p[0], p[1], os.path.basename(p[3])))
    for w in wins:
        print("     WIN hwnd=%-10s pid=%-7s iconic=%-5s %sx%s %s" % (w["hwnd"], w["pid"], w["iconic"], w["rect"][2], w["rect"][3], w["title"][:50]))
    for l in live_ports[:5]:
        print("     PORT", l.strip()[:70])
    if wins or live_ports:
        print("   >>> SURFACE APPEARED")
        break

print("\n=== final neko processes ===")
for p in neko_procs():
    print("  pid=%-7d ppid=%-7d %s" % (p[0], p[1], p[3]))
