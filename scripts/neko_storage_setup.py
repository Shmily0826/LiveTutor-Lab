"""Complete N.E.K.O's first-run storage selection through its own documented API
(POST /api/storage/location/select), then verify the gate opens and inventory the
real API surface. This is the product's intended setup path, not a hack.
"""
import json, time, urllib.request, urllib.error, os

BASE = "http://127.0.0.1:48911"
STORE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-store"

def call(path, method="GET", data=None, timeout=25):
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

print("=== 1. bootstrap state ===")
for p in ("/api/storage/location/bootstrap", "/api/storage/location/status"):
    st, b, ms = call(p)
    print("  GET %-38s -> %s (%.0f ms)" % (p, st, ms))
    print("     ", (b or "")[:400].replace("\n", " "))

print("\n=== 2. select storage root: %s ===" % STORE)
st, b, ms = call("/api/storage/location/select", "POST",
                  {"selected_root": STORE, "selection_source": "user_selected"})
print("  POST select -> %s (%.0f ms)" % (st, ms))
print("  ", (b or "")[:800])

if st not in (200, 201):
    print("\n  select failed; trying preflight first")
    st, b, ms = call("/api/storage/location/preflight", "POST", {"selected_root": STORE})
    print("  POST preflight -> %s (%.0f ms)" % (st, ms))
    print("  ", (b or "")[:500])
    st, b, ms = call("/api/storage/location/select", "POST",
                     {"selected_root": STORE, "selection_source": "user_selected",
                      "confirm_existing_target_content": True})
    print("  POST select(confirm) -> %s (%.0f ms)" % (st, ms))
    print("  ", (b or "")[:800])

print("\n=== 3. gate state after selection ===")
time.sleep(3)
for p in ("/api/storage/location/status", "/api/system/status", "/api/status", "/openapi.json"):
    st, b, ms = call(p, timeout=20)
    print("  GET %-34s -> %s (%.0f ms)  %s" % (p, st, ms, (b or "")[:150].replace("\n", " ")))

print("\n=== 4. if still blocked, try the documented restart step ===")
st, b, ms = call("/api/storage/location/restart", "POST", {}, timeout=30)
print("  POST restart -> %s (%.0f ms)" % (st, ms))
print("  ", (b or "")[:400])
time.sleep(12)
st, b, ms = call("/api/status", timeout=15)
print("  after restart GET /api/status -> %s  %s" % (st, (b or "")[:200].replace("\n", " ")))
st, b, ms = call("/api/system/status", timeout=15)
print("  after restart GET /api/system/status -> %s  %s" % (st, (b or "")[:300].replace("\n", " ")))

print("\n=== 5. openapi inventory if open ===")
st, b, ms = call("/openapi.json", timeout=25)
if st == 200:
    try:
        spec = json.loads(b)
        paths = sorted(spec.get("paths", {}).keys())
        print("  TOTAL ROUTES:", len(paths))
        with open(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-routes.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(paths))
        buckets = {}
        for r in paths:
            seg = r.strip("/").split("/")
            key = "/" + "/".join(seg[:3]) if len(seg) >= 3 else r
            buckets[key] = buckets.get(key, 0) + 1
        for k in sorted(buckets, key=lambda x: -buckets[x])[:35]:
            print("    %-52s %d" % (k, buckets[k]))
        # tutor / study related routes
        print("\n  --- teaching/study/proactive/knowledge related routes ---")
        keys = ("tutor", "teach", "study", "learn", "lesson", "course", "quiz", "mastery",
                "pomodoro", "review", "knowledge", "progress", "exam", "curriculum")
        hits = [r for r in paths if any(k in r.lower() for k in keys)]
        print("   ", hits if hits else "NONE")
    except Exception as e:
        print("  parse error:", e)
else:
    print("  HTTP", st, (b or "")[:200])
