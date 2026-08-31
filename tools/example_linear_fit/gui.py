"""
2nd window for 'Linear Regression'. Meant as a template for further tools: file input, run button, output -- same theme as the main window.
"""

import tkinter as tk
from tkinter import ttk

from theme import style, dialogs
from .regression import fit_from_csv


class ToolWindow(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Linear Regression")
        self.geometry("420x320")
        style.apply_style(self)

        self.file_path: str | None = None

        self._build_file_row()
        self._build_output()
        self._build_run_row()

    def _build_file_row(self) -> None:
        row = ttk.LabelFrame(self, text="Input file", padding=10)
        row.pack(fill="x", padx=10, pady=(10, 5))

        self.file_label = ttk.Label(row, text="no file selected", style="Status.TLabel")
        self.file_label.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text="Browse...", command=self.choose_file).pack(side="right")

    def _build_output(self) -> None:
        frame = ttk.LabelFrame(self, text="Result", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.output = tk.Text(frame, height=8, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_FG, insertbackground=style.COLOR_FG, relief="flat")
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="disabled")

    def _build_run_row(self) -> None:
        row = ttk.Frame(self, padding=10)
        row.pack(fill="x")
        ttk.Button(row, text="Compute", style="Accent.TButton", command=self.run_fit).pack(side="right")

    def choose_file(self) -> None:
        path = dialogs.ask_open_file(
            self, title="Select CSV with x,y values",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if path:
            self.file_path = path
            self.file_label.config(text=path)

    def run_fit(self) -> None:
        if not self.file_path:
            dialogs.show_error(self, "No file", "Please select a CSV file first.")
            return
        try:
            result = fit_from_csv(self.file_path)
        except Exception as e:
            dialogs.show_error(self, "Computation failed", str(e))
            return

        text = (
            f"n = {result['n']}\n"
            f"a (slope) = {result['a']:.6g}\n"
            f"b (intercept) = {result['b']:.6g}\n"
            f"R^2 = {result['r_squared']:.6g}\n"
        )
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")
