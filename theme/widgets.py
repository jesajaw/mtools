"""
theme/widgets.py

Reusable building blocks for tool windows, so each tool's gui.py
doesn't have to rebuild the same layout from scratch. Provides
templates for:

- ToolWindow: a themed Toplevel with a title, a description line,
  and a `self.content` frame that subclasses fill with their own
  inputs/outputs/parameters
- OutputPanel: a text area for computed results plus a "Save..."
  button that writes them to a file via a callback
- ComputeToolWindow: the common "load or reuse workspace data, run
  compute(), show/save the result" tool window -- reads/writes the
  shared data.store workspace so tools can be chained
- Cell: a clickable tile (title, optional status line, hover
  highlight) -- the one building block every cell in the app is
  made from, whether that's a tool in the main window's grid or
  Load/Save in DataBar
- DataBar: the persistent "Input | Output" bar shown at the top of
  the main window, built from two Cells, wired directly to data.store

Extend this file with more shared widgets as new tools need them.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

from data import store
from data.loaders import load_points
from data.savers import save_points_csv

from . import style, dialogs


class Cell(ttk.Frame):
    """A clickable tile: title, optional description/status line,
    hover highlight -- the one class every cell in the app is built
    from, whether that's a tool in the main grid (main.py's
    _build_cell) or Load/Save in DataBar below.

    status_text is the description line. Leave it out (None, the
    default) for a cell that never shows one -- no status_label is
    even created then, so set_status() is a no-op for that cell.
    extra_button is an optional (text, command) pair rendered as a
    small button in the cell's corner -- its own widget, so it
    doesn't also trigger the cell's on_click (used for 'Clear' on
    the Save cell: a rarer, secondary action that shouldn't be one
    accidental cell-click away from Save)."""

    def __init__(self, parent, title: str, on_click, status_text: str | None = None,
                 wraplength: int = style.CELL_WIDTH - 20, extra_button=None):
        super().__init__(parent, padding=8, relief="groove", style="Cell.TFrame")
        self.on_click = on_click
        self.pack_propagate(False)
        self.configure(width=style.CELL_WIDTH, height=style.CELL_HEIGHT)

        self.title_label = ttk.Label(self, text=title, style="CellTitle.TLabel")
        self.title_label.pack(anchor="w")

        self.status_label = None
        clickable = [self, self.title_label]
        if status_text is not None:
            self.status_label = ttk.Label(self, text=status_text, style="Status.TLabel",
                                           wraplength=wraplength, justify="left")
            self.status_label.pack(anchor="w", pady=(4, 8), fill="x")
            clickable.append(self.status_label)

        for w in clickable:
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if extra_button:
            text, command = extra_button
            ttk.Button(self, text=text, command=command).pack(anchor="e")

    def set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text)

    def _on_click(self, _event=None) -> None:
        self.on_click()

    def _on_enter(self, _event=None) -> None:
        self.configure(style="CellHover.TFrame")
        self.title_label.configure(style="CellTitleHover.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="StatusHover.TLabel")

    def _on_leave(self, _event=None) -> None:
        self.configure(style="Cell.TFrame")
        self.title_label.configure(style="CellTitle.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="Status.TLabel")


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


class ToolWindow(tk.Toplevel):
    """Base window for a tool: themed Toplevel with a title, an
    optional description line, and a `self.content` frame that
    subclasses fill with their own widgets/parameters."""

    def __init__(self, parent, title: str, description: str = "", size: str = "420x360"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.minsize(340, 300)
        style.apply_style(self)

        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if description:
            ttk.Label(header, text=description, style="Status.TLabel",
                      wraplength=380, justify="left").pack(anchor="w", pady=(4, 0))

        self.content = ttk.Frame(self, padding=10)
        self.content.pack(fill="both", expand=True)
        

class ComputeToolWindow(ToolWindow):
    """Covers the common case: take the shared workspace data (see
    data.store), compute a result from it, show/save the result.
    Subclass and override compute() (and optionally
    format_result()/save_result()).

    Loading data (file or manual entry) happens only in the main
    window's I/O bar (see DataBar below) -- this window just shows
    whether something is loaded and, once computed, the result.

    After a successful compute(), "Send result to workspace" becomes
    available -- click it to make this tool's result the input for
    whatever tool you open next (e.g. AFM Geometry -> Analysis).

    Class attributes to override as needed:
        output_label -- passed to OutputPanel
    """

    output_label = "Result"
    default_size = "420x360"

    def __init__(self, parent, title: str, description: str = "", size: str | None = None):
        super().__init__(parent, title=title, description=description, size=size or self.default_size)
        self._last_result = None

        self._build_extra(self.content)

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

    # -- data row: read-only status, no browsing/manual entry here --

    def _render_data_row(self) -> None:
        for w in self._data_row.winfo_children():
            w.destroy()

        box = ttk.LabelFrame(self._data_row, text="Data", padding=10)
        box.pack(fill="x")
        if store.is_loaded():
            text = f"Using loaded data: {store.label()}"
        else:
            text = "No data loaded -- load data via the main window."
        ttk.Label(box, text=text, style="Status.TLabel").pack(anchor="w", fill="x")

    # -- extension point ---------------------------------------------

    def _build_extra(self, parent) -> None:
        """Override to insert tool-specific widgets (e.g. the model
        formula / parameter fields the custom non-linear fit needs)
        between the description and the shared data row. No-op by
        default -- most tools don't need anything here."""
        pass

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
            dialogs.show_error(self, "No data", "Please load data via the main window first.")
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
    """Persistent 'Input | Output' bar for the main window, built
    from two Cells (see Cell above) so it looks like part of the
    tool grid rather than a separate toolbar -- input stays visually
    separate from output, just two cells, same as before. Only the
    Load cell ever shows a status line (the loaded file name); Save
    doesn't have one anywhere. Lets the user load data into the
    shared workspace (data.store) once and export/clear it --
    separate from any individual tool, so tools can be chained
    without a file round-trip in between."""

    def __init__(self, parent, filetypes=(("CSV/text files", "*.csv;*.txt;*.dat"), ("All files", "*.*"))):
        super().__init__(parent, padding=(10, 8))
        self.filetypes = filetypes

        row = ttk.Frame(self)
        row.pack(fill="x")

        self.input_cell = Cell(row, "Load", self._load, status_text=self._status_text())
        self.input_cell.pack(side="left", padx=(0, 12))

        self.output_cell = Cell(row, "Save", self._save, extra_button=("Clear", self._clear))
        self.output_cell.pack(side="right", padx=(12, 0))

    def _status_text(self) -> str:
        if not store.is_loaded():
            return "no data loaded"
        data = store.get()
        n = len(data) if hasattr(data, "__len__") else "?"
        return f"{store.label()} ({n} row(s))"

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
        self.input_cell.set_status(self._status_text())