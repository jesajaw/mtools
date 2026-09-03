"""
Quadratic regression tool: y = a*x^2 + b*x + c, via ordinary least
squares. This is the same fit as the 2D branch of 'Polynomial'
(tools/fitting/polynomial.py) -- resolving the overlap the previous
placeholder flagged, Quadratic just exposes that fit under the
conventional a/b/c naming and only accepts 2D data, while Polynomial
additionally covers the 3D quadratic-surface case. Reuses
polynomial._fit_2d() instead of duplicating the math.
"""

import tools.mathlib as t
from tools.fitting import polynomial
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Quadratic"
TOOL_DESCRIPTION = "Least-squares quadratic fit: y = a*x^2 + b*x + c."


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if z:
        raise ValueError(
            "Quadratic fit only supports 2D data (x, y) -- see 'Polynomial' for the 3D surface fit."
        )
    c0, c1, c2 = polynomial._fit_2d(x, y)
    return c2, c1, c0, d, (x, y)  # a, b, c


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        a, b, c, d, _ = result
        return f"a = {a:.6g}\nb = {b:.6g}\nc = {c:.6g}\ndimension = {d}\n"


def open_window(parent) -> None:
    ToolWindow(parent)
