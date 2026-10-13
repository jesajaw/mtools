"""
Confidence intervals for the workspace data. Pick the quantity with the Interval cell and enter the confidence level (0.95, 95 or 95% all work):

- Mean (t)                 unknown sigma, Student t with n-1 df -- every column
- Mean (z, known sigma)    sigma entered below, normal quantile -- every column
- Variance / std dev       chi-square interval, assumes normally distributed data -- every column
- Proportion (Wilson)      for columns that only contain 0 and 1 (1 = success); other columns are skipped
- Median                   distribution-free, from order statistics via the binomial distribution; the achieved coverage is >= the requested level and is reported
- Mean difference (Welch)  A - B for two independent samples, unequal variances
- Linear fit parameters    slope a and intercept b of the least-squares line y = a*x + b (columns x, y), t with n-2 df

The Welch interval reads sample A and B from the columns x and y, or -- with the Samples cell set to "grouped" -- from one value column x and a group label in y (A is the group with the smaller label). Several columns are shown side by side as one table.
"""

import math

from . import _basic as b
from . import _dist as dist
from . import _ui
from data import results
from ui.widgets import ComputeToolWindow, ParameterBox

TOOL_NAME = "Confidence Intervals"
TOOL_DESCRIPTION = "Confidence intervals for a mean (t or z), variance, proportion, median, a difference of means and the parameters of a linear fit."
TOOL_INSTRUCTIONS = "Click the cells to pick the interval and (for the difference of means) the sample layout, enter the confidence level (and sigma for the z-interval), load the data via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "estimate, standard error,\nlower and upper bound of the interval"

INTERVALS = [
    ("mean_t", "Mean (t)"),
    ("mean_z", "Mean (z, known sigma)"),
    ("variance", "Variance / std dev (chi-square)"),
    ("proportion", "Proportion (Wilson)"),
    ("median", "Median (order statistics)"),
    ("diff", "Mean difference (Welch)"),
    ("linear", "Linear fit parameters"),
]


def mean_t(values, level: float) -> dict:
    n = len(values)
    if n < 2:
        raise ValueError("A t-interval needs at least 2 values per column.")
    m, s = b.mean(values), b.std(values)
    se = s / math.sqrt(n)
    half = dist.StudentT(n - 1).ppf(1 - (1 - level) / 2) * se
    return {"n": n, "mean": m, "std error": se, "lower": m - half, "upper": m + half, "margin": half}


def mean_z(values, level: float, sigma: float) -> dict:
    n = len(values)
    m = b.mean(values)
    se = sigma / math.sqrt(n)
    half = dist.norm_ppf(1 - (1 - level) / 2) * se
    return {"n": n, "mean": m, "std error": se, "lower": m - half, "upper": m + half, "margin": half}


def variance_interval(values, level: float) -> dict:
    n = len(values)
    if n < 2:
        raise ValueError("A variance interval needs at least 2 values per column.")
    s2 = b.variance(values)
    alpha = 1 - level
    chi = dist.ChiSquare(n - 1)
    low, high = (n - 1) * s2 / chi.ppf(1 - alpha / 2), (n - 1) * s2 / chi.ppf(alpha / 2)
    return {"n": n, "variance": s2, "var lower": low, "var upper": high, "std dev": math.sqrt(s2), "sd lower": math.sqrt(low), "sd upper": math.sqrt(high)}


def wilson(values, level: float) -> dict:
    n = len(values)
    k = int(sum(values))
    p = k / n
    z = dist.norm_ppf(1 - (1 - level) / 2)
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"n": n, "successes": k, "proportion": p, "lower": max(0.0, centre - half), "upper": min(1.0, centre + half)}


def median_interval(values, level: float) -> dict:
    n = len(values)
    ordered = sorted(values)
    tail = (1 - level) / 2
    binom = dist.Binomial(n, 0.5)
    # largest rank l (1-based) with P(B <= l-1) <= tail; the interval is [x_(l), x_(n-l+1)]
    low, high, best = 1, (n + 1) // 2, 0
    while low <= high:
        mid = (low + high) // 2
        if binom.cdf(mid - 1) <= tail:
            best, low = mid, mid + 1
        else:
            high = mid - 1
    if best == 0:
        raise ValueError(f"n = {n} is too small for a {level:.0%} median interval -- use more data or a lower level.")
    upper_rank = n - best + 1
    return {"n": n, "median": b.quantile(ordered, 0.5), "lower": ordered[best - 1], "upper": ordered[upper_rank - 1], "ranks (l, u)": f"{best}, {upper_rank}", "coverage": 1 - 2 * binom.cdf(best - 1)}


