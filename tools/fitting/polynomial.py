"""
Polynomial (quadratic) regression tool. 2D branch (process() below)
is the working normal-equations quadratic fit y = c0 + c1*x + c2*x^2.
The 3D branch is carried over unchanged from the original script and
is not finished yet -- see the NOTE inside process().
"""

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Polynomial"
TOOL_DESCRIPTION = "Quadratic least-squares fit y = c0 + c1*x + c2*x^2 (2D)."


def process(points):
    n, d, x, y, z = t.split_points(points)
    if not y:
        y = list(range(n))
    if not z:
        A = t.normal_matrix(x)
        b = t.normal_equation_vector(x, y)
        return t.solve_3_3_Gauss(A, b)
    else:
        # NOTE: carried over unchanged from the original script.
        # t.mean(...) below is called with 3 separate list arguments,
        # but mean() only accepts one list-of-lists argument -- this
        # branch raises a TypeError until that's fixed on the
        # mathlib/script side. The GUI will show that error instead
        # of crashing, but the 3D case isn't usable yet.
        (cx, cy, cz) = t.mean([x, y, z])
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((t.distance((x[i], y[i], z[i]), (x[j], y[j], z[j])), i, j))
        pairs.sort(reverse=True, key=lambda p: p[0])
        mean_extreme_distance = t.mean([pairs[i][0] for i in range(3)])
        mean_extreme_pair = t.mean(
            [x[pairs[i][j]] for i in range(3) for j in (1, 2)],
            [y[pairs[i][j]] for i in range(3) for j in (1, 2)],
            [z[pairs[i][j]] for i in range(3) for j in (1, 2)],
        )
        return mean_extreme_pair


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        return process(data)

    def format_result(self, result) -> str:
        if isinstance(result, list) and len(result) == 3 and all(isinstance(v, (int, float)) for v in result):
            c0, c1, c2 = result
            return f"c0 = {c0:.6g}\nc1 = {c1:.6g}\nc2 = {c2:.6g}\n"
        return str(result)


def open_window(parent) -> None:
    ToolWindow(parent)
