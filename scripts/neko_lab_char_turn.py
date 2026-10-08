"""Drive one full character chat turn and prove where the keystrokes landed.

The failure mode this exists to avoid: WorkBuddy re-grabs the foreground between
our raise and the keystroke, so `key enter` fires into the wrong app and nothing
reaches N.E.K.O. Everything therefore happens inside ONE process, and the
foreground ownership is re-checked immediately before Enter. If the character
window is not the foreground at that instant we abort instead of typing blind.

Usage: neko_lab_char_turn.py <text> [--shot-name NAME] [--no-enter]
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

PY = r'C:\Users\Shmily\.workbuddy\binaries\python\envs\default\Scripts\python.exe'
GUI = r'C:\Users\Shmily\.workbuddy\skills\windows-desktop-control\scripts\gui.py'
EVIDENCE = r'D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence'

VK_MENU = 0x12
SW_RESTORE = 9
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0040


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def find_char_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.IsIconic(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = k32.OpenProcess(0x1000, False, pid.value)
            path = ''
            if handle:
                try:
                    size = wintypes.DWORD(1024)
                    pbuf = ctypes.create_unicode_buffer(1024)
                    if k32.QueryFullProcessImageNameW(handle, 0, pbuf,
                                                      ctypes.byref(size)):
                        path = pbuf.value
                finally:
                    k32.CloseHandle(handle)
            if 'N.E.K.O.exe' in path and ('Terminal' in title or 'Carbon' in title):
                rect = wintypes.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append({'hwnd': hwnd, 'title': title,
                              'rect': [rect.left, rect.top, rect.right, rect.bottom]})
        return True

    u32.EnumWindows(cb, 0)
    return found[0] if found else None


def raise_window(hwnd):
    u32.keybd_event(VK_MENU, 0, 0, 0)
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    u32.SetForegroundWindow(hwnd)
    u32.SetActiveWindow(hwnd)
    u32.keybd_event(VK_MENU, 0, 2, 0)
    time.sleep(0.6)


def owner_at(x, y):
    hwnd = u32.WindowFromPoint(wintypes.POINT(x, y))
    root = u32.GetAncestor(hwnd, 2)
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(root, buf, 256)
    return root, buf.value


def gui(*args):
    return subprocess.run([PY, GUI, *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('text')
    parser.add_argument('--shot-name', default='stage1-turn')
    parser.add_argument('--no-enter', action='store_true')
    options = parser.parse_args()

    report = {'text': options.text}
    target = find_char_window()
    if not target:
        print(json.dumps({'error': 'character window not found'}, ensure_ascii=False))
        return
    report['window'] = target
    hwnd = target['hwnd']
    left, top = target['rect'][0], target['rect'][1]
    x, y = left + 940, top + 540
    report['click_point'] = [x, y]

    raise_window(hwnd)
    fg = u32.GetForegroundWindow()
    report['foreground_after_raise'] = {'hwnd': fg, 'title': title_of(fg),
                                        'ok': fg == hwnd}

    gui('click', str(x), str(y))
    time.sleep(0.5)
    # Re-raise between the click and the paste: the click can hand focus back.
    raise_window(hwnd)
    gui('paste', options.text)
    time.sleep(0.8)
    filled = rf'{EVIDENCE}\{options.shot_name}-filled.png'
    gui('crop', '2100', '490', '2800', '600', filled)
    report['filled_shot'] = filled

    if options.no_enter:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    raise_window(hwnd)
    fg_before = u32.GetForegroundWindow()
    fg_title = title_of(fg_before)
    report['foreground_before_enter'] = {'hwnd': fg_before, 'title': fg_title,
                                         'ok': fg_before == hwnd}
    if fg_before != hwnd:
        report['aborted'] = ('character window is not the foreground; '
                             'refusing to send Enter into another app')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    gui('key', 'enter')
    time.sleep(9.0)
    after = rf'{EVIDENCE}\{options.shot_name}-after.png'
    gui('crop', str(left), '0', '2880', '700', after)
    report['after_shot'] = after
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
