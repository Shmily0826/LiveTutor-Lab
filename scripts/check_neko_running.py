#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List any still-running N.E.K.O / OpenFang / script-host processes."""
import ctypes
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


NEEDLES = ("n.e.k.o", "openfang", "pwsh", "windowsterminal")


def main():
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == -1:
        print("snapshot failed")
        return 1
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    rows = []
    ok = k32.Process32FirstW(h, ctypes.byref(pe))
    while ok:
        low = pe.szExeFile.lower()
        if any(n in low for n in NEEDLES):
            rows.append((pe.th32ProcessID, pe.th32ParentProcessID,
                         pe.szExeFile, pe.cntThreads))
        ok = k32.Process32NextW(h, ctypes.byref(pe))
    k32.CloseHandle(h)

    if not rows:
        print("no N.E.K.O / OpenFang processes running")
        return 0
    print("still running (%d):" % len(rows))
    for pid, ppid, name, th in sorted(rows):
        print("  pid=%-7d ppid=%-7d %-28s threads=%d" % (pid, ppid, name, th))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
