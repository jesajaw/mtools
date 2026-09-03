"""
Linear regression tool. Wraps the existing process() logic unchanged: 2D does a least-squares slope/intercept fit; 3D fits a best-fit
line through the point cloud via covariance + power iteration (PCA, first principal component).
"""

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Linear"
TOOL_DESCRIPTION = "Least-squares line fit (2D) or best-fit line via PCA (3D)."


def _fit_2d(n, x, y):
    """Ordinary least-squares slope/intercept fit, minimizing vertical (y) residuals."""
    slope = (
        n * t.sum_list(t.products(x, y)) - t.sum_list(x) * t.sum_list(y)
    ) / (n * t.sum_list(t.square(x)) - t.sum_list(x) ** 2)
    cx, cy = t.mean([x, y])
    intercept = cy - slope * cx
    return slope, intercept


def _fit_3d(x, y, z):
    """Best-fit line through the point cloud (PCA, dominant eigenvector of the
    covariance/scatter matrix), minimizing perpendicular distance to the line."""
    cx, cy, cz = t.mean([x, y, z])
    field = t.shift([x, y, z], [cx, cy, cz])
    cov = [[t.scatter(a, b) for b in field] for a in field]
    direction = t.power_iteration(cov)
    return (cx, cy, cz), direction


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if not z:
        slope, intercept = _fit_2d(n, x, y)
        return slope, intercept, d, (x, y)
    center, direction = _fit_3d(x, y, z)
    return center, direction, d, (x, y, z)


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        if len(result) == 4 and isinstance(result[0], (int, float)):
            slope, intercept, d, _ = result
            return f"slope = {slope:.6g}\nintercept = {intercept:.6g}\ndimension = {d}\n"
        center, direction, d, _ = result
        return (
            f"center = {tuple(round(v, 6) for v in center)}\n"
            f"direction = {tuple(round(v, 6) for v in direction)}\n"
            f"dimension = {d}\n"
        )


def open_window(parent) -> None:
    ToolWindow(parent)