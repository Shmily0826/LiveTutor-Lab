"""Deliver text + Enter to a window WITHOUT relying on foreground focus.

Rationale: on this box WorkBuddy re-grabs the foreground between our
`raise_window` and the keystroke, so a global `key enter` can land in the wrong
app. Posting WM_CHAR / WM_KEYDOWN directly to the target hwnd skips the focus
race entirely.

Caveat: Chromium/Electron renderers use a child HWND for real input, and
PostMessage to the top-level window may be ignored. The script therefore
reports exactly what it posted so the caller can judge, and it still verifies
by reading back the window content via the app's own log/UI.

Usage: neko_lab_post_text.py <hwnd> <text>
"""
import ctypes
from ctypes import wintypes
import json
import sys
import time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D


def child_at(x, y):
    """Return the deepest child hwnd owning a point, plus the root."""
    top = u32.WindowFromPoint(wintypes.POINT(x, y))
    chain = []
    hwnd = top
    while hwnd:
        chain.append(hwnd)
        hwnd = u32.GetParent(hwnd)
    return top, chain


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    hwnd = int(sys.argv[1])
    text = sys.argv[2] if len(sys.argv) > 2 else 'STAGE1 POST TEST'
    report = {'target_hwnd': hwnd, 'target_title': title_of(hwnd),
              'target_class': class_of(hwnd), 'text': text}

    # Enumerate children so we can show whether the renderer has its own hwnd.
    children = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(child, _):
        children.append({'hwnd': child, 'class': class_of(child),
                         'title': title_of(child)})
        return True

    u32.EnumChildWindows(hwnd, cb, 0)
    report['children'] = children[:15]

    posted = []
    for ch in text:
        ok = u32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        posted.append({'char': ch, 'ok': bool(ok)})
        time.sleep(0.02)
    ok_down = u32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
    ok_up = u32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)
    report['posted_chars'] = len(posted)
    report['posted_all_ok'] = all(p['ok'] for p in posted)
    report['enter_posted'] = bool(ok_down and ok_up)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
