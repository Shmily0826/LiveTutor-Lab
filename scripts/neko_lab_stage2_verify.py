"""End-to-end verification of the capture_busy fullscreen-fallback patch.

Submits study_ocr_snapshot(capture_mode='interactive') through the user-plugin server
and reports which branch actually ran:

  a) fallback   -> capture_mode_used='fullscreen', interactive_fallback_reason='capture_busy'
                   (expected while the backend's interactive flag is held)
  b) canceled   -> the interactive overlay really opened; a watcher thread cancels it so
                   the user's screen is never left blocked
  c) hard error -> the patch is not live in the running plugin (still pre-patch code)

A watcher thread polls for 'N.E.K.O Screenshot' overlays every second and cancels them.
"""
import ctypes
import json
import os
import sys
import threading
import time
import urllib.request
from ctypes import wintypes

PBASE = "http://127.0.0.1:48916"
EVIDENCE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
_stop = threading.Event()
_overlays_seen = []


def _overlays():
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
            out.append((hwnd, (r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    return out


def _watcher():
    while not _stop.is_set():
        for hwnd, rect in _overlays():
            _overlays_seen.append(time.time())
            left, top, w, _h = rect
            u32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            u32.SetCursorPos(int(left + w - 220), int(top + 82))
            time.sleep(0.1)
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.4)
            u32.PostMessageW(hwnd, 0x0010, 0, 0)
        time.sleep(1.0)


def request(path, method="GET", data=None, timeout=10):
    req = urllib.request.Request(
        PBASE + path, method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as r:
        return json.load(r)


def main():
    watcher = threading.Thread(target=_watcher, daemon=True)
    watcher.start()

    started = time.monotonic()
    run = request("/runs", "POST", {
        "plugin_id": "study_companion", "entry_id": "study_ocr_snapshot",
        "args": {"locale": "zh-CN", "capture_mode": "interactive"},
    })
    run_id = run.get("run_id") or run.get("id")
    print("run_id:", run_id, flush=True)
    if not run_id:
        print("submission rejected:", run, flush=True)
        _stop.set()
        return 2

    deadline = started + 150
    result = None
    while time.monotonic() < deadline:
        state = request("/runs/%s" % run_id)
        if state.get("status") in {"succeeded", "failed", "canceled", "timeout"}:
            print("status:", state.get("status"), flush=True)
            if state.get("status") == "succeeded":
                export = request("/runs/%s/export" % run_id)
                for item in export.get("items", []):
                    if item.get("type") == "json":
                        result = item.get("json")
                        break
            break
        time.sleep(1.0)
    _stop.set()
    time.sleep(0.5)

    data = (result or {}).get("data", result)
    inner = (data or {}).get("data", data) if isinstance(data, dict) else data
    summary = {
        "run_id": run_id,
        "elapsed_s": round(time.monotonic() - started, 1),
        "overlays_opened_and_canceled": len(_overlays_seen),
        "result": inner if not isinstance(inner, dict) else {
            k: inner.get(k) for k in (
                "status", "capture_mode_requested", "capture_mode_used",
                "interactive_fallback_reason", "error", "diagnostic") if k in inner
        },
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text, flush=True)
    with open(os.path.join(EVIDENCE, "goal-stage2-fallback-verify.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if isinstance(inner, dict) and inner.get("capture_mode_used") == "fullscreen" \
            and inner.get("interactive_fallback_reason") == "capture_busy":
        print("VERDICT: fallback branch live (patch effective)", flush=True)
        return 0
    if isinstance(inner, dict) and inner.get("status") == "canceled":
        print("VERDICT: interactive session opened and was canceled (flag not held)", flush=True)
        return 0
    print("VERDICT: inconclusive -- inspect summary above", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
