"""
The main window: a data bar (Load / Save / Clear for the shared workspace) above a grid with one cell per tool, grouped by category (and subcategory stacks).

It knows nothing about where the tools come from -- main.py hands it the discovered tool entries (core.discover_tools), clicking a cell calls open_window(root) of that tool, which builds its own window.
"""

import tkinter as tk
from tkinter import ttk

from data import autosave, session, store
from . import dialogs, style
from .widgets import Cell
from .workspace import WorkspaceWindow

GRID_COLUMNS_MAX = style.LAYOUT.grid_columns
AUTOSAVE_INTERVAL_MS = 30_000


class MainWindow:
    def __init__(self, root: tk.Tk, entries: list):
        self.root = root
        self.root.title("mtools")
        self.root.configure(bg=style.COLOR_BG)
        style.apply_style(self.root)

        self.tools = entries
        self._build_data_bar()
        self._build_grid()
        self._size_to_content()

        store.subscribe(self._refresh_io_status)  # tools add results to the workspace too -- the bar must follow, not only Load/Clear
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._workspace_window = None
        self._autosaver = autosave.AutoSaver()
        self._autosave_job = self.root.after(AUTOSAVE_INTERVAL_MS, self._autosave_tick)
        self.root.after(300, self._offer_recovery)  # after the window is up

    def _build_data_bar(self) -> None:
        row = ttk.Frame(self.root, padding=(10, 8))
        row.pack(fill="x")

        cell_height = style.LAYOUT.io_cell_height

        self.input_cell = Cell(row, "Load", self._load, status_text=self._io_status_text(), extra_button=("Workspace", self._open_workspace), height=cell_height)
        self.input_cell.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.output_cell = Cell(row, "Save", self._save, status_text=self._save_status_text(), extra_button=("Clear", self._clear), height=cell_height)
        self.output_cell.pack(side="right", fill="x", expand=True, padx=(12, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=(10, 0))

    def _io_status_text(self) -> str:
        if not store.is_loaded():
            return "no data loaded"
        text = store.get().describe()
        n = len(store.all())
        return f"{text}  [{n} datasets in workspace]" if n > 1 else text

    def _save_status_text(self) -> str:
        unsaved = len(store.unsaved())
        if unsaved:
            return f"{unsaved} unsaved result(s)"
        return session.last_saved_text() or "nothing saved yet"

    def _refresh_io_status(self) -> None:
        self.input_cell.set_status(self._io_status_text())
        self.output_cell.set_status(self._save_status_text())

    def _load(self) -> None:
        path = dialogs.ask_open_file(self.root, "Load data", session.OPEN_FILETYPES)
        if not path:
            return
        try:
            session.load_file(path)
        except Exception as e:
            dialogs.show_error(self.root, "Load failed", str(e))

    def _save(self) -> None:
        if not store.is_loaded():
            dialogs.show_error(self.root, "Nothing to save", "No data currently loaded.")
            return
        path = dialogs.ask_save_file(self.root, "Save data", session.SAVE_FILETYPES, initialfile=session.suggest_filename(store.get()))
        if not path:
            return
        try:
            session.save_file(path, store.get(), whole_workspace=True)  # CSV/TSV: the latest dataset, JSON: the whole workspace
        except Exception as e:
            dialogs.show_error(self.root, "Save failed", str(e))

    def _clear(self) -> None:
        if not store.is_loaded():
            return
        unsaved = len(store.unsaved())
        warning = f"\n\n{unsaved} computed result(s) have not been saved." if unsaved else ""
        if dialogs.ask_yes_no(self.root, title="Clear Data", message=f"Are you sure you want to clear all data?{warning}"):
            store.clear()

    def _open_workspace(self) -> None:
        window = self._workspace_window
        if window is not None and window.winfo_exists():
            window.lift()
            return
        self._workspace_window = WorkspaceWindow(self.root)

    def _autosave_tick(self) -> None:
        try:
            self._autosaver.tick()
        finally:
            self._autosave_job = self.root.after(AUTOSAVE_INTERVAL_MS, self._autosave_tick)  # never let one failed tick stop the timer

    def _offer_recovery(self) -> None:
        info = autosave.pending()
        if info is None:
            return
        when = f" (autosaved {info['saved_at'].replace('T', ' ')})" if info.get("saved_at") else ""
        choice = dialogs.ask_choice(self.root, "Restore previous session", f"The last session ended with {info['n_unsaved']} unsaved result(s){when}, {info['n_datasets']} dataset(s) in total. Restore them?", ["Restore", "Discard"])
        if choice == "Restore":
            try:
                autosave.restore()
            except Exception as e:
                dialogs.show_error(self.root, "Restore failed", str(e))
        elif choice == "Discard":
            autosave.discard()

    def _on_close(self) -> None:
        unsaved = len(store.unsaved())
        if unsaved and not dialogs.ask_yes_no(self.root, title="Quit mtools", message=f"{unsaved} computed result(s) have not been saved and will be lost. Quit anyway?"):
            return
        self.root.after_cancel(self._autosave_job)
        self._autosaver.close()
        store.unsubscribe(self._refresh_io_status)
        self.root.destroy()

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

        direct = [e for e in entries if not e.subcategory]
        subcategories: dict[str, list] = {}
        for e in entries:
            if e.subcategory:
                subcategories.setdefault(e.subcategory, []).append(e)

        expanded: set[str] = set()

        def render() -> None:
            for w in body.winfo_children():
                w.destroy()

            items: list = list(direct)
            for name in sorted(subcategories, key=str.lower):
                items.append(("stack", name, subcategories[name]))
                if name in expanded:
                    items.extend(subcategories[name])

            for i, item in enumerate(items):
                r, c = divmod(i, GRID_COLUMNS_MAX)
                if isinstance(item, tuple):
                    _, name, subcat_entries = item
                    self._build_subcategory_stack(body, r, c, name, subcat_entries, name in expanded, expanded, render)
                else:
                    self._build_cell(body, r, c, item)

        render()
        return row_cursor + 1

    def _build_subcategory_stack(self, parent: ttk.Frame, row: int, col: int, label: str, entries: list, is_expanded: bool, expanded: set, on_toggle) -> None:
        wrapper = ttk.Frame(parent, width=style.CELL_WIDTH, height=style.CELL_HEIGHT)
        wrapper.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        if not is_expanded:
            for i in range(min(len(entries), 3), 0, -1):
                x_off, y_off = i * 10, i * 5
                Cell(wrapper, "").place(relx=0, rely=0, relwidth=1, relheight=1, x=x_off, y=y_off, width=-x_off, height=-y_off)

        def _toggle() -> None:
            if label in expanded:
                expanded.discard(label)
            else:
                expanded.add(label)
            on_toggle()

        arrow = "\u25bc" if is_expanded else "\u25b6"
        hint = "click to collapse" if is_expanded else f"{len(entries)} Tools"
        front = Cell(wrapper, f"{arrow}  {label.replace('_', ' ').title()}\n{hint}", on_click=_toggle)

        if not is_expanded and len(entries) > 0:
            max_i = min(len(entries), 3)
            front.place(relx=0, rely=0, relwidth=1, relheight=1, x=0, y=0, width=-(max_i * 10), height=-(max_i * 5))
        else:
            front.place(relx=0, rely=0, relwidth=1, relheight=1, x=0, y=0, width=0, height=0)

    def _build_cell(self, parent: ttk.Frame, row: int, col: int, entry) -> None:
        cell = Cell(parent, entry.name, lambda e=entry: e.open_window(self.root), status_text=entry.description)
        cell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _size_to_content(self) -> None:
        if not self.tools:
            self.root.geometry(f"{style.LAYOUT.grid_width}x300")
            return

        counts: dict[str, int] = {}
        seen_subcategories: dict[str, set] = {}
        for entry in self.tools:
            if entry.subcategory:
                seen = seen_subcategories.setdefault(entry.category, set())
                if entry.subcategory in seen:
                    continue
                seen.add(entry.subcategory)
            counts[entry.category] = counts.get(entry.category, 0) + 1

        total_cell_rows = sum(-(-n // GRID_COLUMNS_MAX) for n in counts.values())
        width = style.LAYOUT.grid_width
        ideal_height = 90 + style.LAYOUT.io_cell_height + len(counts) * style.LAYOUT.category_header_height + total_cell_rows * (style.CELL_HEIGHT + 12) + 40  # top margin + data bar/separator + category headers + cell rows + bottom margin
        max_height = int(self.root.winfo_screenheight() * style.LAYOUT.max_height_fraction)
        height = min(ideal_height, max_height)
        self.root.geometry(f"{width}x{height}")
