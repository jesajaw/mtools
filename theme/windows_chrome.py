"""Windows-only visual fixes tkinter doesn't handle by itself: DPI
awareness (fixes blurry/blocky text on HiDPI displays) and a dark
title bar to match the rest of the theme. Both are no-ops on
non-Windows platforms."""

import sys


def enable_dpi_awareness() -> None:
    """Call once, before creating the Tk root. Without this, Windows
    renders the whole app at 96 DPI and then bitmap-scales it up on
    HiDPI displays -- that's what makes the text look blocky."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # fallback for older Windows
        except Exception:
            pass


def apply_dark_titlebar(window) -> None:
    """Call after a Tk/Toplevel window has been built (needs a real
    window handle). Colors the native title bar dark to match the
    theme instead of the default light OS chrome."""
    if sys.platform != "win32":
        return
    import ctypes
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 (Win10 2004+), 19 (older)
        value = ctypes.c_int(1)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result == 0:
            break