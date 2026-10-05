import tools.mathlib as t
from . import _points
from data import results
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Linear"
TOOL_DESCRIPTION = "Linear line fit for 2D or 3D data."
TOOL_INSTRUCTIONS = "Load (x), (x, y) or (x, y, z) points via the main window (see format hints, datalabel should show you, that youre data is valid), then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = a*x + b \n (x, y, z): line  p + s*d"

def _fit_3d(x, y, z):
    cx, cy, cz = t.mean([x, y, z]) # center
    field = t.shift([x, y, z], [cx, cy, cz]) # shift to get maximum of variance instead of the largest eigenvalue
    return (t.power_iteration(
                [[t.scatter(a, b)
                  for b in field] for a in field # dominant eigenvector via covariance/scatter matrix, minimizing perpendicular distance to the line
                  ]), (cx, cy, cz))


def _fit_2d(n, x, y):
    denom = n * t.sum_list(t.square(x)) - t.sum_list(x) ** 2
    if denom == 0:
        raise ValueError("All x-values are identical -- the slope is undefined.")
    slope = (n * t.sum_list(t.products(x, y)) - t.sum_list(x) * t.sum_list(y)) / denom  # ordinary least-squares slope/intercept fit
    cx, cy = t.mean([x, y])  # center
    return (slope, (cy - slope * cx))


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, dataset):
        n, d, x, y, z = _points.split_data(dataset)
        if not y:
            y = list(range(n))
        if not z:
            a, b = _fit_2d(n, x, y)
            return results.fit_dataset(dataset, TOOL_NAME, "y = a*x + b", {"a": a, "b": b}, response=y, fitted=[a * xi + b for xi in x], metadata={"dimension": 2})

        (dx, dy, dz), (px, py, pz) = _fit_3d(x, y, z)  # orthogonal line fit: point p, direction d
        fitted, distance = [], []
        for xi, yi, zi in zip(x, y, z):
            s = (xi - px) * dx + (yi - py) * dy + (zi - pz) * dz  # foot of the perpendicular on the line
            foot = (px + s * dx, py + s * dy, pz + s * dz)
            fitted.append(foot[2])
            distance.append(t.distance((xi, yi, zi), foot))
        params = {"px": px, "py": py, "pz": pz, "dx": dx, "dy": dy, "dz": dz}
        return results.fit_dataset(dataset, TOOL_NAME, "line: p + s*d", params, response=z, fitted=fitted, residual=distance, residual_kind="perpendicular", metadata={"dimension": 3})


def open_window(parent) -> None:
    ToolWindow(parent)