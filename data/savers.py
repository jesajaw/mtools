"""
Shared file saving for all tools -- mirrors loaders.py for output.
"""

import csv


def save_text(path: str, content: str) -> None:
    """Plain text export -- writes exactly what's given."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_points_csv(path: str, points) -> None:
    """Writes points (flat list of floats, or list of (x, y[, z])
    tuples) out as clean, comma-separated CSV -- mirrors the format
    loaders.load_points() reads."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for p in points:
            writer.writerow([p] if isinstance(p, (int, float)) else list(p))


def save_dataset_csv(path: str, dataset) -> None:
    arrays = list(dataset.axes.values()) + list(dataset.data.values())
    if not arrays:
        raise ValueError("Nothing to save -- this dataset has no arrays.")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in zip(*(a.values for a in arrays)):
            writer.writerow(row)
