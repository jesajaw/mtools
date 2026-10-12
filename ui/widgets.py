"""
Reusable building blocks for tool windows, so each tool's ui doesn't have to rebuild the same layout from scratch. Provides templates for:
- Cell: a clickable tile (title, optional status line, hover highlight) -- the one building block every cell in the app is made from: tools in the main window's grid, Load/Save there too and the read-only "Data" status cell in every ToolWindow
- ToolWindow: a themed Toplevel with a title, a description line, and a `self.content` frame that subclasses fill with their own inputs/outputs/parameters
- OutputPanel: a text area for computed results plus a "Save..." button that writes them to a file via a callback
- ParameterBox: a labelled group of entry fields for tool parameters (alpha, window size, distribution parameters, ...), with get()/set()/set_label()/set_enabled()
- ComputeToolWindow: the common "load or reuse workspace data, run compute(), show/save the result" tool window -- reads/writes the shared data.store workspace so tools can be chained
"""

import tkinter as tk
from tkinter import ttk
from data import store, savers, results
from . import style, dialogs
from data.dataset import DataSet

class Cell(ttk.Frame):
    """
    A clickable tile: title, optional description/status line, hover highlight
    optional:
    - status_text is the description line: Leave it out (None, the default) for a cell that never shows one
    - on_click: leave it out for a plain, inert status tile (no hover, no click cursor, nothing bound)
    - extra_button: render an extra button (text, command) in the cell's corner
    """
    def __init__(self, parent, title: str, on_click=None, status_text: str | None = None, width: int = style.CELL_WIDTH, height: int = style.CELL_HEIGHT, extra_button=None):
        super().__init__(parent, padding=8, relief="groove", style="Cell.TFrame")
        wraplength = width - 20
        self.on_click = on_click
        self.pack_propagate(False)
        self.configure(width=width, height=height)

        self.title_label = ttk.Label(self, text=title, style="CellTitle.TLabel")
        self.title_label.pack(anchor="w")

        self.status_label = None
        clickable = [self, self.title_label]
        if status_text is not None:
            self.status_label = ttk.Label(self, text=status_text, style="Status.TLabel", wraplength=wraplength, justify="left")
            self.status_label.pack(anchor="w", pady=(4, 8), fill="x")
            clickable.append(self.status_label)

        if on_click is not None:
            for w in clickable:
                w.configure(cursor="hand2")
                w.bind("<Button-1>", self._on_click)
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)

        if extra_button:
            text, command = extra_button
            ttk.Button(self, text=text, command=command).pack(anchor="e")

        self.bind("<Configure>", self._on_resize)

    def set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text)

    def _on_click(self, _event=None) -> None:
        if self.on_click:
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

    def _on_resize(self, event) -> None:
        # Keep text reflowing with the cell's actual rendered width, not just its initial size.
        wrap = max(event.width - 20, 20)
        self.title_label.configure(wraplength=wrap)
        if self.status_label is not None:
            self.status_label.configure(wraplength=wrap)


