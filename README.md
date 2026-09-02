# mtools

A small tkinter framework around a collection of regression/analysis
and mathematical scripts. Instead of calling each script separately,
`main.py` opens a selection window; picking a tool opens that tool's
own window with its inputs, outputs, and (where needed) file
selection. There will be more tools over time.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

* **Central Launchpad (`main.py`):** Single entry point dashboard GUI for all integrated tools, grouped by category.
* **Shared Workspace (`data/store.py`):** One "current data" slot for the whole app. Load a file once via the Input/Output bar at the top, and every tool uses it automatically -- no per-tool file picker as long as something's loaded. A tool's result can be sent back to the workspace ("Send result to workspace"), so tools chain: e.g. run AFM Geometry, then feed its output straight into an analysis tool.
* **Dynamic Discovery (`core/registry.py`):** Automatically scans and registers tools from `tools/<category>/<tool>.py` -- add a module, it shows up on next start.
* **Modular Architecture:** Strict separation between computational logic and GUI code; shared GUI building blocks live in `theme/widgets.py`.
* **Themes:** Centralized palette configuration (`dark_purple`, `dark_blue`, `black_white`), Windows dark-titlebar/DPI-awareness handling included.

## Tools

Status: **done** (real computation) / **placeholder** (GUI wired up, `compute()` not implemented yet).

* **fitting/** -- regression & curve fitting
  * Linear -- done
  * Polynomial (quadratic, y = c0 + c1x + c2x^2) -- done
  * Exponential, Logarithmic, Quadratic, Multivariate, Custom Non-linear Fit -- placeholder
* **afm/** -- AFM data processing
  * Geometry (rotate/mirror/crop/level), Filters & Defects, Roughness (ISO Ra/Rq), Grain Analysis -- placeholder
* **ode/**, **pde/** -- differential equation solvers -- placeholder
* **statistics/**
  * Descriptive Statistics, Hypothesis Testing, Probability Distributions, Data Preprocessing, Confidence Intervals -- placeholder
* **spectroscopy/** -- spectral analysis & peak fitting -- placeholder
* **simulation/** -- Monte Carlo / SRIM-style physical modeling -- placeholder
* **transformation/** -- FFT, frequency filtering, normalization, Laplace transform -- placeholder
* **optics/**
  * Diffraction & Interference, Wavefront & Propagation -- placeholder
* **units/** -- unit conversion & dimensional analysis -- placeholder
* **linear_algebra/**
  * Matrix Operations, Eigenvalues & Eigenvectors, Matrix Decomposition (LU/QR/SVD), Linear System Solver -- placeholder
* **interpolation/**
  * Spline Interpolation, Polynomial Interpolation -- placeholder
* **optimization/**
  * Root Finding, Minimization -- placeholder
* **error_propagation/** -- uncertainty propagation through a computation chain -- placeholder
* **example/** -- reference template for new tools

## Structure

```text
mtools/
├── main.py                     # Main launcher GUI (Input/Output bar + category-grouped tool grid)
├── requirements.txt            # Python dependencies (stdlib only, currently)
├── LICENSE
├── README.md
├── .gitignore
├── core/
│   ├── registry.py             # Scans tools/<category>/<tool>.py, imports & registers modules
│   └── tool_base.py            # ToolEntry contract / interface for tools
├── data/
│   ├── loaders.py              # File -> parsed data (auto-detects delimiter, decimal comma, etc.)
│   ├── savers.py                # Parsed data -> file (clean CSV export)
│   └── store.py                 # The shared in-memory workspace ("current data" for the whole app)
├── theme/
│   ├── dialogs.py               # Themed popups (ThemedDialog, show_error, ask_open_file, ...)
│   ├── style.py                  # Palette themes, ttk styling, DPI/dark-titlebar (Windows)
│   └── widgets.py                # Reusable building blocks: ToolWindow, FileInputRow, OutputPanel,
│                                  #   ComputeToolWindow (workspace-aware), DataBar (the top I/O bar)
└── tools/
    ├── mathlib.py               # Shared math routines, used by tools via `import tools.mathlib`
    ├── example/
    │   └── template.py          # Copy this to start a new tool
    ├── fitting/
    │   ├── linear.py
    │   ├── polynomial.py
    │   └── ...
    └── <category>/<tool>.py     # One category folder per topic, see Tools above
```

`data/` is deliberately NOT under `tools/`: it's shared infrastructure
(imported by tools, not discovered as a topic), and deliberately not
named `io` either -- that would shadow Python's stdlib `io` module.

## Running

Clone the repository, navigate into the project directory, and execute `main.py`:

```bash
python main.py
```

## The shared workspace

The bar at the top of the main window ("Input" / "Output") holds one
data set at a time -- the app-wide workspace (`data/store.py`):

* **Load...** -- pick a file, parsed via `data/loaders.py` (delimiter
  and decimal separator auto-detected; header/label rows are skipped
  automatically).
* **Save...** / **Clear** -- export the current workspace contents as
  clean CSV, or drop them.
* Any tool built on `ComputeToolWindow` picks this up automatically:
  if something's loaded, the tool shows "Using loaded data: ..." and
  a "Load different file..." option instead of its own file picker.
  If nothing's loaded yet, the tool shows a file picker itself --
  picking a file there also fills the shared workspace.
* After a tool computes a result, **"Send result to workspace"**
  makes that result the new workspace contents -- so the next tool
  you open picks up right where this one left off (e.g. AFM Geometry
  correction -> straight into an analysis tool, no manual
  save/reload in between).

## Adding a new tool

1. Pick an existing category folder under `tools/` (or create a new one -- just a folder with an `__init__.py`, see any existing category for the docstring convention).
2. Add a module, e.g. `tools/<category>/my_tool.py`:

   ```python
   from theme.widgets import ComputeToolWindow

   TOOL_NAME = "My Tool"
   TOOL_DESCRIPTION = "One or two sentences, plain text."


   class ToolWindow(ComputeToolWindow):
       input_label = "Input file"
       input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

       def __init__(self, parent):
           super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

       def compute(self, data):
           # `data` is whatever's in the shared workspace (or was just
           # loaded via this tool's own picker) -- already parsed, see
           # data/loaders.py. Return anything -- a string, a dict,
           # whatever format_result() (optional override) can turn
           # into text.
           ...

       # optional: override format_result(self, result) -> str and/or
       # save_result(self, path, content) for custom formatting/export

   def open_window(parent) -> None:
       ToolWindow(parent)
   ```
3. That's it -- `main.py` discovers it automatically on the next start (`core/registry.py` scans every category folder for modules exposing `TOOL_NAME`, `TOOL_DESCRIPTION`, `open_window`). No other file needs to change.

A module whose filename starts with `_` is treated as a private helper, not a tool, and is skipped by discovery -- use that for code shared between tools in the same category.

See `theme/widgets.py` for the full building-block set (`ToolWindow`, `FileInputRow`, `OutputPanel`, `ComputeToolWindow`, `DataBar`) if a tool needs something more custom than the standard workspace-in/result-out flow.

## Theme

Switch palette via `COLOR_SCHEME` in `theme/style.py` (`dark_purple`, `dark_blue`, `black_white`).

## Requirements

Standard library only -- see `requirements.txt`. tkinter ships with the standard Windows/macOS Python installers; on some Linux distros install it separately (`sudo apt install python3-tk`).

## License

MIT, see `LICENSE`.
