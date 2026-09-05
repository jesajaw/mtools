# mtools

A small tkinter framework around a collection of regression/analysis
and mathematical scripts. Instead of calling each script separately,
`main.py` opens a selection window; picking a tool opens that tool's
own window with its inputs and outputs. There will be more tools over
time.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

* **Central Launchpad (`main.py`):** Single entry point dashboard GUI for all integrated tools, grouped by category.
* **Shared Workspace (`data/store.py`):** One "current data" slot for the whole app, loaded/saved/cleared exclusively via the Input/Output bar at the top of the main window -- every tool window just reads whatever's currently there, no per-tool file picker. A tool's result can be sent back to the workspace ("Send result to workspace"), so tools chain: e.g. run AFM Geometry, then feed its output straight into an analysis tool.
* **Dynamic Discovery (`core/registry.py`):** Automatically scans and registers tools from `tools/<category>/<tool>.py` -- add a module, it shows up on next start.
* **Modular Architecture:** Strict separation between computational logic and GUI code; shared GUI building blocks live in `theme/widgets.py`.
* **Themes:** Centralized color palettes (`dark_purple`, `dark_blue`, `black_white`) and font presets (`segoe`, `system`) in `theme/style.py`, Windows dark-titlebar/DPI-awareness handling included.

## Tools

Status: **done** (real computation) / **placeholder** (GUI wired up, `compute()` not implemented yet).

* **fitting/** -- regression & curve fitting
  * Linear, Polynomial (2D quadratic + 3D quadratic surface), Quadratic, Exponential, Logarithmic, Multivariate, Custom Non-linear Fit -- done
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
├── main.py        # Main launcher GUI (Input/Output bar + category-grouped tool grid)
├── requirements.txt        # Python dependencies (stdlib only, currently)
├── LICENSE
├── README.md
├── .gitignore
├── core/
│   ├── __init__.py
│   ├── registry.py        # Scans tools/<category>/<tool>.py, imports & registers modules
│   └── tool_base.py        # ToolEntry contract / interface for tools
├── data/
│   ├── __init__.py
│   ├── loaders.py        # File -> parsed data (auto-detects delimiter, decimal comma, etc.)
│   ├── savers.py        # Parsed data -> file (clean CSV export)
│   └── store.py        # The shared in-memory workspace ("current data" for the whole app)
├── theme/
│   ├── __init__.py
│   ├── dialogs.py        # Themed popups (ThemedDialog, show_error, ask_yes_no, ask_open_file, ...)
│   ├── style.py        # Color/font schemes, the Layout dataclass, ttk styling, DPI/dark-titlebar (Windows)
│   └── widgets.py        # Reusable building blocks: Cell, ToolWindow, OutputPanel, ComputeToolWindow
└── tools/
    ├── __init__.py
    ├── mathlib.py        # Shared math routines, used by tools via `import tools.mathlib`
    ├── example/
    │   └── template.py        # Copy this to start a new tool
    ├── fitting/        # Regular Structure
    │   ├── __init__.py
    │   ├── linear.py
    │   ├── polynomial.py
    │   └── ...
    └── <category>/<tool>.py        # One category folder per topic, see Tools above
```

`data/` is deliberately NOT under `tools/`: it's shared infrastructure (imported by tools, not discovered as a topic), and deliberately not named `io` either -- that would shadow Python's stdlib `io` module.

## Running

Clone the repository, navigate into the project directory, and execute `main.py`:

```bash
python main.py
```

## The shared workspace

The bar at the top of the main window ("Load" / "Save", with "Clear" tucked into Save's corner) holds one data set at a time -- the app-wide workspace (`data/store.py`):

* **Load** -- pick a file, parsed via `data/loaders.py` (delimiter and decimal separator auto-detected; header/label rows are skipped automatically).
* **Save** / **Clear** -- export the current workspace contents as clean CSV, or drop them (Clear asks for confirmation first).
* Every tool window built on `ComputeToolWindow` just displays what's currently in the workspace ("Using loaded data: ..." or "No data loaded -- load data via the main window.") -- loading only ever happens through the main window's bar above, so the workspace stays a single source of truth for every open tool.
* After a tool computes a result, **"Send result to workspace"** makes that result the new workspace contents -- so the next tool you open picks up right where this one left off (e.g. AFM Geometry correction -> straight into an analysis tool, no manual save/reload in between).

## Adding a new tool

1. Pick an existing category folder under `tools/` (or create a new one -- just a folder with an `__init__.py`, see any existing category for the docstring convention).
2. Add a module, e.g. `tools/<category>/my_tool.py`:

```python
   from theme.widgets import ComputeToolWindow

   TOOL_NAME = "My Tool"
   TOOL_DESCRIPTION = "One or two sentences, plain text."


   class ToolWindow(ComputeToolWindow):
       def __init__(self, parent):
           super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

       def compute(self, data):
           # `data` is whatever's currently in the shared workspace,
           # already parsed (see data/loaders.py). Return anything --
           # a string, a dict, whatever format_result() (optional
           # override) can turn into text.
           ...

       # optional: override format_result(self, result) -> str and/or
       # save_result(self, path, content) for custom formatting/export,
       # or _build_extra(self, parent) to add tool-specific input
       # widgets (formula fields, parameter entries, ...) above the
       # data status cell -- the window resizes to fit automatically.

   def open_window(parent) -> None:
       ToolWindow(parent)
```
3. That's it -- `main.py` discovers it automatically on the next start (`core/registry.py` scans every category folder for modules exposing `TOOL_NAME`, `TOOL_DESCRIPTION`, `open_window`). No other file needs to change.

A module whose filename starts with `_` is treated as a private helper, not a tool, and is skipped by discovery -- use that for code shared between tools in the same category.

See `theme/widgets.py` for the full building-block set (`Cell`, `ToolWindow`, `OutputPanel`, `ComputeToolWindow`) if a tool needs something more custom than the standard workspace-in/result-out flow.

## Theme

Switch the color palette via `COLOR_SCHEME` and the font preset via `FONT_SCHEME`, both in `theme/style.py` (`dark_purple`/`dark_blue`/`black_white`, `segoe`/`system`). Main-window grid sizing (columns, cell spacing, max height fraction, ...) lives in the same file as `style.LAYOUT`, a single `Layout` dataclass instance instead of scattered numbers.

## Requirements

Standard library only -- see `requirements.txt`. tkinter ships with the standard Windows/macOS Python installers; on some Linux distros install it separately (`sudo apt install python3-tk`).

## License

MIT, see `LICENSE`.
