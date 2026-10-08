"""Enumerate the descendants of the character panel to find the chat child rect."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import sys

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32

TARGET = 7538316
rows = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, _):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    cls = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, cls, 256)
    rect = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rect))
    depth = 0
    parent = hwnd
    while depth < 8:
        parent = u32.GetParent(parent)
        if not parent:
            break
        depth += 1
    rows.append({'hwnd': int(hwnd), 'class': cls.value, 'title': buf.value,
                 'rect': [rect.left, rect.top, rect.right, rect.bottom],
                 'size': [rect.right - rect.left, rect.bottom - rect.top],
                 'depth': depth,
                 'visible': bool(u32.IsWindowVisible(hwnd)),
                 'child_of_target': int(u32.GetParent(hwnd)) == TARGET or depth > 0})


u32.EnumChildWindows(TARGET, cb, 0)
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(rows, ensure_ascii=False, indent=2))
