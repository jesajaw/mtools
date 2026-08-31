# mtools

A small tkinter framework around a collection of regression/analysis ~ mathematicall scripts.
Instead of calling each script separately, `main.py` opens a selection window; picking a tool opens that tool's own window with its inputs, outputs, and (where needed) file selection.

# Structure

```
mtools/
├── main.py                    # main window, dynamic tool grid
├── requirements.txt
├── LICENSE
├── theme/
│   ├── style.py                # color scheme (3 palettes) + ttk styles
│   └── dialogs.py               # ThemedDialog, show_error, ask_yes_no, ask_string, ask_open_file
├── core/
│   ├── tool_base.py             # tool interface contract (ToolEntry)
│   └── registry.py              # scans tools/, imports & collects them
└── tools/
    └── example_linear_fit/      # template for real tools
        ├── __init__.py          # TOOL_NAME, TOOL_DESCRIPTION, open_window()
        ├── gui.py                # 2nd window: file input, run, output
        └── regression.py         # pure computation (your existing script goes here)
```

# Running

```
python main.py
```

Opens the main window with one tile per discovered tool. Click
"Open" to launch that tool's window.

# Adding a new tool

1. Create a folder under `tools/`, e.g. `tools/exp_fit/`.
2. Drop your existing computation script in there unchanged (e.g.
   `regression.py`), as a plain function with no GUI dependency.
3. Write `gui.py` modeled on `tools/example_linear_fit/gui.py`:
   inputs, a run button, and an output area.
4. Add `__init__.py` with:
   ```python
   from .gui import ToolWindow

   TOOL_NAME = "..."
   TOOL_DESCRIPTION = "..."

   def open_window(parent) -> None:
       ToolWindow(parent)
   ```

`main.py` picks it up automatically on the next start -- no other
file needs to change.

# Theme

Ported from an earlier project (DMX Derby Controller): `clam` ttk
theme, cell-grid layout, `ThemedDialog` instead of
`tkinter.messagebox`/`simpledialog`. Switch palette via
`COLOR_SCHEME` in `theme/style.py` (`dark_purple`, `dark_blue`,
`black_white`).

# Requirements

Standard library only -- see `requirements.txt`. tkinter ships with
the standard Windows/macOS Python installers; on some Linux distros
install it separately (`sudo apt install python3-tk`).

# License

MIT, see `LICENSE`.
