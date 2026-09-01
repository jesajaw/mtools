# mtools

A small tkinter framework around a collection of regression/analysis ~ mathematicall scripts. Instead of calling each script separately, `main.py` opens a selection window; picking a tool opens that tool's own window with its inputs, outputs, and (where needed) file selection etc. ~ there will be more tools over time.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

* **Central Launchpad (`main.py`):** Single entry point dashboard GUI for all integrated tools.
* **Dynamic Discovery (`registry.py`):** Automatically scans and registers new tools from `tools/`.
* **Modular Architecture:** Strict separation between computational logic and GUI code.
* **Themes:** Centralized palette configuration (`dark_purple`, `dark_blue`, `black_white`).

## Tools -- todo

* **fitting/**
  * **Regression Models:** Linear, polynomial, exponential, logarithmic, and custom non-linear curve fitting as well as multivariate.

* **afm/**
  * **Geometry:** Tools for rotating, mirroring, cropping, and leveling height data (via polynomial fit or 3-point leveling).
  * **Filters & Defects:** Noise reduction (Gaussian, median) and correction of measurement artifacts like line scars or bad data points.
  * **Roughness:** Calculation of surface roughness parameters according to ISO standards (such as $R_a$, $R_q$) and statistical height distributions.
  * **Grain Analysis:** Segmentation and measurement of individual surface structures/grains (size, height, volume) using thresholding.

* **ODE/** / **PDE/**
  * Solvers for ordinary & partial differential equations

* **statistics/**
  * **Descriptive Statistics:** Calculation of central tendency (mean, median, mode) and dispersion (variance, standard deviation, range, interquartile range).
  * **Hypothesis Testing:** Execution of statistical tests such as t-tests, ANOVA, and Chi-Square tests to evaluate hypotheses and determine significance ($p$-values).
  * **Probability Distributions:** Evaluation of common probability distributions (normal, binomial, Poisson) and calculation of probability density/mass functions (PDF/PMF and CDF).
  * **Data Preprocessing:** Tools for handling missing data, outlier detection, normalization, and standardization.
  * **Confidence Intervals:** Estimation of population parameters with specified confidence levels to quantify uncertainty.

* **spectroscopy/**
  * Spectral analysis & peak fitting
* **simulation/**
  * Physical modeling & Monte Carlo simulation, SRIM
* **transformation/**
  * FFT, frequency filtering & data normalization, Laplace

* **optics/**
  * **Diffraction & Interference:** Calculations involving the grating equation, interference patterns, and diffraction limits for various optical configurations.
  * **Wavefront & Propagation:** Modeling light propagation and phase transformations.

* **units/**
  * **Conversion & Dimensional Analysis:** Conversion between SI and imperial units, custom unit definitions.

## Structure

```text
mtools/
├── main.py                     # Main launcher GUI
├── requirements.txt            # Python dependencies
├── LICENSE                     # License file
├── README.md                   # Project documentation
├── .gitignore                  # Git exclusion rules
├── core/
│   ├── registry.py             # Scans tools/, imports & registers modules
│   └── tool_base.py            # Base contract / interface for tools
├── theme/
│   ├── dialogs.py              # Themed dialogs (errors, confirmation, file prompts)
│   ├── style.py                # Palette themes & ttk styling
│   └── widgets.py              # Custom reusable UI elements
└── tools/
    ├── mathlib.py              # Shared math routines
    ├── example/                # Reference template for new tools
    │   └── template.py         # Tool GUI template
    ...
```
... see [Tools](#tools----todo)

## Running

Clone the repository, navigate into the project directory, and execute `main.py`:

```bash
python main.py
```

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
