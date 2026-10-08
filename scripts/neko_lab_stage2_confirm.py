"""Stage 2.1 confirmation: replay the Study plugin's exact interactive-screenshot request
(loopback, JSON, NO Origin header) against the freshly relaunched backend.

Before the restart this returned 409 capture_busy. Two competing explanations existed:
  (1) a leaked _interactive_capture_active module-global in the backend, or
  (2) a legitimately still-open capture session (a live full-screen overlay).
A restart already ruled out (1) indirectly -- but the fresh process still 409'd, and a
live "N.E.K.O Screenshot" overlay was then observed and dismissed, which made (2) the
conclusion. This script is the final confirmation: with no overlay open, the same
request must NOT be 409.

It opens the overlay deliberately, records it, then cancels it so the user's screen is
never left blocked.
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

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32


def find_overlay():
    """Find a visible window whose title contains 'Screenshot'."""
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


def cancel_overlay(hwnd, rect):
    """Click the Cancel control in the overlay's top bar, then close the window."""
    left, top, w, h = rect
    # Cancel sits at the right end of the top bar; the overlay bar was sampled before.
    x, y = left + w - 220, top + 82
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.2)
    u32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    u32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    time.sleep(0.8)
    u32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    time.sleep(0.6)
    return u32.IsWindow(hwnd)


def main():
    body = json.dumps({"selection_only": True, "copy_to_clipboard": False,
                       "session_timeout_ms": 45000}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    result = {"url": URL, "origin_header": None}
    try:
        r = urllib.request.urlopen(req, timeout=20)
        result["http_status"] = r.status
        result["body"] = r.read()[:600].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["body"] = e.read()[:600].decode("utf-8", "replace")
    except Exception as e:
        result["http_status"] = None
        result["error"] = repr(e)

    print("interactive probe ->", result.get("http_status"), flush=True)
    print("  body:", result.get("body") or result.get("error"), flush=True)

    time.sleep(2.5)
    ov = find_overlay()
    result["overlay_after_probe"] = ov
    print("overlay windows:", ov, flush=True)

    if ov:
        o = ov[0]
        still = cancel_overlay(o["hwnd"], o["rect"])
        result["overlay_still_open_after_cancel"] = bool(still)
        print("after cancel, still open:", still, flush=True)

    out = os.path.join(EVIDENCE, "goal-stage2-confirm.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", out, flush=True)

    verdict = "CONFIRMED-not-409" if result.get("http_status") != 409 else "STILL-409"
    print("VERDICT:", verdict, flush=True)
    return 0 if verdict == "CONFIRMED-not-409" else 1


if __name__ == "__main__":
    sys.exit(main())
