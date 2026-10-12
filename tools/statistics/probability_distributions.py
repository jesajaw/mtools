"""
Probability distributions: pick a distribution with the Distribution cell, enter its parameters, and optionally a point x and a probability p:

- the distribution's mean, variance and standard deviation,
- for x: density (pdf, or pmf for discrete distributions), P(X <= x) and P(X > x),
- for p: the quantile, i.e. the x with P(X <= x) = p (discrete: the smallest integer with P(X <= x) >= p).

Distributions: Normal(mu, sigma), Student t(df), Chi-square(df), F(d1, d2), Exponential(lambda = rate), Uniform(a, b), Gamma(k = shape, theta = scale), Beta(a, b), Binomial(n, p), Poisson(lambda).

Works without loaded data. The result also carries curve data for later plotting: the pdf and cdf evaluated at every x of the loaded data -- or, if nothing is loaded, on an automatic grid covering the bulk of the distribution (a row of integers for discrete ones). The loaded data is not modified; the result becomes a new workspace entry.
"""

import math

from . import _basic as b
from . import _dist as dist
from . import _ui
from data import results
from data.dataset import DataArray
from ui.widgets import ComputeToolWindow, ParameterBox

TOOL_NAME = "Probability Distributions"
TOOL_DESCRIPTION = "Density, cumulative probability and quantiles of common distributions (Normal, t, Chi-square, F, Exponential, Uniform, Gamma, Beta, Binomial, Poisson)."
TOOL_INSTRUCTIONS = "Click the Distribution cell to pick a distribution, enter its parameters and optionally x (probabilities) and p (quantile), then click Compute. Loaded x-values are used as evaluation points for the pdf/cdf curve, otherwise a grid is generated -- save or visualize as you wish."
RESULT_FORMAT = "mean, variance, std dev\npdf(x), P(X <= x), P(X > x)\nquantile(p)"

GRID_POINTS = 101
MAX_DISCRETE_POINTS = 400


def _grid(d: dist.Distribution) -> list[float]:
    # evaluation grid covering the bulk of the distribution
    if d.discrete:
        lo, hi = int(d.ppf(0.0005)), int(d.ppf(0.9995))
        hi = max(hi, lo + 1)
        step = max(1, math.ceil((hi - lo) / MAX_DISCRETE_POINTS))
        return [float(k) for k in range(lo, hi + 1, step)]
    low, high = d.support()
    lo = low if low is not None else d.ppf(0.001)
    hi = high if high is not None else d.ppf(0.999)
    return [lo + (hi - lo) * i / (GRID_POINTS - 1) for i in range(GRID_POINTS)]


class ToolWindow(ComputeToolWindow):
    requires_data = False
    data_hint = "No data loaded -- an automatic grid is used (or load x-values to evaluate at)."

    def __init__(self, parent):
        self._key = next(iter(dist.DISTRIBUTIONS))
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, [(key, cls.label) for key, cls in dist.DISTRIBUTIONS.items()], "Distribution: ", self._on_distribution_change)

        self.box = ParameterBox(parent, "Parameters")
        self.box.pack(fill="x", pady=(0, 8))
        self.box.add("params", "", "")
        self.box.add("x", "x  (pdf, P(X <= x), P(X > x))", "")
        self.box.add("p", "p  (quantile)", "0.95")
        self._apply_distribution(self._key)

    def _on_distribution_change(self, key: str) -> None:
        self._key = key
        self._apply_distribution(key)

    def _apply_distribution(self, key: str) -> None:
        cls = dist.DISTRIBUTIONS[key]
        self.box.set_label("params", f"Parameters ({', '.join(cls.param_names)})")
        self.box.set("params", ", ".join(cls.param_defaults))
        self.box.set("x", cls.x_default)

    def compute(self, dataset):
        d = dist.create(self._key, dist.parse_params(self.box.get("params")))
        stats = {"distribution": d.describe()}

        mean, var = d.mean(), d.variance()
        stats["mean"] = mean
        stats["variance"] = var
        stats["std dev"] = None if var is None else math.sqrt(var)

        x_text, p_text = self.box.get("x").strip(), self.box.get("p").strip()
        if x_text:
            x = b.parse_float(x_text, "x")
            stats[f"{d.density_name}({x:g})"] = d.pdf(x)
            stats[f"P(X <= {x:g})"] = d.cdf(x)
            stats[f"P(X > {x:g})"] = d.sf(x)
        if p_text:
            p = b.parse_probability(p_text, "p")
            stats[f"quantile({p:g})"] = d.ppf(p)

        if dataset is not None:  # evaluate at the loaded x-values; the input coordinates are carried over by stats_dataset
            xs = b.columns(dataset)["x"] if "x" in dataset.axes else None
            if xs is None:
                raise ValueError("The loaded data has no x column to evaluate the distribution at.")
        else:
            xs = _grid(d)

        arrays = [
            DataArray(values=[d.pdf(v) for v in xs], name=d.density_name, label="Probability mass" if d.discrete else "Probability density"),
            DataArray(values=[d.cdf(v) for v in xs], name="cdf", label="Cumulative probability"),
        ]
        result = results.stats_dataset(dataset, TOOL_NAME, d.describe(), {None: stats}, arrays=arrays, metadata={"distribution": self._key, "parameters": list(d.params)})
        if dataset is None:
            result.axes["x"] = DataArray(values=xs, name="x", label="x")
        return result


def open_window(parent) -> None:
    ToolWindow(parent)
