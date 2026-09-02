"""
theme/widgets.py

Reusable building blocks for tool windows, so each tool's gui.py
doesn't have to rebuild the same layout from scratch. Provides
templates for:

- ToolWindow: a themed Toplevel with a title, a description line,
  and a `self.content` frame that subclasses fill with their own
  inputs/outputs/parameters
- FileInputRow: a labeled "browse for input file" row (e.g. a file
  of measurements/points), calls a callback with the chosen path
- OutputPanel: a text area for computed results plus a "Save..."
  button that writes them to a file via a callback
- ComputeToolWindow: the common "load or reuse workspace data, run
  compute(), show/save the result" tool window -- reads/writes the
  shared data.store workspace so tools can be chained
- DataBar: the persistent "Input | Output" bar shown at the top of
  the main window, wired directly to data.store

Extend this file with more shared widgets as new tools need them.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

from data import store
from data.loaders import load_points
from data.savers import save_points_csv

from . import style, dialogs


class ToolWindow(tk.Toplevel):
    """Base window for a tool: themed Toplevel with a title, an
    optional description line, and a `self.content` frame that
    subclasses fill with their own widgets/parameters."""

    def __init__(self, parent, title: str, description: str = "", size: str = "420x360"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        style.apply_style(self)

        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if description:
            ttk.Label(header, text=description, style="Status.TLabel",
                      wraplength=380, justify="left").pack(anchor="w", pady=(4, 0))

        self.content = ttk.Frame(self, padding=10)
        self.content.pack(fill="both", expand=True)


class FileInputRow(ttk.Frame):
    """A labeled row for picking an input file (e.g. measurements or
    points), with a 'Browse...' button. Calls on_file_selected(path)
    whenever a file is chosen. self.path holds the current selection."""

    def __init__(self, parent, label: str = "Input file", on_file_selected=None,
                 filetypes=(("All files", "*.*"),)):
        super().__init__(parent)
        self.on_file_selected = on_file_selected
        self.filetypes = filetypes
        self.path: str | None = None

        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="x")

        self.path_label = ttk.Label(box, text="no file selected", style="Status.TLabel")
        self.path_label.pack(side="left", fill="x", expand=True)

        ttk.Button(box, text="Browse...", command=self._browse).pack(side="right")

    def _browse(self) -> None:
        path = dialogs.ask_open_file(self, title="Select file", filetypes=self.filetypes)
        if not path:
            return
        self.path = path
        self.path_label.config(text=path)
        if self.on_file_selected:
            self.on_file_selected(path)


class OutputPanel(ttk.Frame):
    """A read-only text area for computed results plus a 'Save...'
    button. set_text() updates the shown result; the save button
    opens a save-file dialog and calls on_save(path, text) -- or,
    if no callback is given, writes the text to that path directly."""

    def __init__(self, parent, label: str = "Result", on_save=None,
                 filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
                 default_extension: str = ".txt"):
        super().__init__(parent)
        self.on_save = on_save
        self.filetypes = filetypes
        self.default_extension = default_extension

        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="both", expand=True)

        self.text = tk.Text(box, height=8, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_FG,
                             insertbackground=style.COLOR_FG, relief="flat")
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")

        ttk.Button(box, text="Save...", command=self._save).pack(anchor="e", pady=(8, 0))

    def set_text(self, text: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def _save(self) -> None:
        content = self.get_text()
        if not content.strip():
            dialogs.show_error(self, "Nothing to save", "There's no result to save yet.")
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=self.default_extension, filetypes=self.filetypes
        )
        if not path:
            return
        if self.on_save:
            self.on_save(path, content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


class ComputeToolWindow(ToolWindow):
    """Covers the common case: use the shared workspace data (if
    something is loaded, see data.store) or load a file, compute a
    result from it, show/save the result. Subclass and override
    compute() (and optionally format_result()/save_result()).

    Shows exactly ONE data row at a time -- never a file picker AND a
    "currently loaded" display together:
    - store.is_loaded() -> a status line ("Using loaded data: ...")
      plus a "Load different file..." button
    - nothing loaded -> a FileInputRow; picking a file loads it into
      the shared workspace immediately (so the next tool can reuse it)

    After a successful compute(), "Send result to workspace" becomes
    available -- click it to make this tool's result the input for
    whatever tool you open next (e.g. AFM Geometry -> Analysis).

    Class attributes to override as needed:
        input_label, input_filetypes -- passed to FileInputRow
        output_label -- passed to OutputPanel
    """

    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)
    output_label = "Result"

    def __init__(self, parent, title: str, description: str = ""):
        super().__init__(parent, title=title, description=description)
        self._last_result = None

        self._data_row = ttk.Frame(self.content)
        self._data_row.pack(fill="x", pady=(0, 8))
        self._render_data_row()

        self.output = OutputPanel(self.content, label=self.output_label, on_save=self.save_result)
        self.output.pack(fill="both", expand=True, pady=(0, 8))

        btn_row = ttk.Frame(self.content)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Compute", style="Accent.TButton", command=self.run).pack(side="right")
        self._send_button = ttk.Button(btn_row, text="Send result to workspace", command=self._send_to_workspace)
        self._send_button.pack(side="right", padx=(0, 6))
        self._send_button.configure(state="disabled")

    # -- data row: loaded status OR file picker, never both --------

    def _render_data_row(self) -> None:
        for w in self._data_row.winfo_children():
            w.destroy()

        if store.is_loaded():
            box = ttk.LabelFrame(self._data_row, text="Data", padding=10)
            box.pack(fill="x")
            ttk.Label(box, text=f"Using loaded data: {store.label()}", style="Status.TLabel").pack(
                side="left", fill="x", expand=True
            )
            ttk.Button(box, text="Load different file...", command=self._browse).pack(side="right")
        else:
            row = FileInputRow(self._data_row, label=self.input_label,
                                filetypes=self.input_filetypes, on_file_selected=self._on_file_chosen)
            row.pack(fill="x")

    def _browse(self) -> None:
        path = dialogs.ask_open_file(self, title="Select file", filetypes=self.input_filetypes)
        if path:
            self._on_file_chosen(path)

    def _on_file_chosen(self, path: str) -> None:
        try:
            data = load_points(path)
        except Exception as e:
            dialogs.show_error(self, "Load failed", str(e))
            return
        store.set(data, Path(path).name)
        self._render_data_row()

    # -- compute / result -------------------------------------------

    def compute(self, data):
        """Override: turn the workspace data into a result (any type
        -- format_result() below turns it into display text)."""
        raise NotImplementedError

    def format_result(self, result) -> str:
        """Override if the result needs custom formatting. Default:
        plain str(result)."""
        return str(result)

    def save_result(self, path: str, content: str) -> None:
        """Override for a custom save format (e.g. CSV instead of
        plain text). Default: write the displayed text as-is."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def run(self) -> None:
        if not store.is_loaded():
            dialogs.show_error(self, "No data", "Please load a file first.")
            return
        try:
            result = self.compute(store.get())
        except Exception as e:
            dialogs.show_error(self, "Computation failed", str(e))
            return
        self._last_result = result
        self._send_button.configure(state="normal")
        self.output.set_text(self.format_result(result))

    def _send_to_workspace(self) -> None:
        if self._last_result is None:
            return
        store.set(self._last_result, f"Output of {self.title()}")
        self._render_data_row()


