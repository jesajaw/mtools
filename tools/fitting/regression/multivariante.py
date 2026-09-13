"""
Multivariate regression tool: multiple linear regression with two predictors, z = b0 + b1*x + b2*y, via the general least-squares normal equations. Reuses the existing 3-column point format (x, y, z) -- x and y are the two predictor variables, z is the response. No mode picker and no 2D/3D auto- detection here (unlike the other fitting tools): the point loader only ever supplies up to 3 columns, so (x, y, z) triples are the only shape this tool can meaningfully operate on -- there's no alternative form of the data to choose between.
"""

import tools.mathlib as t
from . import _points
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Multivariate"
TOOL_DESCRIPTION = "Least-squares multiple linear regression: z = b0 + b1*x + b2*y."
TOOL_INSTRUCTIONS = "Load (x, y, z) triples via the main window -- two predictors (x, y) and a response (z), then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "z = b0 + b1*x + b2*y"


def process(data):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y or not z:
            raise ValueError("Multivariate fit needs (x, y, z) triples -- you may use Linear Regression.")
        design = [[1.0, xi, yi] for xi, yi in zip(x, y)]
        b0, b1, b2 = t.least_squares_fit(design, z)
        return b0, b1, b2
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def compute(self, data) -> dict:
        result = process(data)
        if isinstance(result, Exception):
            return {"error": str(result)}
        b0, b1, b2 = result
        return {"name": TOOL_NAME, "b0": b0, "b1": b1, "b2": b2}

    def format_result(self, result: dict) -> str:
        if "error" in result:
            return result["error"]
        return "\n".join(f"{k} = {v:.6g}" for k, v in result.items() if k != "name") + "\n"


def open_window(parent) -> None:
    ToolWindow(parent)