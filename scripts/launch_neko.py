# Launch N.E.K.O detached and record exact PIDs, then report window state.
import subprocess, time, os, sys, ctypes, ctypes.wintypes as wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
LOG = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-stdout.log"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

def snapshot():
    out = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if not title:
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
        out.append((hwnd, title, pid.value,
                    (r.left, r.top, r.right - r.left, r.bottom - r.top),
                    bool(u32.IsIconic(hwnd)),
                    path.value))
        return True
    u32.EnumWindows(cb, 0)
    return out

print("=== BEFORE ===")
before = snapshot()
for w in before:
    print("  hwnd=%-10s pid=%-7s iconic=%-5s %sx%s  %s" % (w[0], w[2], w[4], w[3][2], w[3][3], w[1][:50]))

# Launch detached
lf = open(LOG, "ab")
p = subprocess.Popen([APP], stdout=lf, stderr=subprocess.STDOUT,
                     cwd=os.path.dirname(APP), close_fds=True)
print("\nLAUNCHED PID =", p.pid)
with open(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko.pid", "w") as f:
    f.write(str(p.pid))

for t in (5, 10, 20, 30):
    time.sleep(t if t == 5 else 5)
    snap = snapshot()
    new = [w for w in snap if "N.E.K.O" in w[5] or "neko" in w[5].lower()]
    print("\n--- t~%ds : %d visible titled windows, %d neko-owned ---" % (t, len(snap), len(new)))
    for w in new:
        print("   hwnd=%-10s pid=%-7s iconic=%-5s rect=%s  %s" % (w[0], w[2], w[4], w[3], w[1][:60]))
    if new:
        print("   >>> WINDOWS VISIBLE")
        break

print("\n=== ALIVE CHECK ===")
print("root pid alive:", p.poll() is None)
