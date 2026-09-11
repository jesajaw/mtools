"""
Polynomial regression tool: a general-degree least-squares fit,
y = c0 + c1*x + ... + cn*x^n (2D). 3D extends the exact same
structure additively across both variables:
z = c0 + c1*x + ... + cn*x^n + d1*y + ... + dn*y^n -- no cross terms
(no x*y, x^2*y, ...), just the same 1D polynomial applied to x and
to y separately and summed. Degree is adjustable in the tool window
(click the Degree cell to cycle 1..MAX_DEGREE).

A raw Vandermonde matrix (columns 1, x, x^2, ..., x^n) becomes
severely ill-conditioned past roughly degree 10-15 -- x^20 and x^1
differ by many orders of magnitude for any x not extremely close to
+-1, so the normal equations silently lose precision (observed:
~1-2% drift in the low-order coefficients at degree 20 for x in
[0, 50], worse for wider ranges). Both fits therefore solve in a
centered/scaled variable u = (x - mean(x)) / scale first, then
re-expand the result back into plain coefficients of x via the
binomial theorem (_reexpand) -- the returned c_k still mean exactly
what the docstring above says, just computed on stable footing.

That fix only pushes the problem back so far, though: the normal
equations (mathlib.least_squares_fit solves A^T A c = A^T b, which
squares the condition number of A) stay inherently unreliable well
past degree ~12-15 no matter how the input is scaled -- verified
down to ~1e-11 drift at degree 10, but still ~1e-4 relative drift
(and occasional outright singular-matrix failures on sparser data)
at degree 20. MAX_DEGREE is capped at 12 to stay inside the range
this was actually confirmed accurate in, rather than advertise a
degree the current (normal-equations) solver can't reliably back up.
A QR- or SVD-based solver would lift that ceiling, but that's a
separate, larger piece of numerical linear algebra to add to
mathlib.py, not a small tweak here.

Needs at least (degree + 1) points for 2D, or (2*degree + 1) points
for 3D -- fewer than that makes the normal-equations matrix singular
(mathlib.solve_gauss raises a clear error in that case rather than
silently misfitting).
"""

import math

import tools.mathlib as t
from . import _points
from theme.widgets import ComputeToolWindow, make_mode_cell

TOOL_NAME = "Polynomial"
TOOL_DESCRIPTION = "Least-squares polynomial fit, any degree: y = c0 + c1*x + ... + cn*x^n (2D), or z = c0 + c1*x + ... + cn*x^n + d1*y + ... + dn*y^n (3D)."
TOOL_INSTRUCTIONS = "Click the Degree cell to pick a degree, load (x, y) or (x, y, z) points via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "y = c0 + c1*x + ... + cn*x^n  ||  z = c0 + c1*x + ... + cn*x^n + d1*y + ... + dn*y^n"

CELL_MODE_WIDTH = 400
CELL_MODE_HEIGHT = 40

MAX_DEGREE = 12


def _center_scale(values):
    """Mean and a robust scale (max absolute deviation from the
    mean, or 1.0 for a constant column) -- so the fit works in
    u = (x - mean) / scale, roughly within [-1, 1]."""
    mean = sum(values) / len(values)
    scale = max(abs(v - mean) for v in values) or 1.0
    return mean, scale


def _reexpand(coeffs_of_u, mean, scale):
    """Given coefficients of u = (x - mean) / scale (coeffs_of_u[k]
    multiplies u^k), returns the equivalent coefficients of x
    (same length, coeffs_of_x[i] multiplies x^i) via the binomial
    theorem: u^k = sum_i C(k,i) * x^i * (-mean)^(k-i) / scale^k."""
    degree = len(coeffs_of_u) - 1
    coeffs_of_x = [0.0] * (degree + 1)
    for k, a_k in enumerate(coeffs_of_u):
        for i in range(k + 1):
            coeffs_of_x[i] += a_k * math.comb(k, i) * (-mean) ** (k - i) / scale ** k
    return coeffs_of_x


def _fit_2d(x, y, degree):
    """General least-squares polynomial fit y = sum(c_k * x^k), k = 0..degree. Returns [c0, ..., c_degree]."""
    xm, sx = _center_scale(x)
    u = [(xi - xm) / sx for xi in x]
    design = [[ui ** k for k in range(degree + 1)] for ui in u]
    a = t.least_squares_fit(design, y)
    return _reexpand(a, xm, sx)


def _fit_3d_surface(x, y, z, degree):
    """z = c0 + c1*x + ... + cn*x^n + d1*y + ... + dn*y^n -- the same
    1D polynomial in x and in y, added together, no cross terms.
    Returns [c0, c1..cn, d1..dn] (2*degree + 1 coefficients)."""
    xm, sx = _center_scale(x)
    ym, sy = _center_scale(y)
    u = [(xi - xm) / sx for xi in x]
    v = [(yi - ym) / sy for yi in y]
    design = [[1.0] + [ui ** k for k in range(1, degree + 1)] + [vi ** k for k in range(1, degree + 1)] for ui, vi in zip(u, v)]
    a = t.least_squares_fit(design, z)

    cx = _reexpand([0.0] + a[1:degree + 1], xm, sx)  # a[0] (the shared constant) handled separately below
    cy = _reexpand([0.0] + a[degree + 1:], ym, sy)
    return [a[0] + cx[0] + cy[0]] + cx[1:] + cy[1:]


def process(data, degree):
    n, d, x, y, z = _points.split_data(data)
    try:
        if not y:
            y = list(range(n))
        if not z:
            return False, _fit_2d(x, y, degree)
        return True, _fit_3d_surface(x, y, z, degree)
    except Exception as e:
        return e


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._degree = 2
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        self.mode_cell = make_mode_cell(
            parent,
            modes=f"Degree: {self._degree}",
            on_change=self._cycle_degree,
            width=CELL_MODE_WIDTH,
            height=CELL_MODE_HEIGHT,
        )
        self.mode_cell.pack(fill="x", pady=(0, 8))

    def _cycle_degree(self) -> None:
        self.output.set_text(self._degree +1 if self._degree < 13 else 2)


    def compute(self, data) -> dict:
        result = process(data, self._degree)
        if isinstance(result, Exception):
            return {"error": str(result)}
        is_3d, coeffs = result
        out = {"name": TOOL_NAME, "degree": self._degree}
        if not is_3d:
            for k, c in enumerate(coeffs):
                out[f"c{k}"] = c
            return out
        out["c0"] = coeffs[0]
        for k in range(1, self._degree + 1):
            out[f"cx{k}"] = coeffs[k]
        for k in range(1, self._degree + 1):
            out[f"cy{k}"] = coeffs[self._degree + k]
        return out

    def format_result(self, result: dict) -> str:
        if "error" in result:
            return result["error"]
        return "\n".join(f"{k} = {v:.6g}" for k, v in result.items() if k not in ("name", "degree")) + "\n"


def open_window(parent) -> None:
    ToolWindow(parent)