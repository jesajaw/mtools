"""
Workspace window: every dataset of this session in one list -- pick which one the tools work on and "Save" exports ("Use"), rename, save or remove single datasets. Lives next to the main window's Load/Save bar, which keeps handling the common case (load a file, run tools, save the latest result).

'>' marks the current dataset, '*' a computed result that has not been saved yet.
"""

import tkinter as tk
from tkinter import ttk

from data import session, store
from . import dialogs, style


class WorkspaceWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Workspace")
        self.geometry("560x340")
        self.minsize(380, 240)
        style.apply_style(self)

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Datasets of this session -- tools work on the current one (>).  * = not saved yet", style="TLabel", wraplength=520, justify="left").pack(anchor="w", pady=(0, 8))

        box = ttk.Frame(body)
        box.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(box, activestyle="none", exportselection=False, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_FG, selectbackground=style.COLOR_DARK, selectforeground=style.COLOR_FG, highlightthickness=0, borderwidth=0, font=style.FONT_MONO_NORMAL)
        bar = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<Double-Button-1>", lambda _e: self._use())

        row = ttk.Frame(body)
        row.pack(fill="x", pady=(8, 0))
        for text, command in (("Use", self._use), ("Rename", self._rename), ("Save...", self._save), ("Remove", self._remove)):
            ttk.Button(row, text=text, command=command).pack(side="left", padx=(0, 6))

        self._shown: list = []
        self._refresh()
        store.subscribe(self._refresh)
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            store.unsubscribe(self._refresh)

    def _refresh(self) -> None:
        keep = self._selected()
        self._shown = store.all()
        unsaved = store.unsaved()
        self.listbox.delete(0, "end")
        for i, ds in enumerate(self._shown):
            current = ">" if store.is_current(ds) else " "
            dirty = "*" if any(u is ds for u in unsaved) else " "
            self.listbox.insert("end", f"{current}{dirty} {i + 1:>2}. {ds.describe()}")
        target = next((i for i, ds in enumerate(self._shown) if ds is keep), None)
        if target is None and self._shown:
            target = next((i for i, ds in enumerate(self._shown) if store.is_current(ds)), len(self._shown) - 1)
        if target is not None:
            self.listbox.selection_set(target)
            self.listbox.see(target)

    def _selected(self):
        picked = self.listbox.curselection()
        if not picked or picked[0] >= len(self._shown):
            return None
        return self._shown[picked[0]]

    def _use(self) -> None:
        ds = self._selected()
        if ds is not None:
            store.select(ds)

    def _rename(self) -> None:
        ds = self._selected()
        if ds is None:
            return
        name = dialogs.ask_string(self, "Rename dataset", f"New name for '{ds.name or '(unnamed)'}':")
        if name:
            store.rename(ds, name)

    def _save(self) -> None:
        ds = self._selected()
        if ds is None:
            return
        path = dialogs.ask_save_file(self, "Save dataset", session.SAVE_FILETYPES, initialfile=session.suggest_filename(ds))
        if not path:
            return
        try:
            session.save_file(path, ds, whole_workspace=False)
        except Exception as e:
            dialogs.show_error(self, "Save failed", str(e))

    def _remove(self) -> None:
        ds = self._selected()
        if ds is None:
            return
        if any(u is ds for u in store.unsaved()) and not dialogs.ask_yes_no(self, "Remove dataset", "This result has not been saved. Remove it anyway?"):
            return
        store.remove(ds)
