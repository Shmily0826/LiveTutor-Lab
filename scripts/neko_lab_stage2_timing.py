"""Settle capture_busy with timing instead of inference.

The endpoint waits `session_timeout_ms/1000 + margin` before giving up, so:
  * a request that actually reaches the renderer blocks ~50s and then yields 504
    (renderer_timeout),
  * a request rejected up-front returns 409 capture_busy almost instantly.

So elapsed time alone distinguishes "the flag was already held" from "this request
acquired it". This script parks long enough for any retention window to expire, then
sends exactly one request and reports status + elapsed.
"""
import ctypes
import json
import os
import sys
import time
import urllib.request
from ctypes import wintypes

URL = "http://127.0.0.1:48911/api/screenshot/interactive"
EVIDENCE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"
PARK = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32


def overlays():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, buf, 256)
        if "screenshot" in buf.value.lower():
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append(dict(hwnd=hwnd, title=buf.value,
                            rect=(r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    return out


def close_all():
    for o in overlays():
        left, top, w, _h = o["rect"]
        u32.SetForegroundWindow(o["hwnd"])
        time.sleep(0.3)
        u32.SetCursorPos(int(left + w - 220), int(top + 82))
        time.sleep(0.15)
        u32.mouse_event(0x0002, 0, 0, 0, 0)
        u32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.6)
        u32.PostMessageW(o["hwnd"], 0x0010, 0, 0)
        time.sleep(0.8)


def probe(client_timeout):
    body = json.dumps({"selection_only": True, "copy_to_clipboard": False,
                       "session_timeout_ms": 45000}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=client_timeout)
        return r.status, r.read()[:300].decode("utf-8", "replace"), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "replace"), time.time() - t0
    except Exception as e:
        return None, repr(e), time.time() - t0


def main():
    close_all()
    print("parking %.0fs so any retention window expires..." % PARK, flush=True)
    time.sleep(PARK)

    before = overlays()
    print("overlays before probe: %d" % len(before), flush=True)

    status, body, elapsed = probe(client_timeout=70.0)
    print("PROBE status=%r elapsed=%.2fs body=%s" % (status, elapsed, body[:200]), flush=True)

    after = overlays()
    print("overlays after probe: %d" % len(after), flush=True)
    close_all()
    print("overlays after cleanup: %d" % len(overlays()), flush=True)

    report = dict(park_seconds=PARK, before=before, status=status,
                  elapsed=round(elapsed, 2), body=body, after=after)
    if status == 409 and elapsed < 5:
        report["verdict"] = "flag already held (mechanism 1): rejected up-front"
    elif status == 409:
        report["verdict"] = "409 but slow -- ambiguous"
    elif status == 504:
        report["verdict"] = "reached renderer, timed out (no user selection)"
    else:
        report["verdict"] = "unexpected status %r" % status
    print("VERDICT:", report["verdict"], flush=True)

    with open(os.path.join(EVIDENCE, "goal-stage2-timing.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
