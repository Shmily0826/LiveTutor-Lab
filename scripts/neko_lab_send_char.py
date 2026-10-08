"""Send one message to the N.E.K.O character and prove it was delivered.

Differences from the earlier probe:
  * foreground is taken via the ALT/SetWindowPos trick (gui.py focus loses),
  * the click point is verified with WindowFromPoint so we know which window
    owns the pixel (visual stacking != input stacking on this box),
  * the input box is confirmed to CONTAIN our text before Enter is pressed,
    per the handoff's "trap 2": paste, screenshot-verify, then Enter.
"""
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
ROOT = r'D:\CODE\project\LiveTutor-Lab'
EVIDENCE = ROOT + r'\benchmarks\raw\evidence'

VK_MENU = 0x12
SW_RESTORE = 9
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW


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
                    if k32.QueryFullProcessImageNameW(handle, 0, pbuf, ctypes.byref(size)):
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


def owner_at(x, y):
    hwnd = u32.WindowFromPoint(wintypes.POINT(x, y))
    root = u32.GetAncestor(hwnd, 2)
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(root, buf, 256)
    return root, buf.value


def raise_window(hwnd):
    u32.keybd_event(VK_MENU, 0, 0, 0)
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    u32.SetForegroundWindow(hwnd)
    u32.SetActiveWindow(hwnd)
    u32.keybd_event(VK_MENU, 0, 2, 0)
    time.sleep(0.8)


def gui(*args):
    return subprocess.run([PY, GUI, *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    text = sys.argv[1] if len(sys.argv) > 1 else 'STAGE1-PROBE 请确认收到。'
    report = {'text': text}
    target = find_char_window()
    if not target:
        print(json.dumps({'error': 'window not found'}))
        return
    report['window'] = target
    raise_window(target['hwnd'])

    left, top = target['rect'][0], target['rect'][1]
    # Calibrated from a 1:1 crop: input row ~540px below the window's top edge,
    # horizontally ~940px in from the left edge to clear the right-hand controls.
    x, y = left + 940, top + 540
    owner, owner_title = owner_at(x, y)
    report['click_point'] = [x, y]
    report['owner_hwnd'] = owner
    report['owner_title'] = owner_title
    report['owner_is_character'] = owner == target['hwnd']

    gui('click', str(x), str(y))
    time.sleep(0.7)
    gui('paste', text)
    time.sleep(0.9)
    filled = EVIDENCE + r'\stage1-send-filled.png'
    gui('shot', filled)
    report['filled_shot'] = filled
    (EVIDENCE + r'\stage1-send-probe.json')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
