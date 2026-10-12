"""
Hypothesis testing on the workspace data. Pick a test with the Test cell, the alternative hypothesis with the Alternative cell, enter the significance level alpha (and, for the t-tests, the hypothesised value mu0):

- One-sample t-test      every column: H0 mean = mu0
- Two-sample t-test      Welch (unequal variances): H0 mean(A) - mean(B) = mu0
- Paired t-test          columns x and y row by row: H0 mean(x - y) = mu0
- Mann-Whitney U test    rank test for two independent samples (normal approximation with tie and continuity correction -- use with roughly 8+ values per sample)
- F-test of variances    H0 var(A) = var(B) (sensitive to non-normality)
- Jarque-Bera            every column: H0 the data are normally distributed (asymptotic test, unreliable below ~30 values)

The independent two-sample tests (Welch, Mann-Whitney, F) read sample A and B from the columns x and y, or -- with the Samples cell set to "grouped" -- from one value column x and a group label in y (needed when the groups differ in size, since loaded data is rectangular; A is the group with the smaller label). One-sided alternatives refer to A (greater: A > B); t-test confidence intervals are one-sided to match, like R's t.test.
"""

import math

from . import _basic as b
from . import _dist as dist
from . import _ui
from data import results
from ui.widgets import ComputeToolWindow, ParameterBox

TOOL_NAME = "Hypothesis Testing"
TOOL_DESCRIPTION = "t-tests (one-sample, Welch, paired), Mann-Whitney U, F-test of variances and Jarque-Bera normality test, with p-value, effect size and decision."
TOOL_INSTRUCTIONS = "Click the cells to pick a test, the alternative hypothesis and the sample layout, enter alpha (and mu0 for t-tests), load the data via the main window, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "statistic, df, p-value, effect size,\nconfidence interval and decision (reject H0 / keep H0)"

TESTS = [
    ("t1", "One-sample t-test"),
    ("t2", "Two-sample t-test (Welch)"),
    ("tp", "Paired t-test"),
    ("mw", "Mann-Whitney U"),
    ("f", "F-test (variances)"),
    ("jb", "Jarque-Bera (normality)"),
]
ALTERNATIVES = [("two-sided", "two-sided"), ("greater", "greater"), ("less", "less")]
SYMBOL = {"two-sided": "!=", "greater": ">", "less": "<"}
USES_MU0 = ("t1", "t2", "tp")


def _decision(p: float, alpha: float) -> str:
    return "reject H0" if p < alpha else "keep H0"


def _t_p_value(t: float, df: float, alternative: str) -> float:
    d = dist.StudentT(df)
    if alternative == "greater":
        return d.sf(t)
    if alternative == "less":
        return d.cdf(t)
    return min(1.0, 2.0 * d.sf(abs(t)))


def _mean_interval(alternative: str, estimate: float, se: float, df: float, alpha: float) -> tuple[float, float]:
    # (1 - alpha) confidence interval of a mean/difference, one-sided if the alternative is
    d = dist.StudentT(df)
    if alternative == "greater":
        return estimate - d.ppf(1 - alpha) * se, math.inf
    if alternative == "less":
        return -math.inf, estimate + d.ppf(1 - alpha) * se
    half = d.ppf(1 - alpha / 2) * se
    return estimate - half, estimate + half


def one_sample_t(values, mu0: float, alternative: str, alpha: float, label: str = "mean") -> dict:
    n = len(values)
    if n < 2:
        raise ValueError("A t-test needs at least 2 values per sample.")
    m, s = b.mean(values), b.std(values)
    if s == 0:
        raise ValueError("All values are identical -- the t statistic is undefined.")
    se = s / math.sqrt(n)
    t = (m - mu0) / se
    df = n - 1
    p = _t_p_value(t, df, alternative)
    lo, hi = _mean_interval(alternative, m, se, df, alpha)
    return {"n": n, label: m, "std dev": s, "t": t, "df": df, "p-value": p, "Cohen's d": (m - mu0) / s, "CI lower": lo, "CI upper": hi, "alpha": alpha, "decision": _decision(p, alpha)}


