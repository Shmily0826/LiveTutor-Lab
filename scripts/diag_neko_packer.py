import os, glob, time, subprocess, re, ctypes, ctypes.wintypes as wintypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
size = os.path.getsize(APP)
print("=== exe size: %.1f MB ===" % (size / 1048576))
print("(normal Electron main process exe is 5-15 MB; >200 MB implies self-extracting bundle)")

# Look for packer / bundler signatures
print("\n=== packer signature scan (first 4 MB + PE section names) ===")
with open(APP, "rb") as f:
    head = f.read(4 * 1024 * 1024)
sigs = {
    b"NSIS": "NSIS installer (electron-builder portable target)",
    b"Inno Setup": "Inno Setup",
    b"7-Zip": "7-Zip SFX",
    b"PK\x03\x04": "embedded zip",
    b"pyi-": "PyInstaller bootloader",
    b"electron.asar": "embedded asar",
    b"app.asar": "app.asar reference",
    b"nsis": "nsis",
    b"PORTABLE_EXECUTABLE_DIR": "electron-builder portable",
    b"electron-builder": "electron-builder",
    b"N.E.K.O": "self-named",
    b"neko": "neko string in exe",
}
for sig, label in sigs.items():
    pos = head.find(sig)
    print("  %-26s %-52s %s" % (sig.decode("latin1"), label, ("@%d" % pos) if pos >= 0 else "not in first 4MB"))

# scan whole file for a few key markers (streamed)
print("\n=== full-file marker scan (streamed) ===")
markers = [b"NSIS", b"7-Zip", b"app.asar", b"electron-builder", b"PORTABLE_EXECUTABLE_DIR", b"N.E.K.O.exe", b".py", b"48911"]
found = {m: [] for m in markers}
with open(APP, "rb") as f:
    off = 0
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk:
            break
        for m in markers:
            i = chunk.find(m)
            if i >= 0 and len(found[m]) < 3:
                found[m].append(off + i)
        off += len(chunk)
for m, poss in found.items():
    print("  %-26s %s" % (m.decode("latin1"), poss if poss else "NOT FOUND"))

# PE sections
print("\n=== PE sections ===")
import struct
with open(APP, "rb") as f:
    f.seek(0x3C); pe = struct.unpack("<I", f.read(4))[0]
    f.seek(pe + 6); nsec = struct.unpack("<H", f.read(2))[0]
    f.seek(pe + 20); optsize = struct.unpack("<H", f.read(2))[0]
    f.seek(pe + 24 + optsize)
    for _ in range(nsec):
        nm = f.read(8).rstrip(b"\x00").decode("latin1", "replace")
        vsize, vaddr, rsize, raddr = struct.unpack("<IIII", f.read(16))
        f.read(16)
        print("  %-10s vsize=%-12d rsize=%-12d raddr=%d" % (nm, vsize, rsize, raddr))

# Is it still running? where is it spending time?
print("\n=== current N.E.K.O process state ===")
k32 = ctypes.windll.kernel32
TH32CS_SNAPPROCESS = 0x2
class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]
snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
pe2 = PE32(); pe2.dwSize = ctypes.sizeof(PE32)
pids = []
if k32.Process32First(snap, ctypes.byref(pe2)):
    while True:
        if b"neko" in pe2.szExeFile.lower():
            pids.append((pe2.th32ProcessID, pe2.cntThreads, pe2.szExeFile.decode()))
        if not k32.Process32Next(snap, ctypes.byref(pe2)):
            break
k32.CloseHandle(snap)
print("  running:", pids if pids else "NONE (exited)")

# Temp dir growth — is it self-extracting?
tmp = os.environ.get("TEMP", "")
print("\n=== TEMP for neko-ish dirs ===")
for d in sorted(glob.glob(os.path.join(tmp, "*"))):
    b = os.path.basename(d)
    if any(k in b.lower() for k in ("neko", "{", "electron", "nsis", "7z")):
        try:
            print("  %-60s dir=%s" % (d, os.path.isdir(d)))
        except Exception:
            pass

print("\n=== port check again ===")
net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
hits = [l for l in net.splitlines() if any(x in l for x in ("48911", "48912", "48915", "48916"))]
print("  ", hits if hits else "no neko ports listening")
