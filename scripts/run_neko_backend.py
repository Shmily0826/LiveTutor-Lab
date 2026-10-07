"""Start the N.E.K.O Python backend directly from the shipped binary
(resources/bin/projectneko_server.exe, 531 MB Nuitka standalone) and verify the
HTTP API on 127.0.0.1:48911. This tests the backend half of the product, which does
not depend on the Electron/NSIS installer path.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, json, urllib.request, urllib.error

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
SERVER = os.path.join(BASE, "resources", "bin", "projectneko_server.exe")
LOG = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-backend.log"
UD = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-userdata2"

print("server:", SERVER)
print("exists:", os.path.exists(SERVER), "size: %.1f MB" % (os.path.getsize(SERVER) / 1048576))
print()

env = dict(os.environ)
env["NEKO_USER_DATA_DIR"] = UD
env.setdefault("PYTHONIOENCODING", "utf-8")

lf = open(LOG, "wb")
t0 = time.time()
p = subprocess.Popen([SERVER], cwd=os.path.join(BASE, "resources", "bin"),
                     env=env, stdout=lf, stderr=subprocess.STDOUT)
print("backend pid:", p.pid)

def probe(path="/", timeout=4):
    url = "http://127.0.0.1:48911" + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read(600).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(600).decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)

def ports():
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return [l.strip()[:70] for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]

up = None
SCHEDULE = [3, 6, 10, 15, 20, 30, 45, 60, 90, 120]
prev = 0
for t in SCHEDULE:
    time.sleep(t - prev)
    prev = t
    ps = ports()
    st, body = probe("/")
    print("t=%3ds alive=%-5s ports=%d  GET / -> %s  %s" % (t, p.poll() is None, len(ps), st, (body or "")[:90].replace("\n", " ")))
    if ps:
        up = t
        break
    if p.poll() is not None:
        print("   backend exited rc=%s at ~%.1fs" % (p.returncode, time.time() - t0))
        break

if up:
    print("\n=== BACKEND UP after ~%ds ===" % up)
    for path in ("/", "/docs", "/openapi.json", "/api/status", "/api/config", "/api/system/status", "/health"):
        st, body = probe(path, timeout=6)
        print("  %-22s -> %s  %s" % (path, st, (body or "")[:220].replace("\n", " ")))

    print("\n=== startup latency (cold, 5 samples on /api routes) ===")
    for i in range(5):
        t = time.time()
        st, _ = probe("/api/status", timeout=8)
        print("   sample %d: %.1f ms (HTTP %s)" % (i + 1, (time.time() - t) * 1000, st))
        time.sleep(0.5)

    print("\n=== resource usage ===")
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    h = k32 = ctypes.windll.kernel32.OpenProcess(0x1000, False, p.pid)
    if h:
        s = PMC(); s.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(s), s.cb)
        print("   RSS=%.0f MB  peakRSS=%.0f MB" % (s.WorkingSetSize / 1048576, s.PeakWorkingSetSize / 1048576))
        k32.CloseHandle(h)

print("\n=== backend log (last 60 lines) ===")
try:
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-60:])[:4000])
except Exception as e:
    print("  ", e)
print("\nlog size:", os.path.getsize(LOG) if os.path.exists(LOG) else 0)
print("pid still alive:", p.poll() is None, " pid =", p.pid)
