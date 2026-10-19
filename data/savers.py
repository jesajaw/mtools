"""
Shared file saving for all tools -- mirrors loaders.py for output.

Formats (chosen by the file extension, see save_dataset):
* .csv  -- comma separated, '.' decimals. Header = array names (+ ``[unit]``), ``# ...`` comment lines carry model / equation / parameters / labels / annotations so loaders.py reads a saved result back exactly. Only 1D columns fit in a table: 2D grids and the like raise a clear error -> use .json.
* .tsv  -- same, tab separated.
* .json -- lossless mtools format (any array shape, units, uncertainties, annotations, metadata) and it can hold the whole workspace, i.e. several datasets in one file.

Excel with a German locale wants ';' and decimal ',' -- pass ``delimiter=";", decimal=","`` or change DEFAULT_DELIMITER / DEFAULT_DECIMAL below; loaders.py reads both flavours.

Every file is written atomically (temp file in the same folder, then rename): a failure half-way never destroys an existing file.
"""

import csv
import json
import math
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from data.dataset import DataSet
from data.loaders import JSON_FORMAT, JSON_VERSION

DEFAULT_DELIMITER = ","
DEFAULT_DECIMAL = "."


# --------------------------------------------------------------------------- helpers

@contextmanager
def atomic_open(path: str, newline: str | None = ""):
    """open(path, "w") that only replaces `path` once the block finished without error."""
    target = Path(path)
    fd, tmp = tempfile.mkstemp(dir=target.parent or ".", prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            yield f
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _fmt(value, decimal: str) -> str | int:
    if isinstance(value, float):
        if math.isnan(value):
            return ""  # missing -> empty cell
        text = repr(value)  # shortest string that reads back to the exact same float
        return text.replace(".", decimal) if decimal != "." else text
    return value


def _oneline(text) -> str:
    return " ".join(str(text).split())


# --------------------------------------------------------------------------- public API

def save_dataset(path: str, dataset: DataSet, datasets: list[DataSet] | None = None) -> None:
    """Saves by file extension: .json (all of `datasets` if given, else just `dataset`), .tsv, anything else as CSV."""
    ext = Path(path).suffix.lower()
    if ext == ".json":
        save_json(path, datasets or [dataset])
    elif ext == ".tsv":
        save_dataset_csv(path, dataset, delimiter="\t")
    else:
        save_dataset_csv(path, dataset)


def save_text(path: str, content: str) -> None:
    """Plain text export -- writes exactly what's given."""
    with atomic_open(path, newline=None) as f:
        f.write(content)


def save_points_csv(path: str, points) -> None:
    """Writes points (flat list of floats, or list of (x, y[, z]) tuples) as CSV without header -- mirrors loaders.load_points()."""
    with atomic_open(path) as f:
        writer = csv.writer(f, lineterminator="\n")
        for p in points:
            writer.writerow([p] if isinstance(p, (int, float)) else list(p))


def save_dataset_csv(path: str, dataset: DataSet, delimiter: str = None, decimal: str = None) -> None:
    delimiter = DEFAULT_DELIMITER if delimiter is None else delimiter
    decimal = DEFAULT_DECIMAL if decimal is None else decimal
    if decimal == delimiter:
        raise ValueError("Decimal separator and column delimiter must differ.")

    arrays = list(dataset.axes.values()) + list(dataset.data.values())
    for a in arrays:
        if a.ndim != 1:
            raise ValueError(f"'{a.name}' is {a.ndim}-dimensional -- a CSV table can only hold 1D columns. Save as .json instead (lossless, keeps grids/images).")
    dataset.check_consistency()  # never silently truncate to the shortest column
    if not arrays and not dataset.annotations:
        raise ValueError("Nothing to save -- this dataset has no arrays or annotations.")

    with atomic_open(path) as f:
        _write_comments(f, dataset, with_annotations=bool(arrays))
        writer = csv.writer(f, delimiter=delimiter, lineterminator="\n")
        if arrays:
            writer.writerow([a.name if not a.units else f"{a.name} [{a.units}]" for a in arrays])
            for row in zip(*(a.values for a in arrays)):
                writer.writerow([_fmt(v, decimal) for v in row])
        else:  # annotation-only result (e.g. a peak list): a plain table for spreadsheets; JSON is the loadable form
            keys = sorted({k for a in dataset.annotations for k in a.data})
            grouped = any(a.metadata.get("group") for a in dataset.annotations)  # statistics results: which column/sub-result a value belongs to
            writer.writerow(["kind", *(["group"] if grouped else []), "name", *keys])
            for a in dataset.annotations:
                writer.writerow([a.kind, *([a.metadata.get("group") or ""] if grouped else []), a.name or "", *(_fmt(a.data.get(k, ""), decimal) for k in keys)])


def _write_comments(f, dataset: DataSet, with_annotations: bool = True) -> None:
    md = dataset.metadata
    if md.get("model"):  # fit result: keep model + parameters with the numbers (as '#' lines, which loaders.py reads back)
        f.write(f"# model: {_oneline(md['model'])}\n")
        if md.get("equation"):
            f.write(f"# equation: {_oneline(md['equation'])}\n")
        for a in dataset.annotations_of("parameter"):
            f.write(f"# {a.name} = {a.data['value']!r}\n")
    elif md.get("kind") == "statistics":  # statistics result: heading and every reported value, same '#' convention (use .json for a lossless copy)
        f.write(f"# tool: {_oneline(md.get('tool'))}\n")
        for line in str(md.get("title") or "").splitlines():
            f.write(f"# {line}\n")
        for a in dataset.annotations_of("statistic") if with_annotations else ():  # annotation-only results get them as the table instead
            group = a.metadata.get("group")
            value = a.data["value"]
            f.write(f"# {f'{group}.{a.name}' if group else a.name} = {'' if value is None else value!r}\n")
    for array in list(dataset.axes.values()) + list(dataset.data.values()):
        if array.label:
            f.write(f"# label {array.name}: {_oneline(array.label)}\n")
    for a in dataset.annotations if with_annotations else ():
        if (a.kind == "parameter" and md.get("model")) or a.kind == "statistic":
            continue  # already written above, human-readable
        f.write(f"# annotation: {json.dumps(_sanitize(a.to_dict()), ensure_ascii=False)}\n")


def save_json(path: str, datasets, extra: dict | None = None) -> None:
    """Lossless export of one DataSet or a list of them (e.g. store.all() -- a complete session). `extra` adds header fields next to format/version (readers ignore unknown ones)."""
    if isinstance(datasets, DataSet):
        datasets = [datasets]
    datasets = list(datasets)
    if not datasets:
        raise ValueError("Nothing to save -- no datasets given.")
    doc = {"format": JSON_FORMAT, "version": JSON_VERSION, **(extra or {}), "datasets": [_dataset_doc(d) for d in datasets]}
    with atomic_open(path, newline=None) as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, allow_nan=False)
        f.write("\n")


def _dataset_doc(dataset: DataSet) -> dict:
    """DataSet.to_dict() with the free-form parts made JSON-safe (the bulk number lists are left alone -- DataArray.to_dict already encodes them)."""
    doc = dataset.to_dict()
    doc["metadata"] = _sanitize(doc["metadata"])
    for array in doc["axes"] + doc["data"]:
        array["metadata"] = _sanitize(array["metadata"])
    doc["annotations"] = [_sanitize(a) for a in doc["annotations"]]
    return doc


def _sanitize(obj):
    """Makes free-form metadata JSON-safe: tuples -> lists, non-finite floats -> null, unknown objects -> str()."""
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    return str(obj)
