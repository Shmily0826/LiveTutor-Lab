"""Disambiguate the two capture_busy mechanisms with a clean before/after sequence.

  mechanism 1 -- a stuck _interactive_capture_active flag: busy is reported even with
                 NO overlay on screen, and never clears.
  mechanism 2 -- a legitimately open session: busy is reported because an overlay
                 really is up; once it closes, the next request succeeds.

Sequence per round: inventory overlays -> probe -> inventory overlays -> cancel all
-> wait -> repeat. If a probe in a round whose "before" inventory is empty still 409s,
that is mechanism 1. If it 200s in that situation, it was mechanism 2.
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
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3

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
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            out.append(dict(hwnd=hwnd, title=buf.value, pid=pid.value,
                            rect=(r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    return out


def close_overlay(hwnd, rect):
    left, top, w, _h = rect
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    x, y = left + w - 220, top + 82
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    u32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.6)
    u32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    time.sleep(0.8)
    return bool(u32.IsWindow(hwnd))


def probe():
    body = json.dumps({"selection_only": True, "copy_to_clipboard": False,
                       "session_timeout_ms": 45000}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, r.read()[:400].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf-8", "replace")
    except Exception as e:
        return None, repr(e)


def main():
    report = {"url": URL, "rounds": []}
    for i in range(1, ROUNDS + 1):
        before = overlays()
        status, body = probe()
        after = overlays()
        print("round %d: before=%d overlay(s) | status=%r | after=%d overlay(s)"
              % (i, len(before), status, len(after)), flush=True)
        print("        body=%s" % body[:160], flush=True)
        closed = []
        for o in after:
            closed.append(dict(o, still_open=close_overlay(o["hwnd"], o["rect"])))
        report["rounds"].append(dict(round=i, before=before, status=status,
                                    body=body, after=after, closed=closed))
        time.sleep(6.0)

    # final probe with everything closed
    time.sleep(4.0)
    final_before = overlays()
    status, body = probe()
    final_after = overlays()
    print("FINAL: before=%d status=%r after=%d body=%s"
          % (len(final_before), status, len(final_after), body[:160]), flush=True)
    for o in final_after:
        close_overlay(o["hwnd"], o["rect"])
    report["final"] = dict(before=final_before, status=status, body=body, after=final_after)

    out = os.path.join(EVIDENCE, "goal-stage2-sequence.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
