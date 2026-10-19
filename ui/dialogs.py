"""
Themed popups for mtools.
File selection uses the native tkinter.filedialog, since OS file dialogs can't be themed anyway.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog

from data import settings
from . import style

_last_dir: str | None = settings.get("last_dir")  # file dialogs reopen where the user last picked/saved a file (kept between sessions)
if _last_dir and not os.path.isdir(_last_dir):
    _last_dir = None


def _remember_dir(path: str) -> None:
    global _last_dir
    _last_dir = os.path.dirname(path)
    settings.set("last_dir", _last_dir)


class ThemedDialog(tk.Toplevel):
    # Modal popup styled to match the app's color scheme

    def __init__(self, parent, title: str, message: str, buttons: list[str], with_entry: bool = False):
        super().__init__(parent)
        self.configure(bg=style.COLOR_BG)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        
        style.force_dark_titlebar(self)

        self.grab_set()

        self.result: str | None = None
        self.entry_value: str | None = None

        ttk.Label(self, text=message, wraplength=280, justify="left").pack(padx=20, pady=(20, 10))

        if with_entry:
            self.entry = ttk.Entry(self, width=30)
            self.entry.pack(padx=20, pady=(0, 10))
            self.entry.focus_set()
            self.entry.bind("<Return>", lambda e: self._on_button(buttons[0]))

        btn_row = ttk.Frame(self)
        btn_row.pack(padx=20, pady=(0, 20))
        for label in buttons:
            ttk.Button(btn_row, text=label, command=lambda l=label: self._on_button(l)).pack(side="left", padx=5)

        self.bind("<Escape>", lambda e: self._on_button(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self._on_button(None))

        self.update_idletasks()
        self._center_on(parent)
        self.wait_window(self)

    def _center_on(self, parent) -> None:
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _on_button(self, label: str | None) -> None:
        self.result = label
        if hasattr(self, "entry"):
            self.entry_value = self.entry.get()
        self.grab_release()
        self.destroy()


def show_error(parent, title: str, message: str) -> None:
    ThemedDialog(parent, title, message, buttons=["OK"])


def ask_yes_no(parent, title: str, message: str) -> bool:
    dlg = ThemedDialog(parent, title, message, buttons=["Yes", "No"])
    return dlg.result == "Yes"


def ask_string(parent, title: str, message: str) -> str | None:
    dlg = ThemedDialog(parent, title, message, buttons=["OK", "Cancel"], with_entry=True)
    if dlg.result == "OK" and dlg.entry_value:
        return dlg.entry_value
    return None


def show_info(parent, title: str, message: str) -> None:
    ThemedDialog(parent, title, message, buttons=["OK"])


def ask_choice(parent, title: str, message: str, buttons: list[str]) -> str | None:
    # Several-button question; returns the clicked label (None if the window was closed/Escape)
    return ThemedDialog(parent, title, message, buttons=buttons).result


def ask_open_file(parent, title: str = "Select file", filetypes=(("All files", "*.*"),)) -> str | None:
    path = filedialog.askopenfilename(parent=parent, title=title, filetypes=filetypes, initialdir=_last_dir)
    if path:
        _remember_dir(path)
    return path or None


def ask_save_file(parent, title: str = "Save file", filetypes=(("CSV", "*.csv"), ("All files", "*.*")), initialfile: str | None = None, defaultextension: str | None = None) -> str | None:
    # Native save dialog (asks before overwriting itself); without an explicit defaultextension the first filetype's extension is appended if none was typed
    if defaultextension is None:
        defaultextension = os.path.splitext(filetypes[0][1].split()[0])[1] if filetypes else ""
    path = filedialog.asksaveasfilename(parent=parent, title=title, filetypes=filetypes, defaultextension=defaultextension, initialdir=_last_dir, initialfile=initialfile or "")
    if path:
        _remember_dir(path)
    return path or None
