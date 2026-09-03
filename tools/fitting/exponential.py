"""
Exponential regression tool. Fits y = a * e^(b*x) by linearizing:
ln(y) = ln(a) + b*x, then running an ordinary least-squares line fit
on (x, ln(y)) via mathlib -- slope becomes b, exp(intercept) becomes a.
"""

import math

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Exponential"
TOOL_DESCRIPTION = "Least-squares exponential fit: y = a * e^(b*x), via log-linearization."


def _fit_exponential(n, x, y):
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


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if z:
        raise ValueError("Exponential fit only supports 2D data (x, y).")
    a, b = _fit_exponential(n, x, y)
    return a, b, d, (x, y)


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        a, b, d, _ = result
        return f"a = {a:.6g}\nb = {b:.6g}\ndimension = {d}\n"


def open_window(parent) -> None:
    ToolWindow(parent)