def welch_difference(a, b_, level: float) -> dict:
    n1, n2 = len(a), len(b_)
    if n1 < 2 or n2 < 2:
        raise ValueError("The Welch interval needs at least 2 values per sample.")
    v1, v2 = b.variance(a), b.variance(b_)
    se2 = v1 / n1 + v2 / n2
    if se2 == 0:
        raise ValueError("Both samples are constant -- the interval is degenerate.")
    se = math.sqrt(se2)
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    diff = b.mean(a) - b.mean(b_)
    half = dist.StudentT(df).ppf(1 - (1 - level) / 2) * se
    return {"n (A)": n1, "n (B)": n2, "mean (A)": b.mean(a), "mean (B)": b.mean(b_), "difference": diff, "std error": se, "df": df, "lower": diff - half, "upper": diff + half}


def linear_parameters(x, y, level: float) -> dict:
    n = len(x)
    if n < 3:
        raise ValueError("Intervals for a linear fit need at least 3 points.")
    mx, my = b.mean(x), b.mean(y)
    sxx = math.fsum((v - mx) ** 2 for v in x)
    if sxx == 0:
        raise ValueError("All x-values are identical -- the slope is undefined.")
    slope = math.fsum((u - mx) * (v - my) for u, v in zip(x, y)) / sxx
    intercept = my - slope * mx
    sse = math.fsum((v - (slope * u + intercept)) ** 2 for u, v in zip(x, y))
    s2 = sse / (n - 2)
    sst = math.fsum((v - my) ** 2 for v in y)
    t = dist.StudentT(n - 2).ppf(1 - (1 - level) / 2)
    se_slope, se_intercept = math.sqrt(s2 / sxx), math.sqrt(s2 * (1 / n + mx * mx / sxx))
    return {
        None: {"n": n, "df": n - 2, "R^2": 1 - sse / sst if sst > 0 else None},
        "slope (a)": {"estimate": slope, "std error": se_slope, "lower": slope - t * se_slope, "upper": slope + t * se_slope},
        "intercept (b)": {"estimate": intercept, "std error": se_intercept, "lower": intercept - t * se_intercept, "upper": intercept + t * se_intercept},
    }


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._interval, self._layout = "mean_t", "columns"
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, INTERVALS, "Interval: ", self._on_interval_change)
        _ui.samples_cell(parent, lambda key: setattr(self, "_layout", key))

        self.box = ParameterBox(parent, "Parameters")
        self.box.pack(fill="x", pady=(0, 8))
        self.box.add("level", "Confidence level", "0.95")
        self.box.add("sigma", "Known sigma (z-interval)", "1")
        self.box.set_enabled("sigma", False)

    def _on_interval_change(self, key: str) -> None:
        self._interval = key
        self.box.set_enabled("sigma", key == "mean_z")

    def compute(self, dataset):
        cols = b.columns(dataset)
        kind = self._interval
        level = b.parse_probability(self.box.get("level"), "confidence level")
        label = dict(INTERVALS)[kind]
        extra = ""

        if kind == "mean_t":
            groups = {name: mean_t(v, level) for name, v in cols.items()}
        elif kind == "mean_z":
            sigma = b.parse_float(self.box.get("sigma"), "sigma")
            if not sigma > 0:
                raise ValueError("Known sigma must be > 0.")
            groups = {name: mean_z(v, level, sigma) for name, v in cols.items()}
            extra = f", sigma = {sigma:g}"
        elif kind == "variance":
            groups = {name: variance_interval(v, level) for name, v in cols.items()}
        elif kind == "proportion":
            groups = {name: wilson(v, level) for name, v in cols.items() if all(u in (0.0, 1.0) for u in v)}
            if not groups:
                raise ValueError("No column contains only 0 and 1 -- a proportion interval needs success/failure data (1 = success).")
        elif kind == "median":
            groups = {name: median_interval(v, level) for name, v in cols.items()}
        elif kind == "diff":
            a, b_, la, lb = b.two_samples(cols, grouped=self._layout == "grouped")
            groups = {None: welch_difference(a, b_, level)}
            extra = f", A = {la}, B = {lb}"
        else:  # linear
            if "x" not in cols or "y" not in cols:
                raise ValueError("Linear fit intervals need two columns (x, y).")
            groups = linear_parameters(cols["x"], cols["y"], level)

        title = f"{level * 100:.4g}% confidence interval: {label}{extra}"
        return results.stats_dataset(dataset, TOOL_NAME, title, groups, metadata={"interval": kind, "level": level})


def open_window(parent) -> None:
    ToolWindow(parent)
