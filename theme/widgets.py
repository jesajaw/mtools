"""
Reusable building blocks for tool windows, so each tool's ui doesn't have to rebuild the same layout from scratch. Provides templates for:
- Cell: a clickable tile (title, optional status line, hover highlight) -- the one building block every cell in the app is made from: tools in the main window's grid, Load/Save there too and the read-only "Data" status cell in every ToolWindow
- ToolWindow: a themed Toplevel with a title, a description line, and a `self.content` frame that subclasses fill with their own inputs/outputs/parameters
- OutputPanel: a text area for computed results plus a "Save..." button that writes them to a file via a callback
- ComputeToolWindow: the common "load or reuse workspace data, run compute(), show/save the result" tool window -- reads/writes the shared data.store workspace so tools can be chained
"""

import tkinter as tk
from tkinter import ttk
from data import store
from . import style, dialogs
from data.dataset import DataSet, DataArray

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
    """

    def __init__(self, parent, label: str = "Result", initial_text: str = ""):
        super().__init__(parent)
        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="x")

        ttk.Button(box, text="\u29c9", style="Icon.TButton", command=self._copy).pack(anchor="e")
        self.value_label = ttk.Label(box, text=initial_text, style="ResultText.TLabel", wraplength=200, justify="center", anchor="center")
        self.value_label.pack(fill="x", pady=(0, 8))

    def set_text(self, text: str) -> None:
        self.value_label.configure(text=text)

    def get_text(self) -> str:
        return self.value_label.cget("text")

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_text())


class ComputeToolWindow(ToolWindow):
    """
    Covers the common case: take the shared workspace data (see data.store), compute a result from it, show the result.
    Subclass and override compute() (and optionally format_result()).

    Loading data (file or manual entry) happens only in the main window's I/O bar (see main.py's _build_data_bar) -- this window just shows whether something is loaded and, once computed, the result.

    instructions is shown once, above the data row -- how to use this specific tool (expected input shape, formula syntax, ...).
    result_format is shown in the result area before the first compute(), as a dummy/template of what the real result will look like (e.g. "y = a*x^n + b*x^2 + ... + c") -- both are meant to be passed through from a tool's own TOOL_INSTRUCTIONS/
    RESULT_FORMAT module constants, alongside TOOL_NAME/TOOL_DESCRIPTION.

    After a successful compute(), "Send result to workspace" becomes available -- click it to make this tool's result the input for whatever tool you open next (e.g. AFM Geometry -> Analysis).
    "Visualize" is a placeholder for now -- not wired up to anything yet.

    The window is sized to fit its own content (_size_to_content(), called at the end of __init__) rather than a fixed guessed size -- tools that add extra widgets via _build_extra() (e.g. custom non-linear fit's formula/parameter fields) don't need to pass their own size string, the window just grows to fit.
    """

    def __init__(self, parent, title: str, instructions: str = "", result_format: str = "", size: str = "420x360"):
        super().__init__(parent, title=title, size=size)
        self._last_result = None

        ttk.Label(self.content, text=instructions, style="Status.TLabel", wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

        self._build_extra(self.content)

        self._data_row = ttk.Frame(self.content)
        self._data_row.pack(fill="x", pady=(0, 8))
        self._render_data_row()

        self.output = ResultDisplay(self.content, initial_text=result_format)
        self.output.pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(self.content)
        btn_row.pack(fill="x")
        Cell(btn_row, "Save", on_click=self._save, height=40, width=80).pack(side="left", fill="x", expand=True, padx=(0, 4))
        Cell(btn_row, "Visualize", on_click=self._visualize, height=40, width=80).pack(side="left", fill="x", expand=True, padx=4)
        Cell(btn_row, "Compute", on_click=self.run, height=40, width=80).pack(side="left", fill="x", expand=True, padx=(4, 0))

        self._size_to_content()

    def _visualize(self) -> None:
        """Placeholder"""
        pass

    def _size_to_content(self) -> None:
        self.update_idletasks()
        width = self.winfo_reqwidth()
        max_height = int(self.winfo_screenheight() * style.LAYOUT.max_height_fraction)
        height = min(self.winfo_reqheight(), max_height)
        self.geometry(f"{width}x{height}")

    def _render_data_row(self) -> None:
        for w in self._data_row.winfo_children():
            w.destroy()

        if store.is_loaded():
            text = f"Using loaded data: {store.label()}"
        else:
            text = "No data loaded -- load data via the main window."
        ttk.Label(self._data_row, text=text, style="Status.TLabel").pack(anchor="w")

    # -- extension point ---------------------------------------------

    def _build_extra(self, parent) -> None:
        # Override to insert tool-specific widgets
        pass

    # -- compute / result -------------------------------------------

    def compute(self, dataset) -> dict:
        return process(_points.dataset_to_points(dataset))
        # Override: turn the workspace data into a result (any type -- format_result() below turns it into display text)
        #raise NotImplementedError

    def format_result(self, result) -> str:
        # Override if the result needs custom formatting. Default: plain str(result).
        return str(result)

    def run(self) -> None:
        if not store.is_loaded():
            dialogs.show_error(self, "No data", "Please load data via the main window first.")
            return
        try:
            result = self.compute(store.get())
        except Exception as e:
            dialogs.show_error(self, "Computation failed", str(e))
            return
        if type(result) == str:
            return dialogs.show_error(self, "Computation failed", result)

        self._last_result = result
        self.output.set_text(self.format_result(result))

    def _save(self) -> None:
        if self._last_result is None:
            return
        store.add(DataSet(
            name=f"Output of {self.title()}",
            data={k: DataArray(values=v, name=k) for k, v in self._last_result.items()},
            source_tool=self.title(),
        ))
        self._render_data_row()