"""
Shared file loading for all tools -- central place for input-format handling so individual tool categories don't each reimplement parsing.

Formats
-------
* Text tables (.csv / .tsv / .txt / .dat): delimiter (``; , tab | whitespace``) and decimal separator (``.`` or ``,``, also German "1.234,5") are auto-detected, the encoding too (UTF-8 / UTF-16 / Windows-1252 fallback). Any number of columns is accepted.
    - A header line is recognised and kept: ``name [unit]`` -> array name + units.
    - ``# ...`` comment lines are read back as metadata (this is how a saved fit result -- model, equation, parameters -- survives a CSV round trip, see savers.py).
    - Rows with a wrong column count or missing values are never silently shifted; by default they are dropped and *counted* in ``metadata["skipped_rows"]`` (``on_missing="keep"`` keeps them as NaN, ``"error"`` raises).
* NumPy (.npy): a 1D array becomes the column ``x``; a 2D array (e.g. an AFM image, rows = scanlines) one 2D array ``z`` with dims ``("y", "x")``. Needs numpy only for this format (imported on demand).
* mtools JSON (.json): lossless -- arrays of any dimension, units, uncertainties, annotations, metadata and several datasets per file (a whole workspace). Written by savers.save_json().

Column naming: the first three columns become the axes ``x``, ``y``, ``z`` (what every tool expects); further columns become data arrays. If the header itself names its columns ``x``/``y``/``z`` (as savers.py writes them) that naming is used verbatim, so ``x, y, fit, residual`` comes back exactly as saved.
"""

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from data.dataset import DataSet, DataArray, Annotation, COORDINATES

TEXT_EXTENSIONS = (".csv", ".tsv", ".txt", ".dat")
JSON_EXTENSIONS = (".json",)
NUMPY_EXTENSIONS = (".npy",)
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS + JSON_EXTENSIONS + NUMPY_EXTENSIONS

JSON_FORMAT = "mtools"
JSON_VERSION = 1

_DELIMITERS = (";", "\t", "|", ",", None)  # None = any whitespace; first one giving a consistent multi-column table wins
_MISSING_TOKENS = {"", "nan", "na", "n/a", "null", "none", "-"}
_HEADER_UNIT = re.compile(r"^(.*?)\s*[\[(]([^\[\]()]*)[\])]\s*$")
_PARAM_COMMENT = re.compile(r"^#\s*([A-Za-z_]\w*)\s*=\s*(\S+)\s*$")
_KEY_COMMENT = re.compile(r"^#\s*([A-Za-z_][\w ]*?)\s*:\s*(.*)$")


# --------------------------------------------------------------------------- public API

def load_dataset(path: str, **options) -> DataSet:
    """Loads one DataSet (for a JSON file holding several, the first -- use load_datasets for all)."""
    return load_datasets(path, **options)[0]


