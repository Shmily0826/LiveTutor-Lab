"""Locate the N.E.K.O character panel and capture a 1:1 crop of it.

Screenshots must be read from a crop whose width is <= max_width (default 900)
so the image is served at 1:1 instead of being downscaled by the viewer.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import time
from pathlib import Path

import mss
import mss.tools

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
BOOL = ctypes.c_bool
HWND = ctypes.wintypes.HWND
LPARAM = ctypes.wintypes.LPARAM
RECT = ctypes.wintypes.RECT


def list_windows():
    found = []

    @ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
    def cb(hwnd, _lparam):
        if not u32.IsWindowVisible(hwnd) or u32.IsIconic(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if not title:
            return True
        rect = RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(rect))
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        found.append({
            "hwnd": int(hwnd),
            "title": title,
            "class": cls.value,
            "rect": [rect.left, rect.top, rect.right, rect.bottom],
            "size": [rect.right - rect.left, rect.bottom - rect.top],
        })
        return True

    u32.EnumWindows(cb, 0)
    return found


def grab(path: Path, box):
    with mss.mss() as sct:
        shot = sct.grab(box)
        mss.tools.to_png(shot.rgb, shot.size, output=str(path))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", default="")
    parser.add_argument("--max-width", type=int, default=900)
    parser.add_argument("--tag", default="char")
    parser.add_argument("--full", action="store_true",
                        help="capture the whole panel downscaled for context")
    options = parser.parse_args()

    windows = list_windows()
    report = {"windows": windows, "foreground": int(u32.GetForegroundWindow())}

    target = None
    if options.match:
        needle = options.match.lower()
        candidates = [w for w in windows if needle in w["title"].lower()]
        # prefer the largest non-WorkBuddy candidate
        candidates = [w for w in candidates if "workbuddy" not in w["title"].lower()] or candidates
        if candidates:
            target = max(candidates, key=lambda w: w["size"][0] * w["size"][1])
    if target is None:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    report["target"] = target
    left, top, right, bottom = target["rect"]
    out_dir = Path("benchmarks/raw/evidence")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%H%M%S")

    if options.full:
        path = out_dir / f"{options.tag}-full-{stamp}.png"
        grab(path, {"left": left, "top": top,
                    "width": right - left, "height": bottom - top})
        report["full"] = str(path)

    # 1:1 slices: left half then right half of the panel
    width = right - left
    slices = []
    step = options.max_width
    offset = 0
    index = 0
    while offset < width and index < 4:
        h_left = left + offset
        h_width = min(step, width - offset)
        path = out_dir / f"{options.tag}-crop{index}-{stamp}.png"
        grab(path, {"left": h_left, "top": top,
                    "width": h_width, "height": bottom - top})
        slices.append({"path": str(path), "offset": offset, "width": h_width})
        offset += step
        index += 1
    report["slices"] = slices
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