class ToolWindow(tk.Toplevel):
    # Base window for a tool: themed Toplevel, title in the OS titlebar -- subclasses fill `self.content` with their own widgets/parameters.
    def __init__(self, parent, title: str, size: str = "420x360"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.minsize(340, 300)
        style.apply_style(self)

        self.content = ttk.Frame(self, padding=10)
        self.content.pack(fill="both", expand=True)


class ResultDisplay(ttk.Frame):
    """
    Compact, read-only result display: one label plus a 'Copy to clipboard' button -- no big text box, no file-save, since most results here are short (a fitted formula, a handful of parameter values), not something that needs a scrollable editor-like area.
    set_text() updates what's shown; initial_text is what's shown before the first compute() (e.g. a tool's RESULT_FORMAT dummy, like "y = a*x^n + b*x^2 + ... + c").

    Tables (statistics results with one column per data column, see data.results.summarize) need aligned columns and can be long, so set_text(text, monospace=True) switches to a monospace text area instead: it grows with the text up to MAX_LINES lines and then scrolls (scrollbars only appear when needed). "Copy" always copies the complete text.
    """

    MAX_LINES = 14
    MAX_CHARS = 64

    def __init__(self, parent, label: str = "Result", initial_text: str = ""):
        super().__init__(parent)
        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="x")
        self._box = box
        self._text = initial_text

        ttk.Button(box, text="\u29c9", style="Icon.TButton", command=self._copy).pack(anchor="e")
        self.value_label = ttk.Label(box, text=initial_text, style="ResultText.TLabel", wraplength=200, justify="center", anchor="center")
        self.value_label.pack(fill="x", pady=(0, 8))

        self._table = ttk.Frame(box)  # monospace mode, packed on demand
        self._table.columnconfigure(0, weight=1)
        self.text_area = tk.Text(self._table, height=1, width=30, wrap="none", relief="flat", borderwidth=0, highlightthickness=0, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_STATUS_TEXT, font=style.FONT_MONO_NORMAL, insertwidth=0, cursor="arrow", takefocus=0, padx=8, pady=6)
        self._vbar = ttk.Scrollbar(self._table, orient="vertical", command=self.text_area.yview)
        self._hbar = ttk.Scrollbar(self._table, orient="horizontal", command=self.text_area.xview)
        self.text_area.configure(yscrollcommand=lambda first, last: self._autoscroll(self._vbar, first, last), xscrollcommand=lambda first, last: self._autoscroll(self._hbar, first, last))
        self.text_area.grid(row=0, column=0, sticky="nsew")
        self._vbar.grid(row=0, column=1, sticky="ns")
        self._hbar.grid(row=1, column=0, sticky="ew")

    @staticmethod
    def _autoscroll(bar, first, last) -> None:
        # a scrollbar that only shows up when the content doesn't fit
        if float(first) <= 0.0 and float(last) >= 1.0:
            bar.grid_remove()
        else:
            bar.grid()
        bar.set(first, last)

    def set_text(self, text: str, monospace: bool = False) -> None:
        self._text = text
        if not monospace:
            self._table.pack_forget()
            self.value_label.configure(text=text)
            self.value_label.pack(fill="x", pady=(0, 8))
            return

        lines = text.rstrip("\n").split("\n")
        self.value_label.pack_forget()
        self.text_area.configure(state="normal", height=min(len(lines), self.MAX_LINES), width=max(30, min(max(len(line) for line in lines) + 1, self.MAX_CHARS)))
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text.rstrip("\n"))
        self.text_area.configure(state="disabled")
        self._table.pack(fill="x", pady=(0, 8))

    def get_text(self) -> str:
        return self._text

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_text())


class ParameterBox(ttk.LabelFrame):
    """
    A titled group of labelled entry fields for a tool's own parameters (confidence level, window size, distribution parameters, ...), built from a tool's _build_extra():

        self.box = ParameterBox(parent, "Parameters")
        self.box.pack(fill="x", pady=(0, 8))
        self.box.add("alpha", "Significance level", "0.05")
        ...
        value = self.box.get("alpha")      # the entry's text -- the tool parses/validates it

    set_label()/set() change a field's caption/content (e.g. when a mode cell switches what the parameter means), set_enabled(key, False) greys a field out when the current mode doesn't use it.
    """

    def __init__(self, parent, title: str = "Parameters"):
        super().__init__(parent, text=title, padding=10)
        self.columnconfigure(1, weight=1)
        self._labels: dict[str, ttk.Label] = {}
        self._entries: dict[str, ttk.Entry] = {}

    def add(self, key: str, label: str, default: str = "") -> ttk.Entry:
        row = len(self._entries)
        caption = ttk.Label(self, text=label, style="Status.TLabel")
        caption.grid(row=row, column=0, sticky="w", pady=(0 if row == 0 else 6, 0))
        entry = ttk.Entry(self)
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(0 if row == 0 else 6, 0))
        self._labels[key] = caption
        self._entries[key] = entry
        return entry

    def get(self, key: str) -> str:
        return self._entries[key].get()

    def set(self, key: str, value: str) -> None:
        entry = self._entries[key]
        was_disabled = str(entry.cget("state")) == "disabled"
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        if was_disabled:
            entry.configure(state="disabled")

    def set_label(self, key: str, text: str) -> None:
        self._labels[key].configure(text=text)

    def set_enabled(self, key: str, enabled: bool) -> None:
        self._entries[key].configure(state="normal" if enabled else "disabled")


