# mtools

A small tkinter framework around a collection of regression/analysis ~ mathematicall scripts. Instead of calling each script separately, `main.py` opens a selection window; picking a tool opens that tool's own window with its inputs, outputs, and (where needed) file selection etc. ~ there will be more tools over time.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

* **Central Launchpad (`main.py`):** Single entry point dashboard GUI for all integrated tools.
* **Dynamic Discovery (`registry.py`):** Automatically scans and registers new tools from `tools/`.
* **Modular Architecture:** Strict separation between computational logic and GUI code.
* **Themes:** Centralized palette configuration (`dark_purple`, `dark_blue`, `black_white`).

## Tools

* **fitting/**
  * Linear, quadratic & polynomial fits \todo
  * Exponential & logarithmic fits \todo
  * Multivariate regressions \todo
* **afm/**
  * Topography processing, leveling & profile extraction \todo
* **ODE/** / **PDE/**
  * Solvers for ordinary & partial differential equations \todo
* **statistics/**
  * Descriptive statistics, distributions & outlier detection \todo
* **spectroscopy/**
  * Spectral analysis & peak fitting \todo
* **simulation/**
  * Physical modeling & Monte Carlo simulation \todo
* **transformation/**
  * FFT, frequency filtering & data normalization \todo

## Structure

```
mtools/
├── main.py                   # main window
├── requirements.txt
├── LICENSE
├── README
├── theme/
│   ├── style.py              # color scheme + ttk styles
│   └── dialogs.py            # ThemedDialog, show_error, ask_yes_no, ask_string, ask_open_file
├── core/
│   ├── tool_base.py          # tool interface contract (ToolEntry)
│   └── registry.py           # scans tools/, imports & collects them
└── tools/
│   ├── gui_elements.py       # some standart elements which are may used over multiple tools (in-/output)
    └── example_linear_fit/   # template for real tools
        ├── __init__.py       # TOOL_NAME, TOOL_DESCRIPTION, open_window()
        ├── gui.py            # 2nd window: file input, run, output
        └── regression.py     # pure computation (your existing script goes here)
    └── regression/
    └── analysis/
    └── afm data/
    └── .../
    may new structure hierachy here -> subfolders: regression, analysis etc.
```

## Running

After cloning, just bash in the right path:
```
python main.py
```
Opens the main window with one tile per discovered tool. Click "Open" to launch that tool's window.

## Adding a new tool

1. Create a folder under `tools/`, e.g. `tools/exp_fit/`.
2. Drop your existing computation script in there unchanged (e.g. `regression.py`), as a plain function with no GUI dependency.
3. Write `gui.py` modeled on `tools/example_linear_fit/gui.py`: inputs, a run button, and an output area.
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

## Theme

Switch palette via `COLOR_SCHEME` in `theme/style.py` (`dark_purple`, `dark_blue`, `black_white`) in `theme/style.py`

## Requirements

Standard library only -- see `requirements.txt` . tkinter ships with the standard Windows/macOS Python installers; on some Linux distros install it separately (`sudo apt install python3-tk`).

# License

MIT, see `LICENSE`.
