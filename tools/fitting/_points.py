"""Shared points-file loader for the regression tools. Not a tool
itself (leading underscore -- core.registry skips it)."""

import csv


def load_points(path: str):
    """Reads a CSV file into the point format mathlib.split_points()
    expects: a flat list of floats for a single column, or a list of
    (x, y[, z]) tuples for 2 or 3 columns."""
    rows: list[list[float]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                values = [float(v) for v in row]
            except ValueError:
                continue  # e.g. a header row
            rows.append(values)

    if not rows:
        raise ValueError("No numeric rows found in the file.")

    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("All rows must have the same number of columns.")
    if width not in (1, 2, 3):
        raise ValueError(f"Expected 1 to 3 columns (x[, y[, z]]), got {width}.")

    if width == 1:
        return [r[0] for r in rows]
    return [tuple(r) for r in rows]
