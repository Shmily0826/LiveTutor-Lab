"""Complete N.E.K.O first-run setup the way the product intends:
  1. POST /api/storage/location/select   (persist the choice; returns restart_required)
  2. POST /api/storage/location/exit     (controlled shutdown, requires X-Neko-Storage-Action: exit)
  3. relaunch and verify the gate is open, then inventory the API.
Terminates only by the exact PID recorded in neko-backend.pid.
"""
import json, time, urllib.request, urllib.error, os, subprocess, ctypes, sys

BASE = "http://127.0.0.1:48911"
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"
RAW = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
BIN = os.path.join(RAW, "neko-app", "resources", "bin")
PIDFILE = os.path.join(RAW, "neko-backend.pid")
k32 = ctypes.windll.kernel32

def call(path, method="GET", data=None, headers=None, timeout=30):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.time() - t) * 1000
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), (time.time() - t) * 1000

def stop_exact(pid):
    if not pid:
        print("  no pid recorded")
        return
    h = k32.OpenProcess(0x0001 | 0x0400, False, pid)
    if h:
        k32.TerminateProcess(h, 0); k32.CloseHandle(h)
        print("  terminated exact pid", pid)
    else:
        print("  pid", pid, "already gone")
    time.sleep(4)

def relaunch(tag):
    log = open(os.path.join(RAW, "neko-backend-%s.log" % tag), "wb")
    env = dict(os.environ)
    env["NEKO_STORAGE_SELECTED_ROOT"] = STORE
    env["NEKO_STORAGE_ANCHOR_ROOT"] = STORE
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen([os.path.join(BIN, "projectneko_server.exe")], cwd=BIN, env=env,
                         stdout=log, stderr=subprocess.STDOUT, creationflags=0x00000008)  # DETACHED_PROCESS
    with open(PIDFILE, "w") as f:
        f.write(str(p.pid))
    print("  relaunched[%s] pid=%d" % (tag, p.pid))
    for t in (8, 15, 22, 30, 40, 55):
        while True:
            time.sleep(2.5 if t == 8 else 0)
            break
        st, b, _ = call("/health", timeout=4)
        if st == 200:
            print("  health OK after ~%ds" % t)
            return p.pid
    print("  health did not come up")
    return p.pid

# ---------- 0. clean slate ----------
try:
    old = int(open(PIDFILE).read().strip())
except Exception:
    old = None
print("=== 0. stop any running backend (exact pid) ===")
stop_exact(old)

print("\n=== 1. relaunch clean ===")
pid = relaunch("setup")

print("\n=== 2. select storage root ===")
st, b, ms = call("/api/storage/location/select", "POST",
                 {"selected_root": STORE, "selection_source": "user_selected"})
print("  -> %s (%.0f ms)  %s" % (st, ms, (b or "")[:300]))
if st == 200:
    try:
        j = json.loads(b)
        print("  result=%s restart_mode=%s permission_ok=%s warning=%s" %
              (j.get("result"), j.get("restart_mode"), j.get("permission_ok"), j.get("warning_codes")))
    except Exception:
        pass

print("\n=== 3. controlled shutdown via /exit ===")
st, b, ms = call("/api/storage/location/exit", "POST", {},
                 headers={"X-Neko-Storage-Action": "exit"}, timeout=30)
print("  -> %s (%.0f ms)  %s" % (st, ms, (b or "")[:300]))

# wait for it to actually go away
gone = False
for i in range(20):
    time.sleep(2)
    st, _, _ = call("/health", timeout=3)
    if st is None:
        gone = True
        print("  backend shut down after ~%ds" % ((i + 1) * 2))
        break
if not gone:
    print("  still up; terminating exact pid", pid)
    stop_exact(pid)

print("\n=== 4. relaunch after migration selection ===")
pid2 = relaunch("post")

print("\n=== 5. gate state ===")
time.sleep(4)
for p_ in ("/api/storage/location/status", "/api/system/status", "/api/status", "/openapi.json"):
    st, b, ms = call(p_, timeout=25)
    print("  %-34s -> %-4s %6.0fms  %s" % (p_, st, ms, (b or "")[:170].replace("\n", " ")))

print("\n=== 6. API inventory if gate open ===")
st, b, ms = call("/openapi.json", timeout=30)
if st == 200:
    try:
        spec = json.loads(b)
        paths = sorted(spec.get("paths", {}).keys())
        print("  TOTAL ROUTES: %d" % len(paths))
        with open(os.path.join(RAW, "neko-routes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(paths))
        buckets = {}
        for r in paths:
            seg = r.strip("/").split("/")
            buckets["/" + "/".join(seg[:3])] = buckets.get("/" + "/".join(seg[:3]), 0) + 1
        print("  --- top route groups ---")
        for k in sorted(buckets, key=lambda x: -buckets[x])[:40]:
            print("    %-54s %d" % (k, buckets[k]))
        keys = ("tutor", "teach", "study", "learn", "lesson", "course", "quiz", "mastery",
                "pomodoro", "review", "knowledge", "progress", "exam", "curriculum", "syllabus")
        hits = [r for r in paths if any(k in r.lower() for k in keys)]
        print("\n  --- teaching/study related routes ---")
        print("   ", hits if hits else "NONE FOUND")
    except Exception as e:
        print("  parse error:", e)
else:
    print("  HTTP", st, (b or "")[:250])

print("\nfinal backend pid:", pid2)
