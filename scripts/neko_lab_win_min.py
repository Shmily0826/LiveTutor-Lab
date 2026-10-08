"""Minimize/restore a window by title substring, remembering its prior state.

Used to get occluding windows out of the way for a screenshot-based check, and
to put them back afterwards. Reports exactly what it did so the caller can undo.

Usage: neko_lab_win_min.py <title-substring> [--restore]
"""
import ctypes
from ctypes import wintypes
import json
import sys

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
SW_MINIMIZE = 6
SW_RESTORE = 9


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def find(substring):
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd):
            title = title_of(hwnd)
            if substring.lower() in title.lower():
                hits.append({'hwnd': hwnd, 'title': title,
                             'iconic': bool(u32.IsIconic(hwnd))})
        return True

    u32.EnumWindows(cb, 0)
    return hits


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    substring = sys.argv[1]
    restore = '--restore' in sys.argv
    hits = find(substring)
    actions = []
    for hit in hits:
        hwnd = hit['hwnd']
        u32.ShowWindow(hwnd, SW_RESTORE if restore else SW_MINIMIZE)
        actions.append({'hwnd': hwnd, 'title': hit['title'],
                        'action': 'restore' if restore else 'minimize'})
    print(json.dumps({'substring': substring, 'matched': len(hits),
                      'actions': actions}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
