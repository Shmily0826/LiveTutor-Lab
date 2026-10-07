"""Restart the N.E.K.O backend with NEKO_STORAGE_SELECTED_ROOT set so the
storage-selection gate opens without the GUI, then exercise the real API surface
and record honest latency/resource numbers.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, json, urllib.request, urllib.error, shutil

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

k32 = ctypes.windll.kernel32
BASE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app"
BIN = os.path.join(BASE, "resources", "bin")
SERVER = os.path.join(BIN, "projectneko_server.exe")
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
LOG = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-backend2.log"

os.makedirs(STORE, exist_ok=True)
print("storage root:", STORE)

# --- stop the previous backend by EXACT pid, not by name ---
prev = 38568
h = k32.OpenProcess(0x0001 | 0x0400, False, prev)   # TERMINATE | QUERY_INFORMATION
if h:
    k32.TerminateProcess(h, 0)
    k32.CloseHandle(h)
    print("terminated previous backend pid=%d (exact pid, not by name)" % prev)
time.sleep(3)

env = dict(os.environ)
env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
env["NEKO_STORAGE_CLOUDSAVE_ROOT"] = STORE
env["PYTHONIOENCODING"] = "utf-8"

lf = open(LOG, "wb")
t0 = time.time()
p = subprocess.Popen([SERVER], cwd=BIN, env=env, stdout=lf, stderr=subprocess.STDOUT)
print("backend pid:", p.pid)
print()

def get(path, timeout=8, method="GET", data=None):
    url = "http://127.0.0.1:48911" + path
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"} if data else {})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(3000).decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(3000).decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000

def ports():
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return [l.strip()[:70] for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]

up = None
SCHEDULE = [4, 8, 12, 16, 20, 25, 30, 40, 55, 70]
prev_t = 0
for t in SCHEDULE:
    time.sleep(t - prev_t); prev_t = t
    ps = ports()
    st, body, ms = get("/health", timeout=5)
    print("t=%3ds alive=%-5s ports=%d  /health -> %s (%.0f ms)" % (t, p.poll() is None, len(ps), st, ms))
    if ps and st == 200:
        up = t; break
    if p.poll() is not None:
        print("  exited rc=%s" % p.returncode); break

if not up:
    print("\nbackend did not come up; log tail:")
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-50:])[:3000])
    raise SystemExit(1)

print("\n=== BACKEND UP in ~%ds; storage gate should now be open ===" % up)

print("\n=== API surface probe ===")
for path in ("/health", "/api/system/status", "/api/status", "/openapi.json", "/docs",
             "/api/config", "/api/characters", "/api/plugins", "/api/memory/status",
             "/api/proactive/status", "/api/screen/sources", "/api/tools"):
    st, body, ms = get(path, timeout=8)
    snippet = (body or "").replace("\n", " ")[:150]
    print("  %-24s %-5s %6.0fms  %s" % (path, st, ms, snippet))

print("\n=== openapi route inventory (what the product actually exposes) ===")
st, body, ms = get("/openapi.json", timeout=20)
if st == 200:
    try:
        spec = json.loads(body)
        paths = sorted(spec.get("paths", {}).keys())
        print("  total routes:", len(paths))
        buckets = {}
        for r in paths:
            top = "/" + r.strip("/").split("/")[0] if r.strip("/") else "/"
            buckets[top] = buckets.get(top, 0) + 1
        for k in sorted(buckets, key=lambda x: -buckets[x])[:30]:
            print("    %-40s %d" % (k, buckets[k]))
        with open(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-routes.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(paths))
        print("  full route list -> benchmarks/raw/neko-routes.txt")
    except Exception as e:
        print("  parse failed:", e, body[:300])
else:
    print("  HTTP", st, (body or "")[:200])

print("\n=== cold request latency, 8 samples ===")
for path in ("/health", "/api/system/status"):
    samples = []
    for i in range(8):
        st, _, ms = get(path, timeout=10)
        samples.append(ms)
        time.sleep(0.3)
    s = sorted(samples)
    print("  %-22s median=%.0fms min=%.0f max=%.0f  %s" %
          (path, s[len(s)//2], s[0], s[-1], " ".join("%.0f" % x for x in samples)))

print("\n=== resource usage ===")
class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

def rss(pid):
    hh = k32.OpenProcess(0x1000, False, pid)
    if not hh:
        return None, None
    s = PMC(); s.cb = ctypes.sizeof(PMC)
    ctypes.windll.psapi.GetProcessMemoryInfo(hh, ctypes.byref(s), s.cb)
    k32.CloseHandle(hh)
    return s.WorkingSetSize / 1048576, s.PeakWorkingSetSize / 1048576

r, pk = rss(p.pid)
print("  backend RSS=%.0f MB peak=%.0f MB" % (r, pk))

# total for the whole process tree
TH32CS_SNAPPROCESS = 0x2
class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]
procs = {}
s2 = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
pe = PE(); pe.dwSize = ctypes.sizeof(PE)
if k32.Process32First(s2, ctypes.byref(pe)):
    while True:
        path = ctypes.create_unicode_buffer(600)
        hh = k32.OpenProcess(0x1000, False, pe.th32ProcessID)
        if hh:
            k32.QueryFullProcessImageNameW(hh, 0, path, ctypes.byref(wintypes.DWORD(600)))
            k32.CloseHandle(hh)
        procs[pe.th32ProcessID] = (pe.th32ParentProcessID, path.value)
        if not k32.Process32Next(s2, ctypes.byref(pe)):
            break
k32.CloseHandle(s2)
tree, stack = set(), [p.pid]
while stack:
    c = stack.pop()
    if c in tree: continue
    tree.add(c)
    for q, (pp, _) in procs.items():
        if pp == c: stack.append(q)
print("  process tree size:", len(tree))
tot = 0
for q in sorted(tree):
    rr, pp2 = rss(q)
    if rr:
        tot += rr
        print("    pid=%-7d rss=%.0f MB  %s" % (q, rr, os.path.basename(procs[q][1])))
print("  TOTAL RSS = %.0f MB" % tot)

print("\n=== storage gate now? ===")
st, body, ms = get("/api/system/status", timeout=8)
print("  /api/system/status ->", st)
print("  ", (body or "")[:600])

print("\nbackend pid", p.pid, "alive:", p.poll() is None)
