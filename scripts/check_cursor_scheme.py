#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read the current Windows cursor scheme without reg.exe / PowerShell."""
import ctypes
from ctypes import wintypes

HKEY_CURRENT_USER = 0x80000001
KEY_READ = 0x20019
REG_SZ = 1
REG_EXPAND_SZ = 2

advapi = ctypes.WinDLL("advapi32", use_last_error=True)


def read_values(subkey):
    hkey = wintypes.HKEY()
    rc = advapi.RegOpenKeyExW(HKEY_CURRENT_USER, subkey, 0, KEY_READ, ctypes.byref(hkey))
    if rc != 0:
        return None, rc
    out = {}
    i = 0
    while True:
        name = ctypes.create_unicode_buffer(512)
        nlen = wintypes.DWORD(512)
        typ = wintypes.DWORD()
        dlen = wintypes.DWORD(0)
        rc = advapi.RegEnumValueW(hkey, i, name, ctypes.byref(nlen), None,
                                  ctypes.byref(typ), None, ctypes.byref(dlen))
        if rc != 0:
            break
        buf = ctypes.create_string_buffer(dlen.value + 4)
        rc2 = advapi.RegQueryValueExW(hkey, name.value, None, ctypes.byref(typ),
                                      buf, ctypes.byref(wintypes.DWORD(dlen.value + 4)))
        if rc2 == 0 and typ.value in (REG_SZ, REG_EXPAND_SZ):
            out[name.value] = buf.raw[:dlen.value].decode("utf-16-le", "replace").rstrip("\x00")
        i += 1
    advapi.RegCloseKey(hkey)
    return out, 0


vals, rc = read_values(r"Control Panel\Cursors")
print("RegOpenKeyEx rc=%d" % rc)
if vals is None:
    print("could not read cursor key")
else:
    print("Scheme ((default)): %r" % vals.get("", ""))
    print("")
    for k in sorted(vals):
        if k == "":
            continue
        v = vals[k]
        flag = ""
        if v and "aero" not in v.lower() and "windows" not in v.lower():
            flag = "   <-- NON-STANDARD"
        print("  %-14s %s%s" % (k, v, flag))
    nonstandard = [k for k, v in vals.items()
                   if k and v and "aero" not in v.lower() and "windows" not in v.lower()]
    print("")
    print("non-standard entries: %s" % (nonstandard or "NONE"))
