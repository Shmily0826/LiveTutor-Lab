#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Capture the primary screen with GDI and write a PNG (pure stdlib)."""
import ctypes
import struct
import sys
import zlib
from ctypes import wintypes

g32 = ctypes.WinDLL("gdi32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPFILEHEADER(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("bfType", wintypes.WORD), ("bfSize", wintypes.DWORD),
                ("bfReserved1", wintypes.WORD), ("bfReserved2", wintypes.WORD),
                ("bfOffBits", wintypes.DWORD)]


def main(out_path, scale=1):
    w = u32.GetSystemMetrics(SM_CXSCREEN)
    h = u32.GetSystemMetrics(SM_CYSCREEN)
    hdc_screen = u32.GetDC(0)
    hdc_mem = g32.CreateCompatibleDC(hdc_screen)
    bmp = g32.CreateCompatibleBitmap(hdc_screen, w, h)
    g32.SelectObject(hdc_mem, bmp)

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth = w
    bi.biHeight = -h          # top-down
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = BI_RGB
    bi.biSizeImage = 0

    stride = ((w * 32 + 31) // 32) * 4
    buf = ctypes.create_string_buffer(stride * h)
    got = g32.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), DIB_RGB_COLORS)
    if not got:
        print("GetDIBits failed")
        return 1
    data = bytes(buf)

    sw, sh = w // scale, h // scale
    # BGRA -> RGB rows
    rows = []
    for y in range(0, sh):
        src_y = y * scale
        off = src_y * stride
        row = bytearray()
        for x in range(sw):
            p = off + (x * scale) * 4
            b, g, r = data[p], data[p + 1], data[p + 2]
            row += bytes((r, g, b))
        rows.append(bytes(row))
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", sw, sh, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(out_path, "wb") as f:
        f.write(png)
    print("wrote %s  %dx%d  %d bytes" % (out_path, sw, sh, len(png)))

    g32.DeleteObject(bmp)
    g32.DeleteDC(hdc_mem)
    u32.ReleaseDC(0, hdc_screen)
    return 0


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "screen.png"
    sc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sys.exit(main(p, sc))
