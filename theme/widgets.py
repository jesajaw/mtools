"""
Reusable building blocks for tool windows, so each tool's gui.py doesn't have to rebuild the same layout from scratch. Provides templates for:
- ToolWindow: a themed Toplevel with a title, a description line and a `self.content` frame that subclasses fill with their own inputs/outputs/parameters
- FileInputRow: a labeled "browse for input file" row (e.g. a file of measurements/points), calls a callback with the chosen path
- OutputPanel: a text area for computed results plus a "Save..." button that writes them to a file via a callback

Extend this file with more shared widgets as new tools need them.
"""

import tkinter as tk
from tkinter import ttk, filedialog

from . import style, dialogs


class ToolWindow(tk.Toplevel):
    # Base window for a tool: themed Toplevel with a title, an optional description line, and a `self.content` frame that subclasses fill with their own widgets/parameters.

    def __init__(self, parent, title: str, description: str = "", size: str = "420x360"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        style.apply_style(self)

        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if description:
            ttk.Label(header, text=description, style="Status.TLabel", wraplength=380, justify="left").pack(anchor="w", pady=(4, 0))

        self.content = ttk.Frame(self, padding=10)
        self.content.pack(fill="both", expand=True)


class FileInputRow(ttk.Frame):
    # A labeled row for picking an input file (e.g. measurements or points), with a 'Browse...' button. Calls on_file_selected(path) whenever a file is chosen. self.path holds the current selection.

    def __init__(self, parent, label: str = "Input file", on_file_selected=None, filetypes=(("All files", "*.*"),)):
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
    # A read-only text area for computed results plus a 'Save...' button. set_text() updates the shown result; the save button opens a save-file dialog and calls on_save(path, text) -- or, if no callback is given, writes the text to that path directly.

    def __init__(self, parent, label: str = "Result", on_save=None, filetypes=(("Text files", "*.txt"), ("All files", "*.*")), default_extension: str = ".txt"):
        super().__init__(parent)
        self.on_save = on_save
        self.filetypes = filetypes
        self.default_extension = default_extension

        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="both", expand=True)

        self.text = tk.Text(box, height=8, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_FG, insertbackground=style.COLOR_FG, relief="flat")
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
    """Covers the common case: pick a file, compute a result from it,
    show/save the result. Subclass and override compute() (and
    optionally format_result()/save_result()) -- no need to hand-wire
    FileInputRow/OutputPanel/Compute-button/run() again per tool.

    Class attributes to override as needed:
        input_label, input_filetypes -- passed to FileInputRow
        output_label -- passed to OutputPanel
    """

    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)
    output_label = "Result"

    def __init__(self, parent, title: str, description: str = ""):
        super().__init__(parent, title=title, description=description)

        self.file_input = FileInputRow(
            self.content, label=self.input_label, filetypes=self.input_filetypes,
        )
        self.file_input.pack(fill="x", pady=(0, 8))

        self.output = OutputPanel(self.content, label=self.output_label, on_save=self.save_result)
        self.output.pack(fill="both", expand=True, pady=(0, 8))

        ttk.Button(self.content, text="Compute", style="Accent.TButton",
                   command=self.run).pack(anchor="e")

    def compute(self, path: str):
        raise NotImplementedError

    def format_result(self, result) -> str:
        return str(result)

    def save_result(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def run(self) -> None:
        if not self.file_input.path:
            dialogs.show_error(self, "No file", "Please select a file first.")
            return
        try:
            result = self.compute(self.file_input.path)
        except Exception as e:
            dialogs.show_error(self, "Computation failed", str(e))
            return
        self.output.set_text(self.format_result(result))