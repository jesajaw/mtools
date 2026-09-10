import tools.mathlib as t
from . import _points
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Linear Regression"
TOOL_DESCRIPTION = "Linear line fit for 2D or 3D data."
TOOL_INSTRUCTIONS = "Load (x), (x, y) or (x, y, z) points via the main window (see format hints, datalabel should show you, that youre data is valid), then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = a*x + b || z = a + b*x + c*y"

def _fit_3d(x, y, z):
    cx, cy, cz = t.mean([x, y, z]) # center
    field = t.shift([x, y, z], [cx, cy, cz]) # shift to get maximum of variance instead of the largest eigenvalue
    return (t.power_iteration(
                [[t.scatter(a, b)
                  for b in field] for a in field # dominant eigenvector via covariance/scatter matrix, minimizing perpendicular distance to the line
                  ]), (cx, cy, cz))


def _fit_2d(n, x, y):
    slope = (n * t.sum_list(t.products(x, y)) - t.sum_list(x) * t.sum_list(y)) / (n * t.sum_list(t.square(x)) - t.sum_list(x) ** 2)  # ordinary least-squares slope/intercept fit
    cx, cy = t.mean([x, y])  # center
    return (slope, (cy - slope * cx))


def process(data):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y:
            y = list(range(n))
        if not z:
            return _fit_2d(n, x, y), d, (x, y)
        return _fit_3d(x, y, z), d, (x, y, z)
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, data) -> dict:
        result = process(data)
        if isinstance(result, Exception):
            return {"error": str(result)}
        (direction, point), d, points = result
        return {
            "name": TOOL_NAME,
            "dimension": d,
            "direction": direction,
            "point": point,
            "points": points
        }


def open_window(parent) -> None:
    ToolWindow(parent)