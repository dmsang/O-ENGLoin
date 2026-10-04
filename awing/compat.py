"""awing/compat.py — Platform detection and Windows-only console API."""
import sys

IS_WIN   = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

if IS_WIN:
    import ctypes as _ct
    _k32 = _ct.windll.kernel32
    _u32 = _ct.windll.user32
    _k32.SetConsoleMode(_k32.GetStdHandle(-11), 7)
else:
    _ct = None
    _k32 = None
    _u32 = None

_HWND = [0]

def _get_hwnd():
    if not IS_WIN: return 0
    if _HWND[0] == 0:
        import ctypes
        _HWND[0] = ctypes.windll.kernel32.GetConsoleWindow()
    return _HWND[0]

def hide_console():
    if not IS_WIN: return
    hwnd = _get_hwnd()
    if hwnd: _u32.ShowWindow(hwnd, 0)

def show_console():
    if not IS_WIN: return
    hwnd = _get_hwnd()
    if hwnd:
        _u32.ShowWindow(hwnd, 9)
        _u32.SetForegroundWindow(hwnd)

# subprocess flag for Windows to suppress console windows
NO_WIN = {"creationflags": __import__("subprocess").CREATE_NO_WINDOW} if IS_WIN else {}