def welch_t(a, b_, mu0: float, alternative: str, alpha: float) -> dict:
    n1, n2 = len(a), len(b_)
    if n1 < 2 or n2 < 2:
        raise ValueError("A t-test needs at least 2 values per sample.")
    m1, m2 = b.mean(a), b.mean(b_)
    v1, v2 = b.variance(a), b.variance(b_)
    se2 = v1 / n1 + v2 / n2
    if se2 == 0:
        raise ValueError("Both samples are constant -- the t statistic is undefined.")
    se = math.sqrt(se2)
    diff = m1 - m2
    t = (diff - mu0) / se
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))  # Welch-Satterthwaite
    p = _t_p_value(t, df, alternative)
    lo, hi = _mean_interval(alternative, diff, se, df, alpha)
    pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    return {"n (A)": n1, "n (B)": n2, "mean (A)": m1, "mean (B)": m2, "difference": diff, "t": t, "df": df, "p-value": p, "Cohen's d": diff / pooled if pooled > 0 else None, "CI lower": lo, "CI upper": hi, "alpha": alpha, "decision": _decision(p, alpha)}


def f_test(a, b_, alternative: str, alpha: float) -> dict:
    n1, n2 = len(a), len(b_)
    if n1 < 2 or n2 < 2:
        raise ValueError("The F-test needs at least 2 values per sample.")
    v1, v2 = b.variance(a), b.variance(b_)
    if v2 == 0:
        raise ValueError("Sample B is constant -- the variance ratio is undefined.")
    f = v1 / v2
    d = dist.FDistribution(n1 - 1, n2 - 1)
    if alternative == "greater":
        p = d.sf(f)
    elif alternative == "less":
        p = d.cdf(f)
    else:
        p = min(1.0, 2.0 * min(d.cdf(f), d.sf(f)))
    return {"n (A)": n1, "n (B)": n2, "var (A)": v1, "var (B)": v2, "F": f, "df1": n1 - 1, "df2": n2 - 1, "p-value": p, "alpha": alpha, "decision": _decision(p, alpha)}


def mann_whitney(a, b_, alternative: str, alpha: float) -> dict:
    n1, n2 = len(a), len(b_)
    if n1 < 1 or n2 < 1:
        raise ValueError("Both samples need at least 1 value.")
    ranks, ties = b.ranks(list(a) + list(b_))
    u1 = sum(ranks[:n1]) - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    n = n1 + n2
    mu = n1 * n2 / 2
    var = n1 * n2 / 12 * ((n + 1) - sum(t ** 3 - t for t in ties) / (n * (n - 1))) if n > 1 else 0.0
    if var <= 0:
        raise ValueError("All values are identical -- the U statistic carries no information.")
    sd = math.sqrt(var)
    diff = u1 - mu
    shift = 0.5 if abs(diff) > 0.5 else abs(diff)  # continuity correction, never past the centre
    z = (diff - math.copysign(shift, diff)) / sd if alternative == "two-sided" else ((diff - 0.5) if alternative == "greater" else (diff + 0.5)) / sd
    if alternative == "two-sided":
        p = min(1.0, 2.0 * dist.norm_cdf(-abs(z)))
    elif alternative == "greater":
        p = dist.norm_cdf(-z)
    else:
        p = dist.norm_cdf(z)
    return {"n (A)": n1, "n (B)": n2, "U (A)": u1, "U (B)": u2, "z": z, "p-value": p, "rank-biserial r": (u1 - u2) / (n1 * n2), "alpha": alpha, "decision": _decision(p, alpha)}


