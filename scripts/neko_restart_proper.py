"""Final legitimate attempt: POST /api/storage/location/restart with the required
body (selected_root different from current), which schedules a controlled shutdown
AND commits the pending migration. Then relaunch and verify.
"""
import json, time, urllib.request, urllib.error, os, subprocess, ctypes

BASE = "http://127.0.0.1:48911"
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
BIN = os.path.join(RAW, "neko-app", "resources", "bin")
PIDFILE = os.path.join(RAW, "neko-backend.pid")
k32 = ctypes.windll.kernel32

def call(path, method="GET", data=None, headers=None, timeout=40):
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None, headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000

def stop_exact(pid, label=""):
    if not pid: return
    h = k32.OpenProcess(0x0001 | 0x0400, False, pid)
    if h:
        k32.TerminateProcess(h, 0); k32.CloseHandle(h); print("  terminated exact pid %d %s" % (pid, label))
    else:
        print("  pid %d already gone %s" % (pid, label))
    time.sleep(4)

def relaunch(tag):
    log = open(os.path.join(RAW, "neko-backend-%s.log" % tag), "wb")
    env = dict(os.environ)
    env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
    env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen([os.path.join(BIN, "projectneko_server.exe")], cwd=BIN, env=env,
                         stdout=log, stderr=subprocess.STDOUT, creationflags=0x00000008)
    open(PIDFILE, "w").write(str(p.pid))
    print("  relaunched[%s] pid=%d" % (tag, p.pid))
    for t in (10, 18, 26, 35, 50):
        st, _, _ = call("/health", timeout=4)
        if st == 200:
            print("  health OK (~%ds)" % t)
            return p.pid
        time.sleep(4)
    print("  health never came up")
    return p.pid

print("=== 0. clean restart of backend ===")
try: old = int(open(PIDFILE).read().strip())
except Exception: old = None
stop_exact(old)
pid = relaunch("r1")

print("\n=== 1. current storage state ===")
st, b, _ = call("/api/storage/location/status")
print("  status:", st, (b or "")[:280])

print("\n=== 2. POST /restart with selected_root (different from current) ===")
st, b, ms = call("/api/storage/location/restart", "POST",
                 {"selected_root": STORE, "selection_source": "user_selected"})
print("  -> %s (%.0f ms)" % (st, ms))
print("  ", (b or "")[:600])

print("\n=== 3. wait for controlled shutdown ===")
for i in range(25):
    time.sleep(2)
    st, _, _ = call("/health", timeout=3)
    if st is None:
        print("  shut down after ~%ds" % ((i + 1) * 2))
        break
else:
    print("  still up, terminating exact pid", pid)
    stop_exact(pid, "(forced)")

print("\n=== 4. relaunch after migration ===")
pid2 = relaunch("r2")
time.sleep(6)

print("\n=== 5. gate check ===")
for p_ in ("/api/storage/location/status", "/api/system/status", "/api/status", "/openapi.json", "/docs"):
    st, b, ms = call(p_, timeout=30)
    print("  %-34s -> %-4s %6.0fms  %s" % (p_, st, ms, (b or "")[:160].replace("\n", " ")))

st, b, ms = call("/openapi.json", timeout=30)
if st == 200:
    spec = json.loads(b)
    paths = sorted(spec.get("paths", {}).keys())
    print("\n=== API INVENTORY: %d routes ===" % len(paths))
    open(os.path.join(RAW, "neko-routes.txt"), "w", encoding="utf-8").write("\n".join(paths))
    buckets = {}
    for r in paths:
        seg = r.strip("/").split("/")
        k = "/" + "/".join(seg[:3])
        buckets[k] = buckets.get(k, 0) + 1
    for k in sorted(buckets, key=lambda x: -buckets[x])[:40]:
        print("    %-54s %d" % (k, buckets[k]))
    keys = ("tutor","teach","study","learn","lesson","course","quiz","mastery","pomodoro",
            "review","knowledge","progress","exam","curriculum","syllabus","memory","proactive")
    print("\n  --- study/teaching routes ---")
    print("   ", [r for r in paths if any(k in r.lower() for k in keys[:15])] or "NONE")
else:
    print("\nopenapi still blocked:", st)

print("\nfinal pid:", pid2)
