#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Enumerate ALL top-level windows (visible or not) owned by given pids, plus
per-process CPU time, to tell 'stuck' from 'working'."""
import ctypes
import ctypes.wintypes as wintypes
import sys
import time

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
_wins = []


def _enum(hwnd, lparam):
    ln = u32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(ln + 1)
    u32.GetWindowTextW(hwnd, buf, ln + 1)
    cls = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, cls, 256)
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    ex = u32.GetWindowLongW(hwnd, -20)
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    _wins.append((pid.value, hwnd, u32.IsWindowVisible(hwnd), cls.value, buf.value,
                  [r.left, r.top, r.right - r.left, r.bottom - r.top], bool(ex & 0x8)))
    return True


def all_windows():
    _wins.clear()
    u32.EnumWindows(EnumWindowsProc(_enum), 0)
    return list(_wins)


def cpu(pid):
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    ft_create = wintypes.FILETIME()
    ft_exit = wintypes.FILETIME()
    ft_kernel = wintypes.FILETIME()
    ft_user = wintypes.FILETIME()
    k32.GetProcessTimes(h, ctypes.byref(ft_create), ctypes.byref(ft_exit),
                        ctypes.byref(ft_kernel), ctypes.byref(ft_user))
    k32.CloseHandle(h)

    def to_s(ft):
        return (((ft.dwHighDateTime << 32) | ft.dwLowDateTime) & 0xFFFFFFFFFFFFFFFF) / 1e7
    return {"kernel_s": round(to_s(ft_kernel), 2), "user_s": round(to_s(ft_user), 2)}


def main():
    pids = set(int(x) for x in sys.argv[1:]) if len(sys.argv) > 1 else None
    print("target pids:", pids or "(all)")
    print("\n=== ALL top-level windows (visible + hidden) ===")
    for pid, hwnd, vis, cls, title, rect, top in sorted(all_windows()):
        if pids and pid not in pids:
            continue
        print("  pid=%-7d hwnd=%-9d vis=%-5s top=%-5s rect=%-20s class=%-30s title=%r"
              % (pid, hwnd, vis, top, "%d,%d %dx%d" % tuple(rect), cls, title[:70]))
    print("\n=== CPU time ===")
    for pid in sorted(pids or []):
        print("  pid=%d cpu=%s" % (pid, cpu(pid)))


if __name__ == "__main__":
    main()
