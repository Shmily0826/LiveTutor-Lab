"""Control experiment: can this session create ANY visible top-level window?
Tries tkinter (if present) and a raw Win32 window via ctypes. If raw Win32 works,
GUI is available and N.E.K.O's silence is its own problem. If neither works,
the environment cannot host GUI apps and that is the honest explanation.
"""
import ctypes, ctypes.wintypes as wintypes, time, os

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
u32.SetProcessDPIAware()

print("=== 1. session / desktop info ===")
h_desk = u32.GetThreadDesktop(k32.GetCurrentThreadId())
print("  desktop handle:", h_desk)
buf = ctypes.create_unicode_buffer(256); need = wintypes.DWORD()
u32.GetUserObjectInformationW(u32.GetProcessWindowStation(), 2, buf, 512, ctypes.byref(need))
print("  window station:", buf.value)
u32.GetUserObjectInformationW(h_desk, 2, buf, 512, ctypes.byref(need))
print("  desktop name  :", buf.value)

print("\n=== 2. create raw Win32 window (ctypes) ===")
WNDCLASS_NAME = "NEKOLabProbeCls"
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, ctypes.c_uint,
                             ctypes.c_size_t, ctypes.c_ssize_t)

class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

def wndproc(h, m, w, l):
    return u32.DefWindowProcW(h, m, w, l)

hInst = k32.GetModuleHandleW(None)
wc = WNDCLASS()
wc.lpfnWndProc = WNDPROC(wndproc)
wc.hInstance = hInst
wc.lpszClassName = WNDCLASS_NAME
atom = u32.RegisterClassW(ctypes.byref(wc))
print("  RegisterClassW atom:", atom, "(0 = FAILED, err=%d)" % k32.GetLastError())

hwnd = u32.CreateWindowExW(0, WNDCLASS_NAME, "NEKO_LAB_CONTROL_PROBE",
                           0x00CF0000, 60, 60, 420, 140,
                           None, None, hInst, None)
print("  CreateWindowExW hwnd:", hwnd, "(0 = FAILED, err=%d)" % k32.GetLastError())

if hwnd:
    u32.ShowWindow(hwnd, 5)   # SW_SHOW
    u32.UpdateWindow(hwnd)
    time.sleep(1.5)
    print("  IsWindowVisible:", bool(u32.IsWindowVisible(hwnd)))
    # enumerate to confirm it is discoverable
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if h == hwnd:
            found.append(h)
        return True
    u32.EnumWindows(cb, 0)
    print("  EnumWindows finds it:", bool(found))
    # foreground check
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    fg = u32.GetForegroundWindow()
    b = ctypes.create_unicode_buffer(256); u32.GetWindowTextW(fg, b, 256)
    print("  foreground window now:", repr(b.value))
    u32.DestroyWindow(hwnd)
    print("  => GUI SUBSYSTEM WORKS in this session")
else:
    print("  => raw Win32 window creation FAILED — GUI not available to this process")

print("\n=== 3. can we even SEE the interactive desktop? ===")
print("  SM_CXSCREEN =", u32.GetSystemMetrics(0), "x", u32.GetSystemMetrics(1))
print("  (note: 2880x1800 = physical, matching earlier Win32 enumeration of real windows)")

print("\n=== 4. conclusion inputs gathered ===")
