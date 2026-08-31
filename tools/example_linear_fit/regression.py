"""
Placeholder for one of your existing regression scripts. Pure computation, no GUI dependency -- gui.py only calls fit_from_csv(). This keeps existing scripts untouched; each tool just needs a thin gui.py wrapper.
"""

import csv


def fit_from_csv(path: str) -> dict:
    # Expects a CSV with two columns (x, y), returns the least squares linear fit y = a*x + b.
    xs, ys = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                xs.append(float(row[0]))
                ys.append(float(row[1]))
            except ValueError:
                continue  # e.g. header row

    n = len(xs)
    if n < 2:
        raise ValueError("At least 2 valid (x, y) rows are required.")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        raise ValueError("All x values are identical, slope cannot be computed.")

    a = ss_xy / ss_xx
    b = mean_y - a * mean_x

    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1 - ss_res / ss_tot if ss_tot else 1.0

    return {"a": a, "b": b, "r_squared": r_squared, "n": n}
