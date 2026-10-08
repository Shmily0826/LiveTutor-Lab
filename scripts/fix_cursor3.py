#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete cursor restore: cover ALL 18 IDs that N.E.K.O's helper blanks.

N.E.K.O's `system-cursor-visibility-service.js` builds a 32x32 fully
transparent cursor (AND mask 0xFF, XOR mask 0x00) and SetSystemCursor's it onto:

  32512 32513 32514 32515 32516 32640 32641 32642 32643 32644
  32645 32646 32648 32649 32650 32651 32671 32672

then waits on stdin for "restore" before calling SystemParametersInfo(
SPI_SETCURSORS). Terminating the app hard skips that finally block, leaving
every one of those cursors transparent.

fix_cursor2.py only covered the 11 with scheme files. This restores the rest.
"""
import ctypes
import os
import sys
from ctypes import wintypes

u32 = ctypes.WinDLL("user32", use_last_error=True)

IMAGE_CURSOR = 2
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
LR_SHARED = 0x8000

CURSORS = r"C:\Windows\Cursors"

# id -> (human name, filename or None to load the built-in OEM resource)
TARGETS = [
    (32512, "ARROW",       "aero_arrow.cur"),
    (32513, "IBEAM",       "beam_m.cur"),
    (32514, "WAIT",        "aero_busy.ani"),
    (32515, "CROSS",       "cross_m.cur"),
    (32516, "UPARROW",     "aero_up.cur"),
    (32640, "SIZE",        "aero_move.cur"),   # legacy IDC_SIZE, no scheme file
    (32641, "ICON",        "aero_arrow.cur"),  # legacy IDC_ICON, no scheme file
    (32642, "SIZENWSE",    "aero_nwse.cur"),
    (32643, "SIZENESW",    "aero_nesw.cur"),
    (32644, "SIZEWE",      "aero_ew.cur"),
    (32645, "SIZENS",      "aero_ns.cur"),
    (32646, "SIZEALL",     "aero_move.cur"),
    (32648, "NO",          "aero_unavail.cur"),
    (32649, "HAND",        "aero_link.cur"),
    (32650, "APPSTARTING", "aero_working.ani"),
    (32651, "HELP",        "aero_helpsel.cur"),
    (32671, "PIN",         "aero_pin.cur"),
    (32672, "PERSON",      "aero_person.cur"),
]


def load_from_file(path):
    if not os.path.isfile(path):
        return 0, "no file"
    ctypes.set_last_error(0)
    h = u32.LoadImageW(None, path, IMAGE_CURSOR, 0, 0,
                       LR_LOADFROMFILE | LR_DEFAULTSIZE)
    return (h, "file") if h else (0, "LoadImage err=%s" % ctypes.get_last_error())


def load_oem(res_id):
    """Load the built-in OEM cursor resource (not the currently installed one)."""
    ctypes.set_last_error(0)
    name = ctypes.cast(ctypes.c_void_p(res_id), wintypes.LPCWSTR)
    h = u32.LoadImageW(None, name, IMAGE_CURSOR, 0, 0, LR_DEFAULTSIZE)
    return (h, "oem") if h else (0, "OEM LoadImage err=%s" % ctypes.get_last_error())


def main():
    print("=" * 74)
    print("complete cursor restore (all 18 IDs N.E.K.O blanks)")
    print("=" * 74)

    ok, fail = 0, []
    for cid, label, fname in TARGETS:
        handle, how = (0, "")
        if fname:
            handle, how = load_from_file(os.path.join(CURSORS, fname))
        if not handle:
            handle, how = load_oem(cid)
        if not handle:
            print("  %-12s %-6s LOAD FAILED (%s)" % (label, cid, how))
            fail.append(label)
            continue
        ctypes.set_last_error(0)
        rc = u32.SetSystemCursor(handle, cid)
        err = ctypes.get_last_error()
        if rc:
            ok += 1
            print("  %-12s %-6s restored via %s" % (label, cid, how))
        else:
            print("  %-12s %-6s SetSystemCursor FAILED err=%s" % (label, cid, err))
            fail.append(label)

    print("")
    print("restored %d/%d" % (ok, len(TARGETS)))
    if fail:
        print("still transparent: %s" % ", ".join(fail))
    else:
        print("all 18 cursor slots restored")

    # persist to the scheme so it survives a logoff
    ctypes.set_last_error(0)
    rc = u32.SystemParametersInfoW(0x0057, 0, None, 0x0001 | 0x0002)
    print("SPI_SETCURSORS -> rc=%s err=%s" % (rc, ctypes.get_last_error()))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
