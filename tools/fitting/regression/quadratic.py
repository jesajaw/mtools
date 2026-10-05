"""
Quadratic regression tool: y = a*x^2 + b*x + c (2D), or z = a*x^2 + b*x + c + d*y + e*y^2 (3D) -- the same quadratic structure applied to x, and additively to y too, no cross term (no x*y). This is the same fit as Polynomial's degree=2 case (tools/fitting/regression/polynomial.py) -- Quadratic just exposes it under the conventional a/b/c/d/e naming at a fixed degree, while Polynomial covers any degree. Reuses polynomial._fit_2d()/ _fit_3d_surface() instead of duplicating the math.
"""

from . import _points, polynomial
from data import results
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Quadratic"
TOOL_DESCRIPTION = "Least-squares quadratic fit: y = a*x^2 + b*x + c (2D), or z = a*x^2 + b*x + c + d*y + e*y^2 (3D)."
TOOL_INSTRUCTIONS = "Load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = a*x^2 + b*x + c  \n  z = a*x^2 + b*x + c + d*y + e*y^2"


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, dataset):
        n, d, x, y, z = _points.split_data(dataset)
        if not y:
            y = list(range(n))
        if not z:
            c0, c1, c2 = polynomial._fit_2d(x, y, 2)
            a, b, c = c2, c1, c0
            fitted = [a * xi ** 2 + b * xi + c for xi in x]
            return results.fit_dataset(dataset, TOOL_NAME, "y = a*x^2 + b*x + c", {"a": a, "b": b, "c": c}, response=y, fitted=fitted, metadata={"dimension": 2})
        c0, cx1, cx2, cy1, cy2 = polynomial._fit_3d_surface(x, y, z, 2)
        a, b, c, dd, e = cx2, cx1, c0, cy1, cy2
        fitted = [a * xi ** 2 + b * xi + c + dd * yi + e * yi ** 2 for xi, yi in zip(x, y)]
        return results.fit_dataset(dataset, TOOL_NAME, "z = a*x^2 + b*x + c + d*y + e*y^2", {"a": a, "b": b, "c": c, "d": dd, "e": e}, response=z, fitted=fitted, metadata={"dimension": 3})


def open_window(parent) -> None:
    ToolWindow(parent)