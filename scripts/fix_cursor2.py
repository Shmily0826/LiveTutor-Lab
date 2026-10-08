#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Force-restore the standard Windows cursors with SetSystemCursor, then persist
via SPI_SETCURSORS.

Needed because N.E.K.O's tutorial overlay suppresses the user cursor
("[SystemCursor] ... reason=user_cursor_reveal_suppressed") by installing a
transparent system cursor through a spawned powershell.exe helper. Killing the
app mid-tutorial leaves that cursor installed. The registry scheme stays
correct, so reloading from the scheme is the right repair.
"""
import ctypes
import os
import sys
from ctypes import wintypes

u32 = ctypes.WinDLL("user32", use_last_error=True)

OCR_NORMAL = 32512
OCR_IBEAM = 32513
OCR_WAIT = 32514
OCR_CROSS = 32515
OCR_UP = 32516
OCR_SIZE = 32640
OCR_ICON = 32641
OCR_SIZENWSE = 32642
OCR_SIZENESW = 32643
OCR_SIZEWE = 32644
OCR_SIZENS = 32645
OCR_SIZEALL = 32646
OCR_NO = 32648
OCR_HAND = 32649
OCR_APPSTARTING = 32650

LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
IMAGE_CURSOR = 2

SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002
CURSOR_SHOWING = 0x00000001

CURSORS = r"C:\Windows\Cursors"

TARGETS = [
    (OCR_NORMAL, "aero_arrow.cur"),
    (OCR_IBEAM, None),           # IBeam has no file in the scheme
    (OCR_WAIT, "aero_busy.ani"),
    (OCR_CROSS, None),
    (OCR_UP, "aero_up.cur"),
    (OCR_SIZE, None),
    (OCR_ICON, None),
    (OCR_SIZENWSE, "aero_nwse.cur"),
    (OCR_SIZENESW, "aero_nesw.cur"),
    (OCR_SIZEWE, "aero_ew.cur"),
    (OCR_SIZENS, "aero_ns.cur"),
    (OCR_SIZEALL, "aero_move.cur"),
    (OCR_NO, "aero_unavail.cur"),
    (OCR_HAND, "aero_link.cur"),
    (OCR_APPSTARTING, "aero_working.ani"),
]


class CURSORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("hCursor", wintypes.HANDLE),
                ("ptScreenPos", ctypes.c_long * 2)]


def cursor_state():
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(ci)
    if not u32.GetCursorInfo(ctypes.byref(ci)):
        return None
    return bool(ci.flags & CURSOR_SHOWING), ci.hCursor or 0


def main():
    print("=" * 66)
    print("restore standard system cursors")
    print("=" * 66)
    print("before: showing=%s hCursor=%s" % cursor_state())
    print("")

    ok_count = 0
    for cid, fname in TARGETS:
        if not fname:
            continue
        path = os.path.join(CURSORS, fname)
        if not os.path.isfile(path):
            print("  MISSING FILE  %-20s (skip)" % fname)
            continue
        ctypes.set_last_error(0)
        h = u32.LoadImageW(None, path, IMAGE_CURSOR, 0, 0,
                           LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not h:
            print("  LoadImage FAIL %-20s err=%s" % (fname, ctypes.get_last_error()))
            continue
        ctypes.set_last_error(0)
        rc = u32.SetSystemCursor(h, cid)
        err = ctypes.get_last_error()
        print("  %-20s -> SetSystemCursor rc=%s err=%s" % (fname, rc, err))
        if rc:
            ok_count += 1

    print("")
    print("restored %d cursors" % ok_count)

    ctypes.set_last_error(0)
    rc = u32.SystemParametersInfoW(SPI_SETCURSORS, 0, None,
                                   SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
    print("SPI_SETCURSORS -> rc=%s err=%s" % (rc, ctypes.get_last_error()))

    print("")
    print("after : showing=%s hCursor=%s" % cursor_state())
    return 0


if __name__ == "__main__":
    sys.exit(main())