class DataBar(ttk.Frame):
    """Persistent 'Input | Output' bar for the main window. Lets the
    user load data into the shared workspace (data.store) once and
    export/clear it -- separate from any individual tool, so tools
    can be chained without a file round-trip in between."""

    def __init__(self, parent, filetypes=(("CSV/text files", "*.csv;*.txt;*.dat"), ("All files", "*.*"))):
        super().__init__(parent, padding=(10, 8))
        self.filetypes = filetypes

        row = ttk.Frame(self)
        row.pack(fill="x")

        in_box = ttk.LabelFrame(row, text="Input", padding=8)
        in_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(in_box, text="Load...", command=self._load).pack(side="right")

        out_box = ttk.LabelFrame(row, text="Output", padding=8)
        out_box.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Button(out_box, text="Clear", command=self._clear).pack(side="right")
        ttk.Button(out_box, text="Save...", command=self._save).pack(side="right", padx=(0, 6))

        self.status_label = ttk.Label(self, style="Status.TLabel")
        self.status_label.pack(fill="x", pady=(6, 0))

        self._refresh()

    def _load(self) -> None:
        path = dialogs.ask_open_file(self, title="Load data", filetypes=self.filetypes)
        if not path:
            return
        try:
            data = load_points(path)
        except Exception as e:
            dialogs.show_error(self, "Load failed", str(e))
            return
        store.set(data, Path(path).name)
        self._refresh()

    def _save(self) -> None:
        if not store.is_loaded():
            dialogs.show_error(self, "Nothing to save", "No data currently loaded.")
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        save_points_csv(path, store.get())

    def _clear(self) -> None:
        store.clear()
        self._refresh()

    def _refresh(self) -> None:
        if store.is_loaded():
            data = store.get()
            n = len(data) if hasattr(data, "__len__") else "?"
            self.status_label.configure(text=f"Loaded: {store.label()} ({n} row(s))")
        else:
            self.status_label.configure(text="No data loaded")
