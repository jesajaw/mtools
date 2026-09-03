"""
Reads the tools/ package at startup (core.registry.discover_tools) and dynamically builds a selection grid, one cell per discovered tool. Clicking a tile calls open_window(root) on the corresponding tool module, which builds its own 2nd window (Toplevel).

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

from theme.widgets import Cell, DataBar

GRID_COLUMNS_MAX = 3


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mtools")
        self.root.configure(bg=style.COLOR_BG)
        style.apply_style(self.root)

        self.tools = discover_tools(tools)
        self._build_header()
        self._build_data_bar()
        self._build_grid()
        self._size_to_content()

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Select a tool", font=("Segoe UI", 12, "bold")).pack(anchor="w")

    def _build_data_bar(self) -> None:
        DataBar(self.root).pack(fill="x", padx=10)
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=(10, 0))

    def _build_grid(self) -> None:
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        canvas = tk.Canvas(outer, bg=style.COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        container = ttk.Frame(canvas, padding=10)
        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        def _sync_scrollregion(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_container_width(event) -> None:
            canvas.itemconfig(canvas_window, width=event.width)

        container.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_container_width)

        def _on_mousewheel(event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        if not self.tools:
            ttk.Label(container, text="No tools found under tools/.").pack(anchor="w")
            return

        for col in range(GRID_COLUMNS_MAX):
            container.columnconfigure(col, weight=1)
        
        row_cursor = 0

        grouped: dict[str, list] = {}
        for entry in self.tools:
            grouped.setdefault(entry.category, []).append(entry)

        for category in sorted(grouped, key=str.lower):
            row_cursor = self._build_category_block(container, row_cursor, category.replace("_", " ").upper(), grouped[category])

    def _build_category_block(self, container: ttk.Frame, row_cursor: int, label: str, entries: list) -> int:
        header = ttk.Label(container, text=label, style="CategoryHeader.TLabel")
        header.grid(row=row_cursor, column=0, columnspan=GRID_COLUMNS_MAX,
                    sticky="w", pady=(12 if row_cursor else 0, 6))
        row_cursor += 1

        for i, entry in enumerate(entries):
            r, c = divmod(i, GRID_COLUMNS_MAX)
            self._build_cell(container, row_cursor + r, c, entry)
        row_cursor += -(-len(entries) // GRID_COLUMNS_MAX)  # ceil division
        return row_cursor

    def _build_cell(self, parent: ttk.Frame, row: int, col: int, entry) -> None:
        cell = Cell(parent, entry.name, lambda e=entry: e.open_window(self.root),
                    status_text=entry.description)
        cell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _make_cell_clickable(self, cell: ttk.Frame, title: ttk.Label, desc: ttk.Label, entry) -> None:
        widgets = (cell, title, desc)

        def _open(_event=None) -> None:
            entry.open_window(self.root)

        def _on_enter(_event=None) -> None:
            cell.configure(style="CellHover.TFrame")
            title.configure(style="CellTitleHover.TLabel")
            desc.configure(style="StatusHover.TLabel")

        def _on_leave(_event=None) -> None:
            cell.configure(style="Cell.TFrame")
            title.configure(style="CellTitle.TLabel")
            desc.configure(style="Status.TLabel")

        for w in widgets:
            w.configure(cursor="hand2")
            w.bind("<Button-1>", _open)
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)

    def _size_to_content(self) -> None:
        if not self.tools:
            self.root.geometry(f"{GRID_COLUMNS_MAX * (style.CELL_WIDTH + 12) + 40}x300")
            return

        counts: dict[str, int] = {}
        for entry in self.tools:
            counts[entry.category] = counts.get(entry.category, 0) + 1

        header_height = 34
        total_cell_rows = sum(-(-n // GRID_COLUMNS_MAX) for n in counts.values())
        width = GRID_COLUMNS_MAX * (style.CELL_WIDTH + 12) + 40
        ideal_height = (
            90
            + 70  # data bar + separator
            + len(counts) * header_height
            + total_cell_rows * (style.CELL_HEIGHT + 12)
            + 40
        )
        max_height = int(self.root.winfo_screenheight() * 0.8)
        height = min(ideal_height, max_height)
        self.root.geometry(f"{width}x{height}")


def main() -> None:
    style.enable_dpi_awareness()
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