def jarque_bera(values, alpha: float) -> dict:
    n = len(values)
    if n < 4:
        raise ValueError("Jarque-Bera needs at least 4 values per column.")
    skew, kurt = b.skewness(values, sample=False), b.excess_kurtosis(values, sample=False)
    if skew is None:
        raise ValueError("All values are identical -- skewness is undefined.")
    jb = n / 6.0 * (skew ** 2 + kurt ** 2 / 4.0)
    p = math.exp(-jb / 2.0)  # chi-square with 2 df: sf(x) = exp(-x/2)
    return {"n": n, "skewness": skew, "kurtosis": kurt, "JB": jb, "df": 2, "p-value": p, "alpha": alpha, "decision": _decision(p, alpha)}


def _hypotheses(test: str, alternative: str, la: str, lb: str) -> str:
    sym = SYMBOL[alternative]
    if test == "t1":
        return f"H0: mean = mu0    H1: mean {sym} mu0"
    if test == "t2":
        return f"H0: mean(A) - mean(B) = mu0    H1: mean(A) - mean(B) {sym} mu0"
    if test == "tp":
        return f"H0: mean(x - y) = mu0    H1: mean(x - y) {sym} mu0"
    if test == "mw":
        word = {"two-sided": "differs from", "greater": "tends to be larger than", "less": "tends to be smaller than"}[alternative]
        return f"H0: A and B come from the same distribution    H1: A {word} B"
    if test == "f":
        return f"H0: var(A) = var(B)    H1: var(A) {sym} var(B)"
    return "H0: the data are normally distributed"


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._test, self._alternative, self._layout = "t1", "two-sided", "columns"
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, TESTS, "Test: ", self._on_test_change)
        _ui.mode_cell(parent, ALTERNATIVES, "Alternative: ", lambda key: setattr(self, "_alternative", key))
        _ui.samples_cell(parent, lambda key: setattr(self, "_layout", key))

        self.box = ParameterBox(parent, "Parameters")
        self.box.pack(fill="x", pady=(0, 8))
        self.box.add("alpha", "Significance level alpha", "0.05")
        self.box.add("mu0", "H0 value mu0 (mean / difference)", "0")

    def _on_test_change(self, key: str) -> None:
        self._test = key
        self.box.set_enabled("mu0", key in USES_MU0)

    def compute(self, dataset):
        cols = b.columns(dataset)
        test, alternative = self._test, self._alternative
        alpha = b.parse_probability(self.box.get("alpha"), "alpha")
        mu0 = b.parse_float(self.box.get("mu0"), "mu0") if test in USES_MU0 else 0.0
        label = dict(TESTS)[test]
        la = lb = None

        if test in ("t1", "jb"):  # one sample per column
            groups = {name: one_sample_t(values, mu0, alternative, alpha) if test == "t1" else jarque_bera(values, alpha) for name, values in cols.items()}
        else:
            if test == "tp":
                if "x" not in cols or "y" not in cols:
                    raise ValueError("The paired t-test needs two columns (x, y).")
                groups = {None: one_sample_t([p - q for p, q in zip(cols["x"], cols["y"])], mu0, alternative, alpha, label="mean diff")}
            else:
                a, b_, la, lb = b.two_samples(cols, grouped=self._layout == "grouped")
                if test == "t2":
                    groups = {None: welch_t(a, b_, mu0, alternative, alpha)}
                elif test == "mw":
                    groups = {None: mann_whitney(a, b_, alternative, alpha)}
                else:
                    groups = {None: f_test(a, b_, alternative, alpha)}

        head = f"{label}" + ("" if test == "jb" else f" ({alternative})")
        lines = [head, _hypotheses(test, alternative, la, lb)]
        if la:
            lines.append(f"A = {la}, B = {lb}")
        if test in USES_MU0:
            lines.append(f"mu0 = {mu0:g}")
        return results.stats_dataset(dataset, TOOL_NAME, "\n".join(lines), groups, metadata={"test": test, "alternative": alternative, "alpha": alpha})


def open_window(parent) -> None:
    ToolWindow(parent)
