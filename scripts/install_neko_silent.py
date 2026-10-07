"""Run the NSIS installer silently (/S /D=path) into a Lab-local install dir, then
verify the real Electron binary appears. Nothing is installed system-wide and no
process is killed by name.
"""
import ctypes, ctypes.wintypes as wintypes, time, os, subprocess, glob

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32

INSTALLER = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
TARGET = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-installed"

print("installer:", INSTALLER)
print("target   :", TARGET)
print("args     : /S /D=%s   (/S = silent NSIS, /D = destination, must be LAST and unquoted)" % TARGET)
print()

# NSIS /D must be last and unquoted
cmd = [INSTALLER, "/S", "/D=" + TARGET]
t0 = time.time()
p = subprocess.Popen(cmd, cwd=os.path.dirname(INSTALLER),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("installer pid:", p.pid)

last_size = -1
stable = 0
for i in range(1, 25):
    time.sleep(5)
    n = 0
    total = 0
    for root, dirs, files in os.walk(TARGET):
        for f in files:
            n += 1
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
    alive = p.poll() is None
    print("t=%3ds alive=%-5s files=%-6d size=%.2f GB" % (i * 5, alive, n, total / 1073741824))
    if not alive and p.returncode == 0:
        print("installer exited cleanly (rc=0) at ~%.1fs" % (time.time() - t0))
        break
    if not alive:
        print("installer exited rc=%s at ~%.1fs" % (p.returncode, time.time() - t0))
        break
    if n == last_size:
        stable += 1
        if stable >= 2:
            print("file count stable for 10s")
            break
    else:
        stable = 0
    last_size = n

print("\n=== installed tree (top 2 levels) ===")
if os.path.isdir(TARGET):
    for e in sorted(os.listdir(TARGET)):
        full = os.path.join(TARGET, e)
        if os.path.isdir(full):
            sz = sum(os.path.getsize(os.path.join(r, f))
                     for r, _, fs in os.walk(full) for f in fs
                     if os.path.exists(os.path.join(r, f)))
            print("  [DIR]  %-40s %8.1f MB" % (e, sz / 1048576))
        else:
            print("  [FILE] %-40s %8.1f MB" % (e, os.path.getsize(full) / 1048576))
    print("\n=== .exe files installed ===")
    for exe in sorted(glob.glob(os.path.join(TARGET, "**", "*.exe"), recursive=True),
                      key=lambda x: -os.path.getsize(x))[:10]:
        print("  %10.1f MB  %s" % (os.path.getsize(exe) / 1048576, exe.replace(TARGET + "\\", "")))
else:
    print("  TARGET DOES NOT EXIST — silent install did not produce files")
