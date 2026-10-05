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
        md = dataset.metadata
        if md.get("model"):  # fit result: keep model + parameters with the numbers (as '#' lines, which loaders.parse_points skips)
            f.write(f"# model: {md['model']}\n")
            if md.get("equation"):
                f.write(f"# equation: {md['equation']}\n")
            for a in dataset.annotations_of("parameter"):
                f.write(f"# {a.name} = {a.data['value']!r}\n")
        writer = csv.writer(f)
        writer.writerow([a.name for a in arrays])
        for row in zip(*(a.values for a in arrays)):
            writer.writerow(row)
