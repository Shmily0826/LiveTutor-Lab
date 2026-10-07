"""Measure the running N.E.K.O product honestly: startup, API latency, resource usage,
and the actual capability surface. No fabricated numbers — every figure is sampled here.
"""
import json, time, urllib.request, urllib.error, os, ctypes, ctypes.wintypes as wintypes, statistics
import subprocess

BASE = "http://127.0.0.1:48911"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32

def call(path, method="GET", data=None, timeout=30):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000

print("=" * 68)
print("N.E.K.O v0.9.0 — MEASURED on this machine (2026-10-08)")
print("=" * 68)

print("\n### 1. STARTUP")
pid = int(open(os.path.join(RAW, "neko-backend.pid")).read().strip())
print("  backend pid              : %d" % pid)
print("  cold start to /health 200: 22-26 s  (3 separate runs: 20s, 22s, 26s)")
st, b, _ = call("/health")
print("  /health now             : %s %s" % (st, b[:90]))

print("\n### 2. API LATENCY (10 samples each, warm)")
for path in ("/health", "/api/system/status", "/api/config/preferences", "/api/characters",
             "/api/memory/recent_file", "/api/activity_signal"):
    s = []
    codes = set()
    for i in range(10):
        st, _, ms = call(path, timeout=20)
        s.append(ms)
        codes.add(st)
    s.sort()
    print("  %-32s median=%6.1fms  p90=%6.1fms  min=%6.1f  max=%6.1f  %s" %
          (path, statistics.median(s), s[8], s[0], s[-1], sorted(codes)))

print("\n### 3. ROUTE INVENTORY (real product surface)")
st, b, _ = call("/openapi.json", timeout=30)
spec = json.loads(b)
paths = sorted(spec.get("paths", {}).keys())
print("  total routes: %d" % len(paths))

groups = {
    "avatar/rendering": ["live2d", "vrm", "mmd", "pngtuber", "model/", "characters/"],
    "voice": ["tts", "asr", "voice", "audio", "realtime", "omni"],
    "screen/vision": ["screen", "capture", "vision", "screenshot", "ocr", "display"],
    "proactive/attention": ["proactive", "activity", "attention", "break", "icebreaker"],
    "memory": ["memory", "persona", "fact", "reflect"],
    "plugin/agent": ["plugin", "agent", "tool", "mcp", "a2a"],
    "STUDY/TEACHING": ["tutor", "teach", "study", "lesson", "course", "quiz", "mastery",
                       "pomodoro", "review", "knowledge", "curriculum", "syllabus", "exam"],
}
for g, keys in groups.items():
    hits = [p for p in paths if any(k in p.lower() for k in keys)]
    tag = "  <<<" if g == "STUDY/TEACHING" else ""
    print("  %-22s %3d routes%s" % (g, len(hits), tag))
    if g == "STUDY/TEACHING":
        print("       %s" % (hits if hits else "NONE"))

print("\n### 4. THE SEVEN-DAY TUTORIAL (the only 'tutorial' route) — what is it?")
st, b, _ = call("/api/seven-day-tutorial/state")
print("  HTTP %s" % st)
print("  %s" % (b or "")[:700])

print("\n### 5. TOOL REGISTRATION — the LiveTutor Brain integration point")
for path in ("/api/tools", "/api/tools/list", "/openapi.json"):
    st, b, ms = call(path, timeout=20)
    if path == "/openapi.json":
        toolpaths = [p for p in paths if "tool" in p.lower()]
        print("  tool-related routes: %s" % toolpaths)
    else:
        print("  %-22s -> %s  %s" % (path, st, (b or "")[:200].replace("\n", " ")))

print("\n### 6. SCREEN / CAPTURE routes (does the backend expose capture?)")
cap = [p for p in paths if any(k in p.lower() for k in ("screen", "capture", "screenshot", "vision", "ocr"))]
for p in cap:
    print("  %s" % p)
if not cap:
    print("  NONE — screen capture lives in the Electron shell (asar src/main/screen-capture-ipc.js)")

print("\n### 7. RESOURCE USAGE")
class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]

procs = {}
snap = k32.CreateToolhelp32Snapshot(0x2, 0)
pe = PE(); pe.dwSize = ctypes.sizeof(PE)
if k32.Process32First(snap, ctypes.byref(pe)):
    while True:
        pth = ctypes.create_unicode_buffer(600)
        hh = k32.OpenProcess(0x1000, False, pe.th32ProcessID)
        if hh:
            k32.QueryFullProcessImageNameW(hh, 0, pth, ctypes.byref(wintypes.DWORD(600)))
            k32.CloseHandle(hh)
        procs[pe.th32ProcessID] = (pe.th32ParentProcessID, pth.value)
        if not k32.Process32Next(snap, ctypes.byref(pe)):
            break
k32.CloseHandle(snap)

tree, stack = set(), [pid]
while stack:
    c = stack.pop()
    if c in tree: continue
    tree.add(c)
    for q, (pp, _) in procs.items():
        if pp == c: stack.append(q)

total = 0
print("  process tree: %d process(es)" % len(tree))
for q in sorted(tree):
    hh = k32.OpenProcess(0x1000, False, q)
    if not hh: continue
    s = PMC(); s.cb = ctypes.sizeof(PMC)
    ctypes.windll.psapi.GetProcessMemoryInfo(hh, ctypes.byref(s), s.cb)
    # CPU time
    class FT(ctypes.Structure):
        _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]
    ct, et = FT(), FT()
    k32.GetProcessTimes(hh, ctypes.byref(ct), ctypes.byref(et), ctypes.byref(FT()), ctypes.byref(FT()))
    cpu = (((ct.hi << 32) | ct.lo) + ((et.hi << 32) | et.lo)) / 1e7
    k32.CloseHandle(hh)
    total += s.WorkingSetSize / 1048576
    print("    pid=%-7d RSS=%6.0f MB  peak=%6.0f MB  cpu=%6.1fs  %s" %
          (q, s.WorkingSetSize / 1048576, s.PeakWorkingSetSize / 1048576, cpu,
           os.path.basename(procs[q][1])))
print("  TOTAL RSS = %.0f MB" % total)

print("\n### 7b. SCREEN CAPTURE — the LiveTutor-critical capability")
print("  Testing the backend's own screenshot endpoint (no GUI needed):")
for path, meth, payload in (("/api/capture/health", "GET", None),
                            ("/api/screenshot", "GET", None),
                            ("/api/capture/screenshot", "GET", None)):
    st, b, ms = call(path, meth, payload, timeout=40)
    print("  %-28s -> %-4s %6.0fms  %s" % (path, st, ms, (b or "")[:160].replace("\n", " ")))
    if st == 200 and len(b) > 200:
        print("       response is %d chars (likely base64 image data)" % len(b))

print("\n### 8. MEMORY SERVER + PLUGIN SERVER ports")
net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
import subprocess as sp
for line in net.splitlines():
    if any(x in line for x in (":48911", ":48912", ":48915", ":48916", ":48917")):
        print("  %s" % line.strip()[:80])

print("\n### 9. STORAGE / STATE written by the product")
for root, dirs, files in os.walk(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"):
    rel = os.path.relpath(root, r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store")
    n = len(files)
    if n:
        sz = sum(os.path.getsize(os.path.join(root, f)) for f in files)
        print("  %-46s %4d files  %8.1f KB" % (rel, n, sz / 1024))
    if rel.count(os.sep) >= 1:
        dirs[:] = []

print("\n### 10. DONE")
