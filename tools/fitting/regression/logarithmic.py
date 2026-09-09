"""
Logarithmic regression tool. Three modes, matching the standard distinction (linear-log / log-linear / log-log) between where the
logarithm is applied:
- linear-log: y = a + b*ln(x)      -- only x is logged
- log-linear: ln(y) = a + b*x      -- only y is logged (equivalent to
  an exponential fit, y = e^a * e^(b*x); the "Exponential" tool does
  the same thing under a different name)
- log-log:    ln(y) = a + b*ln(x)  -- both logged (power law,
  y = e^a * x^b)

Interesting: https://articles.outlier.org/logarithmic-regression
"""

import tools.mathlib as t
from . import _points
from theme.widgets import ComputeToolWindow, Cell

TOOL_NAME = "Logarithmic"
TOOL_DESCRIPTION = "Least-squares logarithmic fit -- linear-log, log-linear, or log-log."
TOOL_INSTRUCTIONS = "Click the mode cell below to cycle modes, load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."

_MODE_LABELS = {
    "linear_log": "linear-log: y = a + b*ln(x)",
    "log_linear": "log-linear: ln(y) = a + b*x",
    "log_log": "log-log: ln(y) = a + b*ln(x)",
}
_MODE_ORDER = ["linear_log", "log_linear", "log_log"]

_RESULT_FORMATS = {
    "linear_log": "y = a + b*ln(x)  ||  z = a + b*ln(x) + c*ln(y)",
    "log_linear": "ln(y) = a + b*x  ||  ln(z) = a + b*x + c*y",
    "log_log": "ln(y) = a + b*ln(x)  ||  ln(z) = a + b*ln(x) + c*ln(y)",
}

CELL_MODE_WIDTH = 400
CELL_MODE_HEIGHT = 40

def _require_positive(*columns):
    for col in columns:
        if any(v <= 0 for v in col):
            raise ValueError("This mode requires all logged values to be positive.")


def _fit_line(u, v):
    """Ordinary least-squares line v = a + b*u -- shared by every 2D mode, just fed different (u, v)."""
    n = len(u)
    b = (n * t.sum_list(t.products(u, v)) - t.sum_list(u) * t.sum_list(v)) / (n * t.sum_list(t.square(u)) - t.sum_list(u) ** 2)
    cu, cv = t.mean([u, v])
    a = cv - b * cu
    return a, b


def _fit_plane(u1, u2, v):
    """Ordinary least-squares plane v = a + b*u1 + c*u2 -- shared by every 3D mode."""
    n = len(u1)
    A = [
        [n, t.sum_list(u1), t.sum_list(u2)],
        [t.sum_list(u1), t.sum_list(t.square(u1)), t.sum_list(t.products(u1, u2))],
        [t.sum_list(u2), t.sum_list(t.products(u1, u2)), t.sum_list(t.square(u2))],
    ]
    B = [t.sum_list(v), t.sum_list(t.products(u1, v)), t.sum_list(t.products(u2, v))]
    a, b, c = t.solve_gauss(A, B)
    return a, b, c


def _transform(mode, x, y, z=None):
    """Returns the (u1, u2, v) columns each mode actually fits a
    line/plane through, after checking positivity wherever a log is
    taken."""
    if z is None:
        if mode == "linear_log":
            _require_positive(x)
            return t.log(x), None, y
        if mode == "log_linear":
            _require_positive(y)
            return x, None, t.log(y)
        _require_positive(x, y)  # log_log
        return t.log(x), None, t.log(y)

    if mode == "linear_log":
        _require_positive(x, y)
        return t.log(x), t.log(y), z
    if mode == "log_linear":
        _require_positive(z)
        return x, y, t.log(z)
    _require_positive(x, y, z)  # log_log
    return t.log(x), t.log(y), t.log(z)


def process(data, mode):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y:
            y = list(range(n))
        if not z:
            u, _unused, v = _transform(mode, x, y)
            a, b = _fit_line(u, v)
            return {"name": TOOL_NAME, "mode": mode, "dimension": d, "a": a, "b": b}
        u1, u2, v = _transform(mode, x, y, z)
        a, b, c = _fit_plane(u1, u2, v)
        return {"name": TOOL_NAME, "mode": mode, "dimension": d, "a": a, "b": b, "c": c}
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._mode_index = 0
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=_RESULT_FORMATS[_MODE_ORDER[0]])

    def _build_extra(self, parent) -> None:
        self._mode_cell = Cell(parent, self._mode_title(), on_click=self._cycle_mode, status_text="click to switch mode", width=CELL_MODE_WIDTH, height=CELL_MODE_HEIGHT)
        self._mode_cell.pack(fill="x", pady=(0, 8))

    def _mode_title(self) -> str:
        return f"Mode: {_MODE_LABELS[_MODE_ORDER[self._mode_index]]}"

    def _cycle_mode(self) -> None:
        self._mode_index = (self._mode_index + 1) % len(_MODE_ORDER)
        mode = _MODE_ORDER[self._mode_index]
        self._mode_cell.title_label.configure(text=self._mode_title())
        self.output.set_text(_RESULT_FORMATS[mode])

    def compute(self, data) -> dict:
        mode = _MODE_ORDER[self._mode_index]
        result = process(data, mode)
        if isinstance(result, Exception):
            return {"error": str(result)}
        return result


def open_window(parent) -> None:
    ToolWindow(parent)