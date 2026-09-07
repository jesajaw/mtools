"""
Multivariate regression tool: multiple linear regression with two
predictors, z = b0 + b1*x + b2*y, via the general least-squares
normal equations (mathlib.least_squares_fit). Reuses the existing
3-column point format (x, y, z) -- x and y are the two predictor
variables, z is the response.
"""

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Multivariate"
TOOL_DESCRIPTION = "Least-squares multiple linear regression: z = b0 + b1*x + b2*y."


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y or not z:
        raise ValueError(
            "Multivariate fit needs (x, y, z) triples -- two predictors (x, y) and a response (z)."
        )
    design = [[1.0, xi, yi] for xi, yi in zip(x, y)]
    b0, b1, b2 = t.least_squares_fit(design, z)
    return b0, b1, b2, d


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        b0, b1, b2, d = result
        return f"b0 = {b0:.6g}\nb1 = {b1:.6g}\nb2 = {b2:.6g}\ndimension = {d}\n"


def open_window(parent) -> None:
    ToolWindow(parent)
