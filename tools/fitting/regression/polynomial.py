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
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Polynomial"
TOOL_DESCRIPTION = (
    "Quadratic fit y = c0 + c1*x + c2*x^2 (2D), or quadratic surface "
    "z = c0 + c1*x + c2*y + c3*x^2 + c4*x*y + c5*y^2 (3D)."
)


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


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if not z:
        return _fit_2d(x, y)
    return _fit_3d_surface(x, y, z)


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        if len(result) == 3:
            c0, c1, c2 = result
            return f"c0 = {c0:.6g}\nc1 = {c1:.6g}\nc2 = {c2:.6g}\n"
        c0, c1, c2, c3, c4, c5 = result
        return (
            f"c0 = {c0:.6g}\nc1 = {c1:.6g}\nc2 = {c2:.6g}\n"
            f"c3 = {c3:.6g}\nc4 = {c4:.6g}\nc5 = {c5:.6g}\n"
        )


def open_window(parent) -> None:
    ToolWindow(parent)
