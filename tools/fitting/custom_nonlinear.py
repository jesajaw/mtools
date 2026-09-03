"""
Custom non-linear curve fitting tool. Fits an arbitrary user-supplied
model y = f(x; p1, p2, ...) via damped Gauss-Newton (Levenberg-
Marquardt) least squares, using a numerical (finite-difference)
Jacobian -- no closed-form derivative needed from the user. The model
formula is plain Python syntax with `x` plus the named parameters in
scope, and the functions/constants from the `math` module available
(sin, cos, exp, log, sqrt, pi, ...).
"""

import math

import tools.mathlib as t
from theme.widgets import ComputeToolWindow

TOOL_NAME = "Custom Non-linear Fit"
TOOL_DESCRIPTION = "Fit an arbitrary user-defined model y = f(x; params) via Levenberg-Marquardt."

# Formula evaluation namespace: math functions/constants plus a
# couple of harmless builtins, nothing else -- no access to __builtins__.
_ALLOWED_NAMES = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
_ALLOWED_NAMES.update({"abs": abs, "min": min, "max": max})


def _parse_names(text: str) -> list:
    names = [n.strip() for n in text.split(",") if n.strip()]
    if not names:
        raise ValueError("Enter at least one parameter name.")
    for n in names:
        if not n.isidentifier():
            raise ValueError(f"'{n}' is not a valid parameter name.")
    if "x" in names:
        raise ValueError("'x' is reserved for the independent variable -- pick another parameter name.")
    return names


def _parse_floats(text: str, expected: int, what: str) -> list:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    try:
        values = [float(p.replace(",", ".")) for p in parts]
    except ValueError:
        raise ValueError(f"Could not parse {what} as numbers.")
    if len(values) != expected:
        raise ValueError(f"Expected {expected} {what}, got {len(values)}.")
    return values


def make_model(expression: str, param_names: list):
    """Compiles the formula once; returns f(x, params) -> y."""
    code = compile(expression, "<model>", "eval")

    def f(x, params):
        local_ns = dict(zip(param_names, params))
        local_ns["x"] = x
        return eval(code, {"__builtins__": {}, **_ALLOWED_NAMES}, local_ns)

    return f


def fit_nonlinear(f, x, y, p0, iterations=200, lambda_init=1e-3):
    """Damped Gauss-Newton (Levenberg-Marquardt) least squares fit of
    f(x, params) to (x, y), with a numerical (forward-difference)
    Jacobian. Returns (params, sum_of_squared_residuals)."""
    p = list(p0)
    n, m = len(x), len(p)

    def residuals(params):
        return [y[i] - f(x[i], params) for i in range(n)]

    def jacobian(params, base):
        eps = 1e-6
        J = [[0.0] * m for _ in range(n)]
        for j in range(m):
            step = eps * max(1.0, abs(params[j]))
            bumped = list(params)
            bumped[j] += step
            res_bumped = residuals(bumped)
            for i in range(n):
                J[i][j] = -(res_bumped[i] - base[i]) / step
        return J

    base = residuals(p)
    cost = t.sum_list(t.square(base))
    lam = lambda_init

    for _ in range(iterations):
        J = jacobian(p, base)
        JtJ = [[sum(J[k][i] * J[k][j] for k in range(n)) for j in range(m)] for i in range(m)]
        Jtr = [sum(J[k][i] * base[k] for k in range(n)) for i in range(m)]

        improved = False
        for _attempt in range(30):
            A = [[JtJ[i][j] + (lam * JtJ[i][i] if i == j else 0.0) for j in range(m)] for i in range(m)]
            try:
                delta = t.solve_gauss(A, Jtr)
            except ValueError:
                lam *= 10
                continue
            p_new = [p[i] + delta[i] for i in range(m)]
            res_new = residuals(p_new)
            cost_new = t.sum_list(t.square(res_new))
            if cost_new < cost:
                p, base, cost = p_new, res_new, cost_new
                lam = max(lam / 10, 1e-12)
                improved = True
                break
            lam *= 10
        if not improved:
            break  # converged, or stuck -- either way, stop iterating

    return p, cost


class ToolWindow(ComputeToolWindow):
    default_size = "480x540"

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def _build_extra(self, parent) -> None:
        from tkinter import ttk

        box = ttk.LabelFrame(parent, text="Model", padding=10)
        box.pack(fill="x", pady=(0, 8))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="y = f(x; params) =", style="Status.TLabel").grid(
            row=0, column=0, sticky="w")
        self.formula_entry = ttk.Entry(box)
        self.formula_entry.insert(0, "a*exp(b*x) + c")
        self.formula_entry.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(box, text="Parameters (comma-separated)", style="Status.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 0))
        self.params_entry = ttk.Entry(box)
        self.params_entry.insert(0, "a, b, c")
        self.params_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))

        ttk.Label(box, text="Initial guess (comma-separated)", style="Status.TLabel").grid(
            row=2, column=0, sticky="w", pady=(6, 0))
        self.guess_entry = ttk.Entry(box)
        self.guess_entry.insert(0, "1, 1, 1")
        self.guess_entry.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))

    def compute(self, data):
        n, d, x, y, z = t.split_points(data)
        if not y:
            raise ValueError("Custom non-linear fit needs (x, y) pairs, not a single column.")
        if z:
            raise ValueError("Custom non-linear fit only supports 2D data (x, y).")

        param_names = _parse_names(self.params_entry.get())
        p0 = _parse_floats(self.guess_entry.get(), len(param_names), "initial guesses")
        expression = self.formula_entry.get().strip()
        if not expression:
            raise ValueError("Enter a model formula.")

        f = make_model(expression, param_names)
        try:
            f(x[0], p0)
        except Exception as e:
            raise ValueError(f"Could not evaluate the formula: {e}")

        params, cost = fit_nonlinear(f, x, y, p0)
        return param_names, params, cost, d

    def format_result(self, result) -> str:
        param_names, params, cost, d = result
        lines = [f"{name} = {value:.6g}" for name, value in zip(param_names, params)]
        lines.append(f"sum of squared residuals = {cost:.6g}")
        lines.append(f"dimension = {d}")
        return "\n".join(lines) + "\n"


def open_window(parent) -> None:
    ToolWindow(parent)
