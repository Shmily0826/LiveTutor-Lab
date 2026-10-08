# -*- coding: utf-8 -*-
"""Check topmost/z-order state of WorkBuddy vs N.E.K.O chat windows."""
import ctypes
from ctypes import wintypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x8


def info(hwnd, label):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    ex = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    topmost = bool(ex & WS_EX_TOPMOST)
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    print("%s hwnd=%s title=%r topmost=%s rect=(%d,%d,%d,%d)"
          % (label, hwnd, buf.value, topmost, r.left, r.top, r.right, r.bottom))


def find(pred):
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if u32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(h, buf, 256)
            t = buf.value
            if pred(t):
                hits.append(h)
        return True

    u32.EnumWindows(cb, 0)
    return hits


for t, label in [(lambda s: "workbuddy" in s.lower(), "WORKBUDDY"),
                 (lambda s: s == "Project N.E.K.O.", "NEKO-CHAT"),
                 (lambda s: "N.E.K.O" in s and "Project" not in s, "NEKO-PET")]:
    for h in find(t):
        info(h, label)

fg = u32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
u32.GetWindowTextW(fg, buf, 256)
print("FOREGROUND now: hwnd=%s title=%r" % (fg, buf.value))
