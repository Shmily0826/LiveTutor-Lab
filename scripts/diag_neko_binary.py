import subprocess, os, time, sys, ctypes

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
CWD = os.path.dirname(APP)

print("=== exe 基本信息 ===")
with open(APP, "rb") as f:
    head = f.read(1024)
print("size:", os.path.getsize(APP), "bytes")
print("MZ header:", head[:2])

# PE machine type
import struct
with open(APP, "rb") as f:
    f.seek(0x3C)
    pe_off = struct.unpack("<I", f.read(4))[0]
    f.seek(pe_off)
    sig = f.read(4)
    machine = struct.unpack("<H", f.read(2))[0]
machines = {0x14c: "x86 (32-bit)", 0x8664: "x64", 0xaa64: "ARM64"}
print("PE sig:", sig, "machine:", hex(machine), "=", machines.get(machine, "unknown"))

print("\n=== 直接运行并捕获退出码 (20s window) ===")
try:
    p = subprocess.Popen([APP], cwd=CWD, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, errors="replace")
    print("pid:", p.pid)
    for t in (3, 8, 15, 20):
        time.sleep(t - (0 if t == 3 else (3 if t == 8 else (8 if t == 15 else 15))))
        rc = p.poll()
        print("  t~%2ds poll=%r" % (t, rc))
        if rc is not None:
            out, _ = p.communicate(timeout=10)
            print("  --- captured output (%d chars) ---" % len(out or ""))
            print((out or "")[:3000])
            print("  exit code:", rc)
            break
    else:
        print("  still running after 20s, killing by exact pid")
        p.kill()
        out, _ = p.communicate(timeout=10)
        print("  --- output ---")
        print((out or "")[:2000])
except Exception as e:
    print("EXCEPTION:", type(e).__name__, e)