def load_datasets(path: str, **options) -> list[DataSet]:
    """Loads every DataSet in a file: text files give exactly one, mtools JSON any number. `options` go to parse_table() (delimiter=, decimal=, on_missing=)."""
    ext = Path(path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: '{ext or '(none)'}' (supported: {', '.join(SUPPORTED_EXTENSIONS)}).")
    name = Path(path).name
    if ext in NUMPY_EXTENSIONS:
        return [_load_npy(path, name)]

    text, encoding = read_text(path)
    if not text.strip():
        raise ValueError("File is empty.")

    if ext in JSON_EXTENSIONS:
        datasets = datasets_from_json(text)
        for ds in datasets:
            ds.name = ds.name or name
            ds.metadata.setdefault("source_path", str(path))
        return datasets

    dataset = parse_dataset(text, name=name, **options)
    dataset.metadata.update(source_path=str(path), encoding=encoding)
    return [dataset]


def _load_npy(path: str, name: str) -> DataSet:
    try:
        import numpy as np
    except ImportError:
        raise ValueError("Loading .npy files needs numpy (pip install numpy).") from None
    try:
        array = np.load(path, allow_pickle=False)  # never unpickle: a data file must not be able to run code
    except ValueError as e:
        raise ValueError(f"Not a plain numeric .npy file ({e}).") from None
    if array.dtype.kind not in "biuf":
        raise ValueError(f"Only numeric arrays can be loaded (this one has dtype {array.dtype}).")
    if array.size == 0:
        raise ValueError("File is empty.")
    array = array.astype(float)
    meta = {"format": "npy", "source_path": str(path), "shape": list(array.shape)}
    if array.ndim == 1:
        return DataSet(axes={"x": DataArray(values=array.tolist(), name="x")}, metadata=meta, name=name)
    if array.ndim == 2:
        return DataSet(data={"z": DataArray(values=array.tolist(), name="z", dims=("y", "x"), label="Image")}, metadata=meta, name=name)
    raise ValueError(f"Only 1D and 2D arrays are supported (this one is {array.ndim}D).")


def read_text(path: str) -> tuple[str, str]:
    """Reads a text file, detecting the encoding. Returns (text, encoding_name). Never raises UnicodeDecodeError -- Excel/German files are often Windows-1252, not UTF-8."""
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8"
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def datasets_from_json(text: str) -> list[DataSet]:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Not a valid JSON file: {e}") from None
    if not isinstance(doc, dict) or doc.get("format") != JSON_FORMAT:
        raise ValueError("This JSON file was not written by mtools (missing 'format': 'mtools').")
    if int(doc.get("version", 0)) > JSON_VERSION:
        raise ValueError(f"File format version {doc['version']} is newer than this mtools understands ({JSON_VERSION}) -- please update mtools.")
    try:
        datasets = [DataSet.from_dict(d) for d in doc.get("datasets", [])]
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Corrupt mtools JSON file ({type(e).__name__}: {e}).") from None
    if not datasets:
        raise ValueError("The file contains no datasets.")
    return datasets


# --------------------------------------------------------------------------- text tables

@dataclass
class ParsedTable:
    columns: list[list[float]]                 # column-major, equal lengths
    header: list[str] | None = None
    delimiter: str | None = None
    comments: list[str] = field(default_factory=list)
    skipped_rows: int = 0                      # numeric-looking rows dropped (wrong width / missing values)
    skipped_lines: int = 0                     # free-text lines ignored (titles, notes)

    @property
    def width(self) -> int:
        return len(self.columns)


def parse_dataset(text: str, name: str | None = None, **options) -> DataSet:
    """Text -> DataSet (see module docstring for naming/metadata rules)."""
    table = parse_table(text, **options)
    comments = _read_comments(table.comments)
    axes, data = _name_columns(table)

    metadata = {"format": "text", "delimiter": "whitespace" if table.delimiter is None else table.delimiter}
    metadata.update(comments["metadata"])
    if table.skipped_rows:
        metadata["skipped_rows"] = table.skipped_rows
    if table.skipped_lines:
        metadata["skipped_lines"] = table.skipped_lines
    if comments["notes"]:
        metadata["comments"] = comments["notes"]

    for array in list(axes.values()) + list(data.values()):
        if array.name in comments["labels"]:
            array.label = comments["labels"][array.name]

    ds = DataSet(axes=axes, data=data, annotations=comments["annotations"], metadata=metadata, name=name, source_tool=comments["metadata"].get("model"))
    return ds


def parse_table(text: str, delimiter: str | None | bool = True, decimal: str | None = None, on_missing: str = "drop") -> ParsedTable:
    """The tolerant core parser. `delimiter=True` auto-detects (pass ';', '\\t', ',' ... or None for whitespace to force one), `decimal` forces '.' or ','. `on_missing`: 'drop' | 'keep' (NaN) | 'error'."""
    if on_missing not in ("drop", "keep", "error"):
        raise ValueError("on_missing must be 'drop', 'keep' or 'error'.")
    comments, body = [], []
    for line in text.splitlines():
        stripped = line.strip().lstrip("﻿")
        if not stripped:
            continue
        (comments if stripped.startswith("#") else body).append(stripped if stripped.startswith("#") else line.strip().lstrip("﻿"))
    if not body:
        raise ValueError("No data given.")

    candidates = _DELIMITERS if delimiter is True else (delimiter,)
    best = None
    for delim in candidates:
        parsed = _try_delimiter(body, delim, decimal)
        if parsed is None:
            continue
        if parsed["width"] > 1:
            best = parsed
            break
        if best is None or len(parsed["rows"]) > len(best["rows"]):
            best = parsed
    if best is None:
        raise ValueError("No numeric data found -- check the file (delimiter, decimal separator).")

    rows, width = best["rows"], best["width"]
    if len(rows) * 2 < best["numeric_lines"]:
        raise ValueError("Could not determine a consistent column structure -- most rows have a different number of columns.")

    kept, skipped = [], best["numeric_lines"] - len(rows)  # lines whose width != the table's width
    for row in rows:
        if any(v is None for v in row):
            if on_missing == "error":
                raise ValueError("Missing values found (empty cell or NaN) -- fill them or load with on_missing='drop'.")
            if on_missing == "drop":
                skipped += 1
                continue
            row = [math.nan if v is None else v for v in row]
        kept.append(row)
    if not kept:
        raise ValueError("No complete numeric rows found.")

    return ParsedTable(columns=[list(c) for c in zip(*kept)], header=best["header"], delimiter=best["delimiter"], comments=comments, skipped_rows=skipped, skipped_lines=best["text_lines"])


def _split(line: str, delim: str | None) -> list[str]:
    return line.split() if delim is None else [f.strip().strip('"').strip("'").strip() for f in line.split(delim)]


def _try_delimiter(body: list[str], delim, decimal):
    """Parses every line with `delim`. Returns None if there's no numeric line, else the rows of the dominant width (values may be None = missing)."""
    split_lines = [_split(line, delim) for line in body]
    if delim is not None and len(split_lines) > 1 and all(f and f[-1] == "" for f in split_lines):
        split_lines = [f[:-1] for f in split_lines]  # every line ends with a delimiter ("1;2;") -> not a column

    parsed: list[tuple[int, list]] = []  # (line index, values) for lines that are entirely numeric (empty/NaN allowed)
    for i, fields in enumerate(split_lines):
        if not fields:
            continue
        values = []
        for tok in fields:
            v = _to_float(tok, decimal)
            if v is _BAD:
                values = None
                break
            values.append(v)
        if values is not None and any(v is not None for v in values):
            parsed.append((i, values))
    if not parsed:
        return None

    widths: dict[int, int] = {}
    for _, values in parsed:
        widths[len(values)] = widths.get(len(values), 0) + 1
    width = max(widths, key=lambda w: (widths[w], w))
    rows = [(i, v) for i, v in parsed if len(v) == width]

    first = rows[0][0]
    header = None
    if first > 0:
        candidate = split_lines[first - 1]
        if len(candidate) == width and not any(_to_float(t, decimal) is not _BAD for t in candidate if t):
            header = candidate  # the line right above the first data row, same width, all text
    numeric_idx = {i for i, _ in parsed}
    text_lines = sum(1 for i, f in enumerate(split_lines) if f and i not in numeric_idx) - (1 if header else 0)
    return {"rows": [v for _, v in rows], "width": width, "header": header, "delimiter": delim, "numeric_lines": len(parsed), "text_lines": max(text_lines, 0)}


_BAD = object()


def _to_float(token: str, decimal: str | None = None):
    """float | None (missing: empty / nan / n/a ...) | _BAD (not a number at all)."""
    t = token.strip()
    if t.lower() in _MISSING_TOKENS:
        return None
    if "_" in t or " " in t:
        return _BAD  # Python's float() would accept "1_0" -- a number with underscores is a label, not data
    if decimal == ",":
        t = t.replace(".", "").replace(",", ".")
    elif decimal == ".":
        t = t.replace(",", "")
    elif "," in t:
        if "." in t:  # both present: the last one is the decimal separator ("1.234,5" / "1,234.5")
            if t.rfind(",") > t.rfind("."):
                t = t.replace(".", "").replace(",", ".")
            else:
                t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return _BAD
    return None if math.isnan(v) else v


def _clean_header(raw: str) -> tuple[str, str | None]:
    m = _HEADER_UNIT.match(raw)
    name, unit = (m.group(1), m.group(2).strip() or None) if m else (raw, None)
    return name.strip(), unit


def _name_columns(table: ParsedTable) -> tuple[dict, dict]:
    width = table.width
    headers = [_clean_header(h) for h in table.header] if table.header else [None] * width
    lowered = [h[0].lower() if h else None for h in headers]

    names: list[str] = []
    if "x" in lowered:  # the file names its coordinates itself (savers.py output) -> keep its naming
        used: set[str] = set()
        for i in range(width):
            n = lowered[i] if lowered[i] in COORDINATES else (headers[i][0] or f"col{i + 1}")
            base, k = n, 2
            while n in used:
                n, k = f"{base}_{k}", k + 1
            used.add(n)
            names.append(n)
    else:  # positional: first three columns are x, y, z -- the header text (if any) is kept as label/units
        for i in range(width):
            if i < len(COORDINATES):
                names.append(COORDINATES[i])
            else:
                own = headers[i][0] if headers[i] else ""
                names.append(own if own and own not in names and own not in COORDINATES else f"col{i + 1}")

    axes, data = {}, {}
    for i, name in enumerate(names):
        label, units = (headers[i][0] or None, headers[i][1]) if headers[i] else (None, None)
        array = DataArray(values=table.columns[i], name=name, units=units, label=label if label != name else None)
        (axes if name in COORDINATES else data)[name] = array
    return axes, data


def _read_comments(comments: list[str]) -> dict:
    """'# model: X' / '# equation: ...' / '# a = 1.5' / '# label x: Time' / '# annotation: {json}' -> structured metadata (everything else stays a free note)."""
    meta, labels, annotations, notes, params = {}, {}, [], [], {}
    for line in comments:
        m = _PARAM_COMMENT.match(line)
        if m:
            try:
                params[m.group(1)] = float(m.group(2))
                continue
            except ValueError:
                pass
        m = _KEY_COMMENT.match(line)
        if m:
            raw_key, value = m.group(1).strip(), m.group(2).strip()
            key = raw_key.lower()
            if key in ("model", "equation"):
                meta[key] = value
                continue
            if key.startswith("label "):
                labels[raw_key[6:].strip()] = value  # array names are case-sensitive
                continue
            if key == "annotation":
                try:
                    annotations.append(Annotation.from_dict(json.loads(value)))
                    continue
                except (ValueError, KeyError, TypeError):
                    pass
        notes.append(line.lstrip("#").strip())
    if "model" in meta:  # a fit result: the '# name = value' lines are its parameters
        meta["kind"] = "fit"
        annotations = [Annotation(kind="parameter", name=k, data={"value": v}) for k, v in params.items()] + annotations
    else:
        notes.extend(f"{k} = {v!r}" for k, v in params.items())
    return {"metadata": meta, "labels": labels, "annotations": annotations, "notes": [n for n in notes if n]}


# --------------------------------------------------------------------------- legacy API (kept for existing callers)

def load_points(path: str):
    """Reads points from a file -- flat list of floats (1 column) or (x, y[, z]) tuples (2-3 columns). Kept for old callers; new code should use load_dataset()."""
    ds = load_dataset(path)
    return _points_of(ds)


def parse_points(text: str):
    """Text -> flat list of floats / list of tuples, see load_points()."""
    return _points_of(parse_dataset(text))


def _points_of(ds: DataSet):
    cols = [ds.get(n).values for n in COORDINATES if n in ds.axes]
    width = len(ds.axes) + len(ds.data)
    if width not in (1, 2, 3):
        raise ValueError(f"Expected 1 to 3 columns (x[, y[, z]]), got {width}.")
    return list(cols[0]) if len(cols) == 1 else [tuple(p) for p in zip(*cols)]
