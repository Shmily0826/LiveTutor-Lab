"""Bring the N.E.K.O character window to the real foreground.

`gui.py focus` reports success but loses to other top-level windows on this box,
because the character is a TOPMOST transparent overlay whose "chat panel" is a
separate sibling window. This script uses the ALT-key trick plus
SetWindowPos(HWND_TOPMOST) and then verifies with GetForegroundWindow.

Usage: neko_lab_focus_char.py [--verify]
"""
import ctypes
import json
from ctypes import wintypes
import sys
import time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
HWND_TOP = 0
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def window_pid(hwnd):
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def exe_path(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ''
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(1024)
        if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
    finally:
        k32.CloseHandle(handle)
    return ''


def find_targets():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.IsIconic(hwnd):
            title = window_title(hwnd)
            pid = window_pid(hwnd)
            path = exe_path(pid)
            if 'N.E.K.O.exe' in path and ('Terminal' in title or 'Carbon' in title):
                rect = wintypes.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append({'hwnd': hwnd, 'title': title, 'path': path,
                              'rect': [rect.left, rect.top, rect.right, rect.bottom]})
        return True

    u32.EnumWindows(callback, 0)
    return found


def force_foreground(hwnd):
    # ALT down/up lifts the foreground lock so SetForegroundWindow is allowed.
    u32.keybd_event(VK_MENU, 0, 0, 0)
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    u32.SetForegroundWindow(hwnd)
    u32.SetActiveWindow(hwnd)
    u32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.8)
    fg = u32.GetForegroundWindow()
    return {'requested': hwnd, 'foreground': fg,
            'foreground_title': window_title(fg),
            'match': fg == hwnd or window_title(fg) == window_title(hwnd)}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    targets = find_targets()
    report = {'targets': targets}
    if not targets:
        report['error'] = 'character window not found'
    else:
        report['focus'] = force_foreground(targets[0]['hwnd'])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
