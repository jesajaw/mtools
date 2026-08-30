"""
mtools - main window

Reads the tools/ package at startup (core.registry.discover_tools)
and dynamically builds a selection grid, one cell per discovered
tool -- analogous to the channel grid in the DMX reference script.
Clicking "Open" calls open_window(root) on the corresponding tool
module, which builds its own 2nd window (Toplevel).

To add a new tool: create a new folder under tools/ with an
__init__.py (TOOL_NAME, TOOL_DESCRIPTION, open_window) -- main.py
does not need to be touched.
"""

import tkinter as tk
from tkinter import ttk

import tools
from core.registry import discover_tools
from theme import style

GRID_COLUMNS = 3


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mtools")
        self.root.configure(bg=style.COLOR_BG)
        style.apply_style(self.root)

        self.tools = discover_tools(tools)
        self._build_header()
        self._build_grid()

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Select a tool", font=("Segoe UI", 12, "bold")).pack(anchor="w")

    def _build_grid(self) -> None:
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)

        if not self.tools:
            ttk.Label(container, text="No tools found under tools/.").pack(anchor="w")
            return

        for col in range(GRID_COLUMNS):
            container.columnconfigure(col, weight=1)

        for i, entry in enumerate(self.tools):
            row, col = divmod(i, GRID_COLUMNS)
            self._build_cell(container, row, col, entry)

    def _build_cell(self, parent: ttk.Frame, row: int, col: int, entry) -> None:
        cell = ttk.Frame(parent, padding=8, relief="groove", style="Cell.TFrame")
        cell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        cell.pack_propagate(False)
        cell.configure(width=style.CELL_WIDTH, height=style.CELL_HEIGHT)

        ttk.Label(cell, text=entry.name, style="CellTitle.TLabel").pack(anchor="w")
        ttk.Label(cell, text=entry.description, style="Status.TLabel",
                  wraplength=style.CELL_WIDTH - 20, justify="left").pack(
            anchor="w", pady=(4, 8), fill="x"
        )
        ttk.Button(cell, text="Open", style="Accent.TButton",
                   command=lambda e=entry: e.open_window(self.root)).pack(anchor="e")


def main() -> None:
    root = tk.Tk()
    root.geometry("850x600")
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
