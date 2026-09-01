"""
Central theme for mtools.

Color scheme matches previous convention (see DMX Derby Controller
reference): several palettes are available, the active one is chosen
via COLOR_SCHEME. Every window (main + tool windows) calls
apply_style() once on root/Toplevel and shares the same style names
(Cell.TFrame, CellTitle.TLabel, Status.TLabel, ...).
"""

import sys

# ------------------------------------------------------------
# Color schemes (as before: several palettes, one active)
# ------------------------------------------------------------
_SCHEMES = {
    "dark_purple": dict(
        BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0",
        ACCENT="#9b59d9", ACCENT_DARK="#6c3fa0", STATUS_TEXT="#c9a6f5",
    ),
    "dark_blue": dict(
        BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0",
        ACCENT="#4a90d9", ACCENT_DARK="#2f5f9e", STATUS_TEXT="#a6c9f5",
    ),
    "black_white": dict(
        BG="#000000", BG_LIGHT="#1a1a1a", FG="#ffffff",
        ACCENT="#ffffff", ACCENT_DARK="#808080", STATUS_TEXT="#d9d9d9",
    ),
}

COLOR_SCHEME = "dark_purple"  # switch palette here

_active = _SCHEMES[COLOR_SCHEME]
COLOR_BG = _active["BG"]
COLOR_BG_LIGHT = _active["BG_LIGHT"]
COLOR_FG = _active["FG"]
COLOR = _active["ACCENT"]
COLOR_DARK = _active["ACCENT_DARK"]
COLOR_STATUS_TEXT = _active["STATUS_TEXT"]

# ------------------------------------------------------------
# Layout constants (cell grid, as before)
# ------------------------------------------------------------
CELL_WIDTH = 260
CELL_HEIGHT = 110
STATUS_LABEL_CHARS = 32


def apply_style(root) -> None:
    """Applies the theme to root (Tk or Toplevel): background +
    ttk styles. Call once per window (main, tool windows) before
    building widgets."""
    from tkinter import ttk

    root.configure(bg=COLOR_BG)
    apply_dark_titlebar(root)

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=("Segoe UI", 9))
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_FG, bordercolor=COLOR_DARK)
    style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)

    style.configure("TButton", background=COLOR_BG_LIGHT, foreground=COLOR_FG,
                     bordercolor=COLOR_DARK, focusthickness=1, padding=6)
    style.map("TButton", background=[("active", COLOR_DARK), ("pressed", COLOR)],
              foreground=[("active", COLOR_FG)])

    style.configure("TCombobox", fieldbackground=COLOR_BG_LIGHT, background=COLOR_BG_LIGHT,
                     foreground=COLOR_FG, arrowcolor=COLOR)
    style.map("TCombobox", fieldbackground=[("readonly", COLOR_BG_LIGHT)])
    style.configure("Horizontal.TScale", background=COLOR_BG, troughcolor=COLOR_BG_LIGHT)
    style.configure("TEntry", fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_FG, insertcolor=COLOR_FG)

    style.configure("Accent.TButton", background=COLOR_DARK, foreground=COLOR_FG)
    style.map("Accent.TButton", background=[("active", COLOR)])

    style.configure("Cell.TFrame", background=COLOR_BG_LIGHT, bordercolor=COLOR_DARK)
    style.configure("Status.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_STATUS_TEXT, font=("Consolas", 9))
    style.configure("CellTitle.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_FG, font=("Segoe UI", 9, "bold"))

    # hover state for clickable cells (see main.py MainWindow._build_cell)
    style.configure("CellHover.TFrame", background=COLOR_DARK, bordercolor=COLOR)
    style.configure("StatusHover.TLabel", background=COLOR_DARK, foreground=COLOR_STATUS_TEXT, font=("Consolas", 9))
    style.configure("CellTitleHover.TLabel", background=COLOR_DARK, foreground=COLOR_FG, font=("Segoe UI", 9, "bold"))

    style.configure("CategoryHeader.TLabel", background=COLOR_BG, foreground=COLOR, font=("Segoe UI", 10, "bold"))


# ------------------------------------------------------------
# Windows-only visual fixes tkinter doesn't handle by itself: DPI
# awareness (fixes blurry/blocky text on HiDPI displays) and a dark
# title bar to match the theme. Both are no-ops on non-Windows.
# ------------------------------------------------------------

def enable_dpi_awareness() -> None:
    """Call once, before creating the Tk root."""
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
    window handle)."""
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
