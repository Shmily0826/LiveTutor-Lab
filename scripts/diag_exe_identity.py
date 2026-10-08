#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Decide definitively whether neko-app/N.E.K.O.exe is an Electron shell or an NSIS
installer, without executing it.

Signals used:
  1. UTF-16LE VS_VERSION_INFO strings (CompanyName / FileDescription / ProductName)
  2. UTF-16LE 'Nullsoft Install System' presence
  3. Context bytes around each 'NSIS' / 'Electron' / 'app.asar' literal hit
"""
import os
import struct

EXE = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"


def find_all(path, needle, limit=6):
    out = []
    base = 0
    prev = b""
    with open(path, "rb") as f:
        while True:
            buf = f.read(8 * 1024 * 1024)
            if not buf:
                break
            data = prev + buf
            b0 = base - len(prev)
            i = 0
            while True:
                j = data.find(needle, i)
                if j < 0:
                    break
                out.append(b0 + j)
                if len(out) >= limit:
                    return out
                i = j + 1
            base += len(buf)
            prev = buf[-512:]
    return out


def context(path, off, before=140, after=180):
    with open(path, "rb") as f:
        f.seek(max(0, off - before))
        raw = f.read(before + after)
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in raw)
    return printable


def utf16_find(path, text, limit=6):
    return find_all(path, text.encode("utf-16-le"), limit)


def main():
    print("size:", os.path.getsize(EXE))
    print("\n=== UTF-16LE probes ===")
    for t in ["Electron", "CompanyName", "FileDescription", "ProductName",
              "OriginalFilename", "Nullsoft", "N.E.K.O", "GitHub"]:
        offs = utf16_find(EXE, t)
        print("  %-18s %s" % (t, offs if offs else "NOT FOUND"))

    print("\n=== context around UTF-16 'Electron' / 'CompanyName' ===")
    for t in ["CompanyName", "FileDescription", "ProductName", "OriginalFilename"]:
        offs = utf16_find(EXE, t, 2)
        for o in offs[:1]:
            print("  [%s @ %d]" % (t, o))
            print("   ", context(EXE, o, 0, 260))

    print("\n=== context around ASCII 'NSIS' hits ===")
    for o in find_all(EXE, b"NSIS", 3):
        print("  @%d: %s" % (o, context(EXE, o)))

    print("\n=== context around ASCII 'Electron' ===")
    for o in find_all(EXE, b"Electron", 3):
        print("  @%d: %s" % (o, context(EXE, o, 100, 160)))

    print("\n=== context around ASCII 'app.asar' ===")
    for o in find_all(EXE, b"app.asar", 3):
        print("  @%d: %s" % (o, context(EXE, o, 100, 160)))


if __name__ == "__main__":
    main()
