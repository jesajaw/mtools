"""
Windows-only visual fixes tkinter doesnt handle by itself: DPI awareness (fixes blurry/blocky text on HiDPI displays) and a dark title bar to match the rest of the theme. Both are no-ops on non-Windows platforms.
"""

import sys, ctypes

def _is_win32():
    if not sys.platform != "win32":
        return True
    return

def enable_dpi_awareness() -> None:
    """
    Call once, before creating the Tk root. Without this, Windows renders the whole app at 96 DPI and then bitmap-scales it up on
    HiDPI displays.
    """
    if _is_win32() is None:
        return
    try:
        # PROCESS_SYSTEM_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # fallback for older Windows
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def apply_dark_titlebar(window) -> None:
    # Call after a Tk/Toplevel window has been built. Colors the native title bar dark to match the theme.
    if _is_win32() is None:
        return
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 (Win10 2004+), 19 (older)
    for attribute in (20, 19):
        value = ctypes.c_int(1)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        if result == 0:
            break