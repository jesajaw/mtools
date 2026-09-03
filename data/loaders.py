"""
Shared file loading for all tools. Central place for input-format
handling so individual tool categories don't each reimplement CSV
parsing -- adding a new format is a one-time job here.

Not a tool itself (no TOOL_NAME/TOOL_DESCRIPTION/open_window) --
core.registry only requires those on modules it lists as tools;
importing this module from elsewhere is fine either way.
"""

from pathlib import Path

# Tried in this order; whitespace (last) also collapses runs of
# spaces/tabs, so ragged manually-aligned columns still parse.
_DELIMITER_SPLITTERS = [
    lambda line: line.split(";"),
    lambda line: line.split("\t"),
    lambda line: line.split(","),
    lambda line: line.split(),
]


def load_points(path: str):
    """Reads points from a file, format inferred from the extension.
    Currently supports .csv/.txt/.dat -- parsing itself is handled by
    parse_points() below, so file input and manual text entry (see
    theme.widgets.FileInputRow) go through identical logic."""
    ext = Path(path).suffix.lower()
    if ext not in (".csv", ".txt", ".dat"):
        raise ValueError(f"Unsupported file format: '{ext or '(none)'}'.")

    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    if not text.strip():
        raise ValueError("File is empty.")
    return parse_points(text)

def parse_points(text: str):
    """Parses points from raw text, auto-detected delimiter
    (semicolon, tab, comma, or whitespace) -- German-style decimal
    commas (e.g. "1,23") are also accepted. Non-numeric lines
    (headers/labels) are skipped automatically. Returns a flat list
    of floats for a single column, or a list of (x, y[, z]) tuples
    for 2 or 3 columns -- the format mathlib.split_points() expects."""
    raw_lines = [line.rstrip("\r\n") for line in text.splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError("No data given.")

    best = None
    for splitter in _DELIMITER_SPLITTERS:
        rows = _numeric_rows(raw_lines, splitter)
        if rows is None:
            continue
        if best is None or len(rows[0]) > len(best[0]):
            best = rows
        if len(rows[0]) > 1:
            break

    if best is None:
        raise ValueError("Could not determine a consistent column structure -- check the formatting.")

    width = len(best[0])
    if width not in (1, 2, 3):
        raise ValueError(f"Expected 1 to 3 columns (x[, y[, z]]), got {width}.")

    if width == 1:
        return [r[0] for r in best]
    return [tuple(r) for r in best]


def _numeric_rows(raw_lines, splitter):
    """Applies splitter to every line, keeps only the lines that parse
    as all-numeric (skipping headers/labels), and requires those
    numeric lines to share one consistent column count. Returns None
    if nothing numeric was found or the column count isn't consistent."""
    rows: list[list[float]] = []
    for line in raw_lines:
        fields = [v.strip() for v in splitter(line) if v.strip() != ""]
        if not fields:
            continue
        try:
            values = [float(v.replace(",", ".")) for v in fields]
        except ValueError:
            continue  # header row or other non-numeric line
        rows.append(values)

    if not rows:
        return None
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        return None
    return rows
