"""PrintWindow-based window capture (GDI screen copy returns black in this session).

Usage: python scripts/neko_lab_window_shot.py <title-substring> <out.png> [--list]
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import struct
import sys
import zlib

g32 = ctypes.WinDLL("gdi32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
PW_RENDERFULLCONTENT = 0x00000002


class BMIH(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BMI(ctypes.Structure):
    _fields_ = [("bmiHeader", BMIH), ("bmiColors", wt.DWORD * 3)]


def list_windows():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lp):
        if u32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(300)
            u32.GetWindowTextW(hwnd, buf, 300)
            r = wt.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            w, h = r.right - r.left, r.bottom - r.top
            if buf.value.strip() and w > 100 and h > 100:
                found.append((hwnd, buf.value, w, h))
        return True

    u32.EnumWindows(cb, 0)
    return found


def find_window(part: str):
    matches = [w for w in list_windows() if part.lower() in w[1].lower()]
    if not matches:
        return None
    matches.sort(key=lambda item: item[2] * item[3], reverse=True)
    return matches[0]


def capture(hwnd, w, h, out_path: str) -> tuple[int, int]:
    hdc_win = u32.GetWindowDC(hwnd)
    hdc_mem = g32.CreateCompatibleDC(hdc_win)
    hbmp = g32.CreateCompatibleBitmap(hdc_win, w, h)
    g32.SelectObject(hdc_mem, hbmp)
    ok = u32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
    if not ok:
        g32.BitBlt(hdc_mem, 0, 0, w, h, hdc_win, 0, 0, SRCCOPY)
    bmi = BMI()
    bmi.bmiHeader.biSize = ctypes.sizeof(BMIH)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

    raw = bytearray()
    data = buf.raw
    for y in range(h):
        raw.append(0)
        row = data[y * w * 4:(y + 1) * w * 4]
        for x in range(w):
            i = x * 4
            raw += bytes((row[i + 2], row[i + 1], row[i]))

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload +
                struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
           chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))
    with open(out_path, "wb") as fh:
        fh.write(png)

    g32.DeleteObject(hbmp)
    g32.DeleteDC(hdc_mem)
    u32.ReleaseDC(hwnd, hdc_win)
    return w, h


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        for hwnd, title, w, h in list_windows():
            print(f"0x{hwnd:X} {w}x{h} {title}")
        return
    part, out = sys.argv[1], sys.argv[2]
    match = find_window(part)
    if not match:
        raise SystemExit(f"no window matching {part!r}")
    hwnd, title, w, h = match
    size = capture(hwnd, w, h, out)
    print(f"captured {title!r} {size} -> {out}")


if __name__ == "__main__":
    main()
