"""
Shared numeric helpers for the statistics tools (private helper, skipped by tool discovery): descriptive building blocks, column access on the workspace DataSet and parsing of user-typed numbers.

Functions return None where a quantity is undefined for the given sample (e.g. a sample variance for n = 1) -- callers decide whether that is an error or just a "-" in the result.
"""

import math
from collections import Counter

COORDINATES = ("x", "y", "z")


# -- column access -----------------------------------------------------------

def _flat_numbers(values) -> list[float] | None:
    # the values as a flat list of finite floats, or None if the array is not a plain numeric column
    try:
        out = []
        for v in values:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return None
            out.append(float(v))
        return out
    except TypeError:
        return None


def columns(dataset) -> dict[str, list[float]]:
    """
    Every numeric column of a workspace DataSet as {name: values}: the axes first (x, y, z, ...), then 1D data arrays of the same length (e.g. 'fit' and 'residual' of a fit result), so statistics can also be taken of a previous tool's output.
    Raises a readable ValueError for missing data or non-finite values (NaN/inf).
    """
    if dataset is None:
        raise ValueError("No data loaded -- load data via the main window first.")
    names = [k for k in COORDINATES if k in dataset.axes] + [k for k in dataset.axes if k not in COORDINATES]
    cols: dict[str, list[float]] = {}
    for name in names:
        values = _flat_numbers(dataset.axes[name].values)
        if values is None:
            raise ValueError(f"Column '{name}' is not a plain list of numbers.")
        cols[name] = values
    n = len(next(iter(cols.values()))) if cols else None
    for name, array in dataset.data.items():
        values = _flat_numbers(array.values)
        if values is not None and (n is None or len(values) == n):
            cols[name] = values
    if not cols or not next(iter(cols.values())):
        raise ValueError("The loaded data contains no values.")
    for name, values in cols.items():
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f"Column '{name}' contains NaN or infinite values.")
    return cols


def two_samples(cols: dict, grouped: bool = False):
    """
    Two independent samples (a, b, label_a, label_b) from the columns x and y:
    - grouped=False: sample A = column x, sample B = column y.
    - grouped=True: x holds the values and y the group label; y must contain exactly two distinct values, A is the group with the smaller label.
    """
    if "x" not in cols or "y" not in cols:
        raise ValueError("This test needs two columns (x, y).")
    if not grouped:
        return cols["x"], cols["y"], "x", "y"
    labels = sorted(set(cols["y"]))
    if len(labels) != 2:
        raise ValueError(f"Grouped layout: column y must contain exactly 2 distinct group labels, found {len(labels)}.")
    a = [v for v, g in zip(cols["x"], cols["y"]) if g == labels[0]]
    b = [v for v, g in zip(cols["x"], cols["y"]) if g == labels[1]]
    return a, b, f"x[y={labels[0]:g}]", f"x[y={labels[1]:g}]"


# -- descriptive building blocks --------------------------------------------

def mean(values) -> float:
    return math.fsum(values) / len(values)


def variance(values, ddof: int = 1) -> float | None:
    n = len(values)
    if n - ddof < 1:
        return None
    m = mean(values)
    return math.fsum((v - m) ** 2 for v in values) / (n - ddof)


def std(values, ddof: int = 1) -> float | None:
    var = variance(values, ddof)
    return None if var is None else math.sqrt(var)


def quantile(ordered, q: float) -> float:
    """Quantile of an already sorted list, linear interpolation between order statistics (NumPy/R 'type 7')."""
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def median(values) -> float:
    return quantile(sorted(values), 0.5)


def modes(values) -> tuple[list[float], int]:
    """(sorted modes, their count); an empty list if no value occurs more than once."""
    counts = Counter(values)
    top = max(counts.values())
    if top == 1:
        return [], 1
    return sorted(v for v, c in counts.items() if c == top), top


def _central_moments(values):
    n = len(values)
    m = mean(values)
    m2 = math.fsum((v - m) ** 2 for v in values) / n
    m3 = math.fsum((v - m) ** 3 for v in values) / n
    m4 = math.fsum((v - m) ** 4 for v in values) / n
    return n, m2, m3, m4


def skewness(values, sample: bool = True) -> float | None:
    """Fisher-Pearson skewness; sample=True applies the usual bias adjustment G1 (needs n >= 3)."""
    n, m2, m3, _ = _central_moments(values)
    if m2 == 0 or (sample and n < 3):
        return None
    g1 = m3 / m2 ** 1.5
    return g1 * math.sqrt(n * (n - 1)) / (n - 2) if sample else g1


def excess_kurtosis(values, sample: bool = True) -> float | None:
    """Excess kurtosis (normal = 0); sample=True applies the bias adjustment G2 (needs n >= 4)."""
    n, m2, _, m4 = _central_moments(values)
    if m2 == 0 or (sample and n < 4):
        return None
    g2 = m4 / m2 ** 2 - 3.0
    return (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 + 6.0) if sample else g2


def ranks(values) -> tuple[list[float], list[int]]:
    """Average ranks (1-based, ties share the mean rank) and the sizes of all tie groups."""
    n = len(values)
    order = sorted(range(n), key=values.__getitem__)
    out = [0.0] * n
    ties = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = rank
        ties.append(j - i + 1)
        i = j + 1
    return out, ties


# -- parsing user input ------------------------------------------------------

def parse_float(text: str, name: str) -> float:
    """A number typed into an entry; a decimal comma is accepted like in the file loader."""
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"'{name}' must be a number, got '{text.strip()}'.")


def parse_probability(text: str, name: str) -> float:
    """A probability typed as 0.95, 95 or 95% (all meaning 0.95). Must end up strictly between 0 and 1."""
    raw = text.strip()
    percent = raw.endswith("%")
    value = parse_float(raw.rstrip("%"), name)
    if percent or 1.0 < value < 100.0:
        value /= 100.0
    if not 0.0 < value < 1.0:
        raise ValueError(f"'{name}' must be between 0 and 1 (e.g. 0.95 or 95%), got '{raw}'.")
    return value
