"""
Polynomial regression tool. 2D: quadratic least-squares fit
y = c0 + c1*x + c2*x^2 via the 3x3 normal equations (unchanged from
before). 3D: quadratic surface fit
z = c0 + c1*x + c2*y + c3*x^2 + c4*x*y + c5*y^2, via the general
least-squares normal equations (mathlib.least_squares_fit).

This replaces the previous 3D branch, which was an unfinished,
broken carry-over from the original script (called mathlib.mean()
with an unsupported calling convention and never produced a fit --
see the project's git history) with an actual surface fit.
"""

import tools.mathlib as t
from . import _points
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Polynomial"
TOOL_DESCRIPTION = (
    "Quadratic fit y = c0 + c1*x + c2*x^2 (2D), or quadratic surface "
    "z = c0 + c1*x + c2*y + c3*x^2 + c4*x*y + c5*y^2 (3D)."
)
TOOL_INSTRUCTIONS = "Load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = c0 + c1*x + c2*x^2  ||  z = c0 + c1*x + c2*y + c3*x^2 + c4*x*y + c5*y^2"


def _fit_2d(x, y):
    """Quadratic least-squares fit y = c0 + c1*x + c2*x^2, via the
    3x3 normal equations. Returns [c0, c1, c2]."""
    A = t.normal_matrix(x)
    b = t.normal_equation_vector(x, y)
    return t.solve_3_3_Gauss(A, b)


def _fit_3d_surface(x, y, z):
    """Quadratic surface fit z = c0 + c1*x + c2*y + c3*x^2 + c4*x*y +
    c5*y^2, via the general (6-parameter) normal equations. Needs at
    least 6 non-degenerate points. Returns [c0, c1, c2, c3, c4, c5]."""
    design = [[1.0, xi, yi, xi * xi, xi * yi, yi * yi] for xi, yi in zip(x, y)]
    return t.least_squares_fit(design, z)


def process(data):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y:
            y = list(range(n))
        if not z:
            return _fit_2d(x, y)
        return _fit_3d_surface(x, y, z)
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, data) -> dict:
        result = process(data)
        if isinstance(result, Exception):
            return {"error": str(result)}
        if len(result) == 3:
            c0, c1, c2 = result
            return {"name": TOOL_NAME, "c0": c0, "c1": c1, "c2": c2}
        c0, c1, c2, c3, c4, c5 = result
        return {"name": TOOL_NAME, "c0": c0, "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5}

    def format_result(self, result: dict) -> str:
        if "error" in result:
            return result["error"]
        return "\n".join(f"{k} = {v:.6g}" for k, v in result.items() if k != "name") + "\n"


def open_window(parent) -> None:
    ToolWindow(parent)