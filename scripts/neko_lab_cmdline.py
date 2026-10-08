"""Read a process command line via PEB (no WMI, no PowerShell)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import sys
from struct import unpack

ntdll = ctypes.WinDLL("ntdll")
k32 = ctypes.WinDLL("kernel32")

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
ProcessBasicInformation = 0


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Reserved1", ctypes.c_void_p),
        ("PebBaseAddress", ctypes.c_void_p),
        ("Reserved2", ctypes.c_void_p * 2),
        ("UniqueProcessId", ctypes.c_void_p),
        ("Reserved3", ctypes.c_void_p),
    ]


def read_memory(handle, address, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size,
                               ctypes.byref(read))
    return bytes(buf[: read.value]) if ok else None


def cmdline_of(pid):
    handle = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                             False, pid)
    if not handle:
        return None
    try:
        pbi = PROCESS_BASIC_INFORMATION()
        status = ntdll.NtQueryInformationProcess(
            handle, ProcessBasicInformation, ctypes.byref(pbi),
            ctypes.sizeof(pbi), None)
        if status != 0 or not pbi.PebBaseAddress:
            return None
        peb = read_memory(handle, pbi.PebBaseAddress, 0x40)
        if not peb:
            return None
        # x64 PEB: ProcessParameters at offset 0x20
        params_ptr = unpack("<Q", peb[0x20:0x28])[0]
        params = read_memory(handle, params_ptr, 0x100)
        if not params:
            return None
        # RTL_USER_PROCESS_PARAMETERS: CommandLine UNICODE_STRING at 0x70.
        # UNICODE_STRING on x64 is {USHORT Length; USHORT MaximumLength;
        # 4 bytes padding; PVOID Buffer} so the pointer sits at 0x78, not 0x74.
        if len(params) < 0x80:
            return None
        length = unpack("<H", params[0x70:0x72])[0]
        ptr = unpack("<Q", params[0x78:0x80])[0]
        if not ptr or length == 0:
            return None
        raw = read_memory(handle, ptr, length)
        return raw.decode("utf-16-le", errors="replace") if raw else None
    finally:
        k32.CloseHandle(handle)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pids = [int(a) for a in sys.argv[1:]] or [3812]
    print(json.dumps({str(p): cmdline_of(p) for p in pids},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
