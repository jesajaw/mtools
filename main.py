"""
Reads the tools/ package at startup (core.registry.discover_tools) and dynamically builds a selection grid, one cell per discovered tool. Clicking a tile calls open_window(root) on the corresponding tool module, which builds its own 2nd window (Toplevel).

To add a new tool: create a new folder under tools/ with an __init__.py (TOOL_NAME, TOOL_DESCRIPTION, open_window) -- main.py does not need to be touched.
"""

import sys
from pathlib import Path
from tkinter import filedialog

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk
from tkinter import ttk

import tools
from core import discover_tools

from data import loaders, savers, store
from theme import style, dialogs
from theme.widgets import Cell

GRID_COLUMNS_MAX = style.LAYOUT.grid_columns


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("mtools")
        self.root.configure(bg=style.COLOR_BG)
        style.apply_style(self.root)

        self.tools = discover_tools(tools)
        self._build_data_bar()
        self._build_grid()
        self._size_to_content()

    def _build_data_bar(self) -> None:
        row = ttk.Frame(self.root, padding=(10, 8))
        row.pack(fill="x")

        cell_width = style.LAYOUT.grid_width / 2
        cell_height = style.LAYOUT.io_cell_height

        self.input_cell = Cell(row, "Load", self._load, status_text=self._io_status_text(), width=cell_width, height=cell_height)
        self.input_cell.pack(side="left", padx=(0, 12))

        output_cell = Cell(row, "Save", self._save, extra_button=("Clear", self._clear), width=cell_width, height=cell_height)
        output_cell.pack(side="right", padx=(12, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=(10, 0))

    def _io_status_text(self) -> str:
        if not store.is_loaded():
            return "no data loaded"
        data = store.get()
        n = len(data) if hasattr(data, "__len__") else "?"
        return f"{store.label()} ({n} row(s))"

    def _load(self) -> None:
        path = dialogs.ask_open_file(self.root, title="Load data", filetypes=(("CSV/text files", "*.csv;*.txt;*.dat"), ("All files", "*.*")))
        if not path:
            return
        try:
            data = loaders.load_points(path)
        except Exception as e:
            dialogs.show_error(self.root, "Load failed", str(e))
            return
        store.set(data, Path(path).name)
        self.input_cell.set_status(self._io_status_text())

    def _save(self) -> None:
        if not store.is_loaded():
            dialogs.show_error(self.root, "Nothing to save", "No data currently loaded.")
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not path:
            return
        savers.save_points_csv(path, store.get())

    def _clear(self) -> None:
        if dialogs.ask_yes_no(self.root, title="Clear Data", message="Are you sure you want to clear all data?"):
            store.clear()
            self.input_cell.set_status(self._io_status_text())

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
        header.grid(row=row_cursor, column=0, columnspan=GRID_COLUMNS_MAX, sticky="w", pady=(12 if row_cursor else 0, 6))
        row_cursor += 1

        body = ttk.Frame(container)
        body.grid(row=row_cursor, column=0, columnspan=GRID_COLUMNS_MAX, sticky="nsew")
        for col in range(GRID_COLUMNS_MAX):
            body.columnconfigure(col, weight=1)

        expanded: set[str] = set()

        def render() -> None:
            for w in body.winfo_children():
                w.destroy()

            direct = [e for e in entries if not e.subcategory]
            subcategories: dict[str, list] = {}
            for e in entries:
                if e.subcategory:
                    subcategories.setdefault(e.subcategory, []).append(e)

            items: list = list(direct)
            for name in sorted(subcategories, key=str.lower):
                if name in expanded:
                    items.extend(subcategories[name])  # unfolded -- now just normal tools
                else:
                    items.append((name, subcategories[name]))  # still a collapsed stack

            for i, item in enumerate(items):
                r, c = divmod(i, GRID_COLUMNS_MAX)
                if isinstance(item, tuple):
                    self._build_subcategory_stack(body, r, c, item[0], item[1], expanded, render)
                else:
                    self._build_cell(body, r, c, item)

        render()
        row_cursor += -(-len(entries) // GRID_COLUMNS_MAX) if entries else 0
        return row_cursor

    def _build_subcategory_stack(self, parent: ttk.Frame, row: int, col: int, label: str, entries: list, expanded: set, on_toggle) -> None:
        """A stack-of-cards tile standing in for a collapsed
        subcategory -- one normal grid slot, styled to look like 2-3
        Cells layered behind the front one. Clicking it expands in
        place: the stack disappears and its tools appear as regular
        cells right where it was (on_toggle re-renders the whole
        category body, since adding N tools shifts everything after
        this position)."""
        wrapper = ttk.Frame(parent, width=style.CELL_WIDTH, height=style.CELL_HEIGHT)
        wrapper.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        wrapper.grid_propagate(False)

        for offset in (10, 5):
            ttk.Frame(wrapper, style="Cell.TFrame", width=style.CELL_WIDTH, height=style.CELL_HEIGHT).place(x=offset, y=offset)

        def _expand() -> None:
            expanded.add(label)
            on_toggle()

        display_name = label.replace("_", " ").title()
        front = Cell(wrapper, f"{display_name} ({len(entries)})", on_click=_expand, width=style.CELL_WIDTH, height=style.CELL_HEIGHT)
        front.place(x=0, y=0)

    def _build_cell(self, parent: ttk.Frame, row: int, col: int, entry) -> None:
        cell = Cell(parent, entry.name, lambda e=entry: e.open_window(self.root), status_text=entry.description)
        cell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _size_to_content(self) -> None:
        if not self.tools:
            self.root.geometry(f"{style.LAYOUT.grid_width}x300")
            return

        counts: dict[str, int] = {}
        for entry in self.tools:
            counts[entry.category] = counts.get(entry.category, 0) + 1

        total_cell_rows = sum(-(-n // GRID_COLUMNS_MAX) for n in counts.values())
        width = style.LAYOUT.grid_width
        ideal_height = 90 + 70 + len(counts) * style.LAYOUT.category_header_height + total_cell_rows * (style.CELL_HEIGHT + 12) + 40  # top margin + data bar/separator + category headers + cell rows + bottom margin
        max_height = int(self.root.winfo_screenheight() * style.LAYOUT.max_height_fraction)
        height = min(ideal_height, max_height)
        self.root.geometry(f"{width}x{height}")


def main() -> None:
    style.enable_dpi_awareness()
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
