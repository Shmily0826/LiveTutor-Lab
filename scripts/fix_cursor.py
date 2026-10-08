#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnose and repair a hidden / replaced system cursor.

N.E.K.O's tutorial overlay hides the user cursor (log:
  [SystemCursor] tutorial relay hidden=true reason=user_cursor_reveal_suppressed)
via a spawned powershell.exe helper. Killing the app mid-tutorial leaves the
cursor suppressed.

Repair = reload cursors from the registry scheme:
  SystemParametersInfoW(SPI_SETCURSORS, 0, NULL, SPIF_UPDATEINIFILE|SPIF_SENDCHANGE)
"""
import ctypes
import sys
from ctypes import wintypes

u32 = ctypes.WinDLL("user32", use_last_error=True)

SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002
CURSOR_SHOWING = 0x00000001


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("hCursor", wintypes.HANDLE), ("ptScreenPos", POINT)]


def cursor_state():
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(ci)
    ok = u32.GetCursorInfo(ctypes.byref(ci))
    if not ok:
        return None
    return {
        "flags": ci.flags,
        "showing": bool(ci.flags & CURSOR_SHOWING),
        "hCursor": ci.hCursor or 0,
        "pos": (ci.ptScreenPos.x, ci.ptScreenPos.y),
    }


def main():
    print("=" * 62)
    print("cursor repair")
    print("=" * 62)
    before = cursor_state()
    print("before: %s" % before)

    ctypes.set_last_error(0)
    rc = u32.SystemParametersInfoW(
        SPI_SETCURSORS, 0, None,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    )
    err = ctypes.get_last_error()
    print("")
    print("SystemParametersInfoW(SPI_SETCURSORS) -> rc=%s  last_error=%s" % (rc, err))

    after = cursor_state()
    print("after : %s" % after)

    print("")
    if after and after["showing"]:
        print("RESULT: cursor is SHOWING again (flags has CURSOR_SHOWING).")
    else:
        print("RESULT: still not showing. Manual fallback:")
        print("  1. Win+R -> main.cpl -> Pointers tab")
        print("     Scheme: 'Windows Default' -> Apply -> OK")
        print("  2. If still hidden, sign out and back in (reloads cursor objects).")

    return 0 if (after and after["showing"]) else 1


if __name__ == "__main__":
    sys.exit(main())
