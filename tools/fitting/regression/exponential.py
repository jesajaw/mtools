"""
Exponential regression tool. Fits y = a * e^(b*x) (2D), or
z = a * e^(b*x + c*y) (3D) by linearizing: ln(y) = ln(a) + b*x (or
ln(z) = ln(a) + b*x + c*y), then running an ordinary least-squares
line/plane fit via mathlib -- the slope(s) become b (and c),
exp(intercept) becomes a. Same auto-detected 2D/3D split as
Linear/Polynomial/Multivariate: dimension follows directly from
whether the loaded data has a z column, not a modeling choice, so
there's no mode picker here (unlike Logarithmic, where linear-log/
log-linear/log-log genuinely are different models for the same
data).
"""

import math

import tools.mathlib as t
from . import _points
from data import results
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Exponential"
TOOL_DESCRIPTION = "Least-squares exponential fit: y = a*e^(b*x) (2D), or z = a*e^(b*x + c*y) (3D), via log-linearization."
TOOL_INSTRUCTIONS = "Load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = a*e^(b*x)  \n  z = a*e^(b*x + c*y)"


def _fit_exponential_2d(n, x, y):
    """Least-squares fit of y = a*e^(bx) via linearization: OLS line
    fit of ln(y) against x gives slope = b, intercept = ln(a).
    Requires all y > 0 (log of non-positive values is undefined)."""
    if any(v <= 0 for v in y):
        raise ValueError("Exponential fit requires all y-values to be positive.")
    ln_y = t.log(y)
    slope = (
        n * t.sum_list(t.products(x, ln_y)) - t.sum_list(x) * t.sum_list(ln_y)
    ) / (n * t.sum_list(t.square(x)) - t.sum_list(x) ** 2)
    cx, cln_y = t.mean([x, ln_y])
    intercept = cln_y - slope * cx
    return math.exp(intercept), slope


def _fit_exponential_3d(x, y, z):
    """Least-squares fit of z = a*e^(b*x + c*y) via linearization:
    OLS plane fit of ln(z) against x and y gives slope_x = b,
    slope_y = c, intercept = ln(a). Requires all z > 0."""
    if any(v <= 0 for v in z):
        raise ValueError("Exponential fit requires all z-values to be positive.")
    ln_z = t.log(z)
    n = len(x)
    A = [
        [n, t.sum_list(x), t.sum_list(y)],
        [t.sum_list(x), t.sum_list(t.square(x)), t.sum_list(t.products(x, y))],
        [t.sum_list(y), t.sum_list(t.products(x, y)), t.sum_list(t.square(y))],
    ]
    B = [t.sum_list(ln_z), t.sum_list(t.products(x, ln_z)), t.sum_list(t.products(y, ln_z))]
    intercept, b, c = t.solve_gauss(A, B)
    return math.exp(intercept), b, c


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, dataset):
        n, d, x, y, z = _points.split_data(dataset)
        if not y:
            y = list(range(n))
        note = "fitted on ln(response); fit/residual are in original units"
        if not z:
            a, b = _fit_exponential_2d(n, x, y)
            fitted = [a * math.exp(b * xi) for xi in x]
            return results.fit_dataset(dataset, TOOL_NAME, "y = a*e^(b*x)", {"a": a, "b": b}, response=y, fitted=fitted, metadata={"dimension": 2, "fit_space": note})
        a, b, c = _fit_exponential_3d(x, y, z)
        fitted = [a * math.exp(b * xi + c * yi) for xi, yi in zip(x, y)]
        return results.fit_dataset(dataset, TOOL_NAME, "z = a*e^(b*x + c*y)", {"a": a, "b": b, "c": c}, response=z, fitted=fitted, metadata={"dimension": 3, "fit_space": note})


def open_window(parent) -> None:
    ToolWindow(parent)