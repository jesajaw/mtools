"""
Descriptive statistics for every column of the workspace data (x, y, z -- and for a fit result also fit/residual, so e.g. the residuals can be inspected directly): sample size, central tendency (mean, median, mode), position (min, quartiles, max), dispersion (variance, standard deviation, standard error, range, IQR, coefficient of variation) and shape (skewness, excess kurtosis).

One mode cell switches between the sample estimators (divide by n - 1, bias-adjusted skewness/kurtosis -- the Excel/pandas convention) and the population ones (divide by n). Quartiles use linear interpolation between order statistics (the NumPy/R default, "type 7"). Several columns are shown side by side as one table.
"""

import math

from . import _basic as b
from . import _ui
from data import results
from ui.widgets import ComputeToolWindow

TOOL_NAME = "Descriptive Statistics"
TOOL_DESCRIPTION = "Central tendency (mean, median, mode), dispersion (variance, standard deviation, range, IQR) and shape (skewness, kurtosis) of every column."
TOOL_INSTRUCTIONS = "Load one or more columns (x[, y[, z]]) via the main window, optionally switch between sample (n-1) and population (n) estimators, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "n, mean, median, mode, min, Q1, Q3, max, range, IQR,\nvariance, std dev, std error, CV, skewness, kurtosis\n(one column per data column)"

ESTIMATORS = [("sample", "sample (n-1)"), ("population", "population (n)")]


def _mode_text(values) -> str:
    found, _count = b.modes(values)
    if not found:
        return "none"
    shown = ", ".join(f"{v:.6g}" for v in found[:3])
    return shown + (f" (+{len(found) - 3} more)" if len(found) > 3 else "")


def describe(values: list[float], sample: bool = True) -> dict:
    """All statistics of one column as {label: value}; None where undefined for this sample."""
    n = len(values)
    ordered = sorted(values)
    m = b.mean(values)
    var = b.variance(values, 1 if sample else 0)
    sd = None if var is None else math.sqrt(var)
    q1, med, q3 = (b.quantile(ordered, q) for q in (0.25, 0.5, 0.75))
    return {
        "n": n,
        "mean": m,
        "median": med,
        "mode": _mode_text(values),
        "min": ordered[0],
        "Q1": q1,
        "Q3": q3,
        "max": ordered[-1],
        "range": ordered[-1] - ordered[0],
        "IQR": q3 - q1,
        "variance": var,
        "std dev": sd,
        "std error": None if sd is None else sd / math.sqrt(n),
        "CV": None if sd is None or m == 0 else sd / abs(m),
        "skewness": b.skewness(values, sample),
        "kurtosis": b.excess_kurtosis(values, sample),
    }


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._estimator = "sample"
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, ESTIMATORS, "Estimator: ", self._on_estimator_change)

    def _on_estimator_change(self, key: str) -> None:
        self._estimator = key

    def compute(self, dataset):
        cols = b.columns(dataset)
        sample = self._estimator == "sample"
        groups = {name: describe(values, sample) for name, values in cols.items()}
        title = f"Descriptive statistics ({'sample, n-1' if sample else 'population, n'})"
        return results.stats_dataset(dataset, TOOL_NAME, title, groups, metadata={"estimator": self._estimator})


def open_window(parent) -> None:
    ToolWindow(parent)
