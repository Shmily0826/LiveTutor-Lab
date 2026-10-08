"""Report which top-level window actually owns a screen point.

`shot` captures pixels, so a window can look "on top" in a screenshot while
another window owns that pixel for input. WindowFromPoint + GA_ROOT tells the
truth, which is what matters before sending a click.
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
k32 = ctypes.windll.kernel32
GA_ROOT = 2


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def exe_of(hwnd):
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = k32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return '', pid.value
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(1024)
        if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value, pid.value
    finally:
        k32.CloseHandle(handle)
    return '', pid.value


def owner_of(x, y):
    hwnd = u32.WindowFromPoint(wintypes.POINT(x, y))
    root = u32.GetAncestor(hwnd, GA_ROOT)
    path, pid = exe_of(root)
    return {'point': [x, y], 'hwnd_under_point': hwnd, 'root': root,
            'title': title_of(root), 'pid': pid, 'path': path}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    points = []
    for token in sys.argv[1:]:
        x, y = token.split(',')
        points.append((int(x), int(y)))
    if not points:
        points = [(2350, 540), (2350, 498), (2000, 300)]
    print(json.dumps([owner_of(x, y) for x, y in points],
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
