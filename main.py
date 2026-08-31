"""
Reads the tools/ package at startup (core.registry.discover_tools) and dynamically builds a selection grid, one cell per discovered tool. Clicking "Open" calls open_window(root) on the corresponding tool module, which builds its own 2nd window (Toplevel).

To add a new tool: create a new folder under tools/ with an __init__.py (TOOL_NAME, TOOL_DESCRIPTION, open_window) -- main.py does not need to be touched.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk
from tkinter import ttk

import tools
from core import discover_tools
from theme import style

GRID_COLUMNS_MAX = 3


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mtools")
        self.root.configure(bg=style.COLOR_BG)
        style.apply_style(self.root)

        self.tools = discover_tools(tools)
        self._build_header()
        self._build_grid()
        self._size_to_content()

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

        columns = min(GRID_COLUMNS_MAX, len(self.tools))
        for col in range(columns):
            container.columnconfigure(col, weight=1)

        for i, entry in enumerate(self.tools):
            row, col = divmod(i, columns)
            self._build_cell(container, row, col, entry)

    def _build_cell(self, parent: ttk.Frame, row: int, col: int, entry) -> None:
        cell = ttk.Frame(parent, padding=8, relief="groove", style="Cell.TFrame")
        cell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        cell.pack_propagate(False)
        cell.configure(width=style.CELL_WIDTH, height=style.CELL_HEIGHT)

        ttk.Label(cell, text=entry.name, style="CellTitle.TLabel").pack(anchor="w")
        ttk.Label(cell, text=entry.description, style="Status.TLabel", wraplength=style.CELL_WIDTH - 20, justify="left").pack(anchor="w", pady=(4, 8), fill="x")
        ttk.Button(cell, text="Open", style="Accent.TButton", command=lambda e=entry: e.open_window(self.root)).pack(anchor="e")
        
    def _size_to_content(self) -> None:
        count = len(self.tools) or 1
        columns = min(GRID_COLUMNS_MAX, count)
        rows = -(-count // columns)  # ceil division
        width = columns * (style.CELL_WIDTH + 12) + 40
        height = 70 + rows * (style.CELL_HEIGHT + 12) + 40
        self.root.geometry(f"{width}x{height}")

def main() -> None:
    style.enable_dpi_awareness()
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
