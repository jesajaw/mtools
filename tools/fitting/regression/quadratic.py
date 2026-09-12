"""
Quadratic regression tool: y = a*x^2 + b*x + c (2D), or z = a*x^2 + b*x + c + d*y + e*y^2 (3D) -- the same quadratic structure applied to x, and additively to y too, no cross term (no x*y). This is the same fit as Polynomial's degree=2 case (tools/fitting/regression/polynomial.py) -- Quadratic just exposes it under the conventional a/b/c/d/e naming at a fixed degree, while Polynomial covers any degree. Reuses polynomial._fit_2d()/ _fit_3d_surface() instead of duplicating the math.
"""

from . import _points, polynomial
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Quadratic"
TOOL_DESCRIPTION = "Least-squares quadratic fit: y = a*x^2 + b*x + c (2D), or z = a*x^2 + b*x + c + d*y + e*y^2 (3D)."
TOOL_INSTRUCTIONS = "Load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = a*x^2 + b*x + c  \n  z = a*x^2 + b*x + c + d*y + e*y^2"


def process(data):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y:
            y = list(range(n))
        if not z:
            c0, c1, c2 = polynomial._fit_2d(x, y, 2)
            return False, (c2, c1, c0)  # a, b, c
        c0, cx1, cx2, cy1, cy2 = polynomial._fit_3d_surface(x, y, z, 2)
        return True, (cx2, cx1, c0, cy1, cy2)  # a, b, c, d, e
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, data) -> dict:
        result = process(data)
        if isinstance(result, Exception):
            return {"error": str(result)}
        is_3d, coeffs = result
        if not is_3d:
            a, b, c = coeffs
            return {"name": TOOL_NAME, "a": a, "b": b, "c": c}
        a, b, c, d, e = coeffs
        return {"name": TOOL_NAME, "a": a, "b": b, "c": c, "d": d, "e": e}

    def format_result(self, result: dict) -> str:
        if "error" in result:
            return result["error"]
        return "\n".join(f"{k} = {v:.6g}" for k, v in result.items() if k != "name") + "\n"


def open_window(parent) -> None:
    ToolWindow(parent)