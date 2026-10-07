"""Correct CPU-time probe: raw FILETIME kernel+user, 100ns units, divided by 1e7."""
import ctypes, time
from ctypes import wintypes

k32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD)]


def cpu_seconds(pid):
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        c, e = FILETIME(), FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e),
                                  ctypes.byref(c), ctypes.byref(e)):
            return None
        raw = (c.dwHighDateTime << 32) | c.dwLowDateTime   # kernel
        raw += (e.dwHighDateTime << 32) | e.dwLowDateTime  # user
        return raw / 1e7
    finally:
        k32.CloseHandle(h)


def rss_mb(pid):
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None, None
    try:
        ps = psapi = ctypes.windll.psapi
        ps.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb)
        return c.WorkingSetSize / 1048576, c.PeakWorkingSetSize / 1048576
    finally:
        k32.CloseHandle(h)


PID = 40040
print(f"pid={PID}")
print(f"cpu_total_seconds = {cpu_seconds(PID)}")
r, p = rss_mb(PID)
print(f"rss_mb = {r}  peak_rss_mb = {p}")

# idle-CPU burn test: hammer an API for 15s and see how much CPU time accrues
import json, urllib.request
def call(path):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen("http://127.0.0.1:48911" + path, timeout=30) as r:
            r.read()
        st = r.status
    except urllib.error.HTTPError as e:
        st = e.code
        e.read()
    except Exception as e:
        st = repr(e)
    return (time.perf_counter() - t) * 1000, st

print("\n--- 15s load: /api/system/status in a loop ---")
c0 = cpu_seconds(PID)
t0 = time.perf_counter()
n = 0
while time.perf_counter() - t0 < 15:
    ms, st = call("/api/system/status")
    n += 1
    if n <= 5 or n % 50 == 0:
        print(f"  #{n:<5} {ms:7.1f}ms  [{st}]")
wall = time.perf_counter() - t0
c1 = cpu_seconds(PID)
print(f"requests        = {n} in {wall:.1f}s  ({n/wall:.1f} rps)")
print(f"cpu_delta       = {c1-c0:.2f}s")
print(f"cpu_per_request = {(c1-c0)/n*1000:.1f} ms")
print(f"cpu_utilisation = {(c1-c0)/wall*100:.1f}% of one core")

# now idle 20s to measure background CPU
print("\n--- 20s idle ---")
c2 = cpu_seconds(PID)
time.sleep(20)
c3 = cpu_seconds(PID)
print(f"idle cpu_delta  = {c3-c2:.2f}s over 20s  ({(c3-c2)/20*100:.2f}% of one core)")
r, p = rss_mb(PID)
print(f"rss_after={r}MB peak={p}MB")
