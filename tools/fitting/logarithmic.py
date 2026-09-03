"""
Logarithmic regression tool. Fits y = a*ln(x) + b via an ordinary
least-squares line fit of y against ln(x) -- the mirror image of the
exponential tool's linearization (there it's ln(y) against x, here
it's y against ln(x)).
"""

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Logarithmic"
TOOL_DESCRIPTION = "Least-squares logarithmic fit: y = a*ln(x) + b."


def _fit_logarithmic(n, x, y):
    """Least-squares fit of y = a*ln(x) + b: OLS line fit of y
    against ln(x) gives slope = a, intercept = b. Requires all
    x > 0 (log of non-positive values is undefined)."""
    if any(v <= 0 for v in x):
        raise ValueError("Logarithmic fit requires all x-values to be positive.")
    ln_x = t.log(x)
    slope = (
        n * t.sum_list(t.products(ln_x, y)) - t.sum_list(ln_x) * t.sum_list(y)
    ) / (n * t.sum_list(t.square(ln_x)) - t.sum_list(ln_x) ** 2)
    cln_x, cy = t.mean([ln_x, y])
    intercept = cy - slope * cln_x
    return slope, intercept


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if z:
        raise ValueError("Logarithmic fit only supports 2D data (x, y).")
    a, b = _fit_logarithmic(n, x, y)
    return a, b, d, (x, y)


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        a, b, d, _ = result
        return f"a = {a:.6g}\nb = {b:.6g}\ndimension = {d}\n"


def open_window(parent) -> None:
    ToolWindow(parent)