class ComputeToolWindow(ToolWindow):
    """
    Covers the common case: take the shared workspace data (see data.store), compute a result from it, show the result.
    Subclass and override compute() (and optionally format_result()).

    Loading data (file or manual entry) happens only in the main window's I/O bar (see main.py's _build_data_bar) -- this window just shows whether something is loaded and, once computed, the result.

    instructions is shown once, above the data row -- how to use this specific tool (expected input shape, formula syntax, ...).
    result_format is shown in the result area before the first compute(), as a dummy/template of what the real result will look like (e.g. "y = a*x^n + b*x^2 + ... + c") -- both are meant to be passed through from a tool's own TOOL_INSTRUCTIONS/
    RESULT_FORMAT module constants, alongside TOOL_NAME/TOOL_DESCRIPTION.

    compute() returns a DataSet; run() puts it into the shared workspace automatically (replacing this window's previous result), so whatever tool you open next works on it (e.g. AFM Geometry -> Analysis). "Save" exports it as CSV.
    "Visualize" is a placeholder for now -- not wired up to anything yet.

    Class attributes for tools that need to deviate from the standard flow:
    requires_data (default True) -- set False for a tool that also makes sense without loaded data (e.g. a distribution calculator); compute() then receives None instead of a DataSet.
    data_hint -- the text shown in the data row while nothing is loaded.

    The window is sized to fit its own content (_size_to_content(), called at the end of __init__) rather than a fixed guessed size -- tools that add extra widgets via _build_extra() (e.g. custom non-linear fit's formula/parameter fields) don't need to pass their own size string, the window just grows to fit.
    """

    requires_data = True
    data_hint = "No data loaded -- load data via the main window."

    def __init__(self, parent, title: str, instructions: str = "", result_format: str = "", size: str = "420x360", description: str = ""):
        super().__init__(parent, title=title, size=size)
        instructions = instructions or description  # README / template pass `description=`
        self._last_result = None
        self._last_input = None  # the DataSet _last_result was computed from

        self._instructions_label = ttk.Label(self.content, text=instructions, style="Status.TLabel", wraplength=380, justify="left")
        self._instructions_label.pack(anchor="w", pady=(0, 8), fill="x")
        self._instructions_label.bind("<Configure>", self._on_instructions_resize)

        self._build_extra(self.content)

        self._data_row = ttk.Frame(self.content)
        self._data_row.pack(fill="x", pady=(0, 8))
        self._render_data_row()
        store.subscribe(self._render_data_row)  # status follows the workspace, also when this window's own result lands in it
        self.bind("<Destroy>", self._on_destroy)

        self.output = ResultDisplay(self.content, initial_text=result_format)
        self.output.pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(self.content)
        btn_row.pack(fill="x")
        Cell(btn_row, "Save", on_click=self._save, height=40, width=80).pack(side="left", fill="x", expand=True, padx=(0, 4))
        Cell(btn_row, "Visualize", on_click=self._visualize, height=40, width=80).pack(side="left", fill="x", expand=True, padx=4)
        Cell(btn_row, "Compute", on_click=self.run, height=40, width=80).pack(side="left", fill="x", expand=True, padx=(4, 0))

        self._size_to_content()

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            store.unsubscribe(self._render_data_row)

    def _on_instructions_resize(self, event) -> None:
        self._instructions_label.configure(wraplength=max(event.width - 4, 20))

    def _visualize(self) -> None:
        """Placeholder"""
        pass

    def _size_to_content(self) -> None:
        self.update_idletasks()
        width = self.winfo_reqwidth()
        max_height = int(self.winfo_screenheight() * style.LAYOUT.max_height_fraction)
        height = min(self.winfo_reqheight(), max_height)
        self.geometry(f"{width}x{height}")

    def _grow_to_content(self) -> None:
        # after a result arrived: make room for it, but never shrink a window the user may have sized themselves
        self.update_idletasks()
        max_height = int(self.winfo_screenheight() * style.LAYOUT.max_height_fraction)
        width = max(self.winfo_width(), self.winfo_reqwidth())
        height = min(max(self.winfo_height(), self.winfo_reqheight()), max_height)
        self.geometry(f"{width}x{height}")

    def _render_data_row(self) -> None:
        for w in self._data_row.winfo_children():
            w.destroy()

        if store.is_loaded():
            text = f"Using loaded data: {store.label()}"
        else:
            text = self.data_hint
        ttk.Label(self._data_row, text=text, style="Status.TLabel").pack(anchor="w")

    # -- extension point ---------------------------------------------

    def _build_extra(self, parent) -> None:
        # Override to insert tool-specific widgets
        pass

    # -- compute / result -------------------------------------------

    def compute(self, dataset: DataSet | None) -> DataSet:
        # Override: turn the workspace DataSet (None only if requires_data is False and nothing is loaded) into a result DataSet (for fits see data/results.fit_dataset). The base class puts it back into the workspace -- tools never format or store anything themselves.
        raise NotImplementedError

    def format_result(self, result: DataSet) -> str:
        # Generic rendering of the result DataSet (equation, parameters, statistics) -- override only if a tool genuinely needs something else.
        return results.summarize(result)

    def run(self) -> None:
        source = store.get() if store.is_loaded() else None
        if source is not None and source is self._last_result:
            source = self._last_input  # re-compute works on the original input (possibly none, see requires_data), not on this window's own previous result
        if source is None and self.requires_data:
            dialogs.show_error(self, "No data", "Please load data via the main window first.")
            return
        try:
            result = self.compute(source)
        except Exception as e:
            dialogs.show_error(self, "Computation failed", str(e))
            return
        if type(result) == str:
            return dialogs.show_error(self, "Computation failed", result)
        if not isinstance(result, DataSet):
            return dialogs.show_error(self, "Computation failed", f"compute() must return a DataSet, got {type(result).__name__}.")

        if result.source_tool is None:
            result.source_tool = self.title()
        if self._last_result is None:
            store.add(result)
        else:
            store.replace(self._last_result, result)  # re-compute in this window replaces its own previous result
        self._last_result = result
        self._last_input = source
        self.output.set_text(self.format_result(result), monospace=result.metadata.get("kind") == "statistics")
        self._grow_to_content()

    def _save(self) -> None:
        # Exports this window's result as CSV (the result is already in the workspace -- no manual "send" step)
        if self._last_result is None:
            dialogs.show_error(self, "Nothing to save", "Compute a result first.")
            return
        path = dialogs.ask_save_file(self, title="Save result")
        if not path:
            return
        try:
            savers.save_dataset_csv(path, self._last_result)
        except Exception as e:
            dialogs.show_error(self, "Save failed", str(e))

def make_mode_cell(parent, modes: list[tuple], on_change=None, label_prefix: str = "Mode: ", width: int = style.CELL_WIDTH, height: int = style.CELL_HEIGHT) -> Cell:
    if not modes:
        raise ValueError("make_mode_cell needs at least one mode")
    state = {"index": 0}

    def title_for(i: int) -> str:
        return f"{label_prefix}{modes[i][1]}"

    def status_for(i: int) -> str | None:
        entry = modes[i]
        return entry[2] if len(entry) > 2 else None

    def cycle() -> None:
        state["index"] = (state["index"] + 1) % len(modes)
        cell.title_label.configure(text=title_for(state["index"]))
        cell.set_status(status_for(state["index"]) or "")
        if on_change is not None:
            on_change(cell.mode())

    cell = Cell(parent, title=title_for(0), on_click=cycle, status_text=status_for(0), width=width, height=height)
    cell.mode = lambda: modes[state["index"]][0]
    return cell