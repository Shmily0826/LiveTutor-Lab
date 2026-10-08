#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Determine whether benchmarks/raw/neko-app/N.E.K.O.exe is:
  (a) an NSIS installer (previous evaluation's conclusion), or
  (b) the real Electron shell executable sitting in an extracted app dir.

Read-only. No execution, no writes outside stdout.
"""
import os
import struct
import sys

ROOT = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw"
EXE = os.path.join(ROOT, "neko-app", "N.E.K.O.exe")
ZIP = os.path.join(ROOT, "neko-v0.9.0-win.zip")

MARKERS = [
    b"Nullsoft", b"Nullsoft Install System", b"NSIS", b"nsis",
    b"Electron", b"electron", b"Electron Framework",
    b"app.asar", b"app-64.7z", b"app.7z", b"7z\xbc\xaf\x27\x1c",
    b"chrome_100_percent.pak", b"v8_context_snapshot.bin",
    b"GHBDRISD",  # electron-builder asar integrity marker
]


def read_pe(path):
    with open(path, "rb") as f:
        dos = f.read(0x400)
    if dos[:2] != b"MZ":
        return {"error": "not MZ"}
    e_lfanew = struct.unpack_from("<I", dos, 0x3C)[0]
    with open(path, "rb") as f:
        f.seek(e_lfanew)
        sig = f.read(4)
        coff = f.read(20)
        machine, nsec, _, _, _, opt_size, characteristics = struct.unpack("<HHIIIHH", coff)
        opt_magic = struct.unpack("<H", f.read(2))[0]
        is_pe32p = opt_magic == 0x20B
        # skip to section table: e_lfanew + 24 + opt_size
        f.seek(e_lfanew + 24 + opt_size)
        secs_raw = f.read(40 * nsec)
    secs = []
    for i in range(nsec):
        name = secs_raw[i * 40:i * 40 + 8].rstrip(b"\x00").decode("ascii", "replace")
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", secs_raw, i * 40 + 8)
        secs.append((name, vsize, vaddr, rsize, raddr))
    return {
        "machine": hex(machine),
        "pe32+": bool(is_pe32p),
        "nsec": nsec,
        "opt_magic": hex(opt_magic),
        "characteristics": hex(characteristics),
        "sections": secs,
    }


def scan_markers(path, markers, max_hits=3):
    size = os.path.getsize(path)
    hits = {m: [] for m in markers}
    chunk = 8 * 1024 * 1024
    overlap = 256
    pos = 0
    prev_tail = b""
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            data = prev_tail + buf
            base = pos - len(prev_tail)
            for m in markers:
                if len(hits[m]) >= max_hits:
                    continue
                start = 0
                while True:
                    idx = data.find(m, start)
                    if idx < 0:
                        break
                    if len(hits[m]) < max_hits:
                        hits[m].append(base + idx)
                    start = idx + 1
                    if len(hits[m]) >= max_hits:
                        break
            pos += len(buf)
            prev_tail = buf[-overlap:]
    return size, hits


def main():
    print("=" * 78)
    print("TARGET:", EXE)
    print("exists:", os.path.exists(EXE), "size:", os.path.getsize(EXE) if os.path.exists(EXE) else "-")
    if not os.path.exists(EXE):
        return
    pe = read_pe(EXE)
    for k, v in pe.items():
        if k == "sections":
            print("\n-- PE sections --")
            for s in v:
                print("   %-16s vsize=%-12d vaddr=%-10d rsize=%-10d raddr=%d" % s)
        else:
            print("%-16s %s" % (k, v))
    print("\n-- marker scan (offsets; max 3 each) --")
    size, hits = scan_markers(EXE, MARKERS)
    print("file size:", size)
    for m in MARKERS:
        offs = hits[m]
        if offs:
            print("   %-28s %d hit(s) @ %s" % (m.decode("ascii", "replace"), len(offs), offs))
    print("\n" + "=" * 78)
    print("ZIP:", ZIP, "exists:", os.path.exists(ZIP))
    if os.path.exists(ZIP):
        import zipfile
        try:
            with zipfile.ZipFile(ZIP) as z:
                names = z.namelist()
                print("entries:", len(names))
                tops = {}
                for n in names:
                    parts = n.split("/")
                    key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
                    tops[key] = tops.get(key, 0) + 1
                for k in sorted(tops)[:60]:
                    print("   %-70s %d" % (k, tops[k]))
        except Exception as e:
            print("zip read failed:", type(e).__name__, e)


if __name__ == "__main__":
    main()
