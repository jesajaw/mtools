"""
The load/save workflow in one place, free of any GUI code (so it is testable and every window behaves the same):

* load_file(path)  -- file -> workspace (a text file adds one DataSet, an mtools .json adds all datasets it holds)
* save_file(path, ...) -- workspace/result -> file, by extension (.csv / .tsv / .json), and bookkeeping which results are saved now
* OPEN_FILETYPES / SAVE_FILETYPES -- the lists for the file dialogs, derived from what loaders/savers support
"""

import re
from pathlib import Path

from data import loaders, savers, store
from data.dataset import DataSet

OPEN_FILETYPES = (
    ("All supported", " ".join(f"*{e}" for e in loaders.SUPPORTED_EXTENSIONS)),
    ("Text tables", " ".join(f"*{e}" for e in loaders.TEXT_EXTENSIONS)),
    ("mtools workspace (JSON)", "*.json"),
    ("NumPy array", "*.npy"),
    ("All files", "*.*"),
)

SAVE_FILETYPES = (
    ("CSV", "*.csv"),
    ("Tab separated", "*.tsv"),
    ("mtools JSON (lossless, whole workspace)", "*.json"),
)

_last_saved = {"text": None}


def load_file(path: str, **options) -> list[DataSet]:
    """Loads `path` into the workspace and returns the added datasets. Raises ValueError/OSError with a readable message -- nothing is added on failure."""
    try:
        datasets = loaders.load_datasets(path, **options)
    except UnicodeError as e:  # read_text() should prevent this, but never show a codec traceback to the user
        raise ValueError(f"Could not decode the file: {e}") from None
    store.add_many(datasets)
    return datasets


def save_file(path: str, dataset: DataSet | None = None, whole_workspace: bool = False) -> str:
    """Writes to `path` (format from the extension). `dataset` defaults to the latest one in the workspace. A .json file holds the whole workspace when `whole_workspace` is true, otherwise only `dataset`. Returns a short status text; on failure the exception propagates and an existing file at `path` stays untouched."""
    if not path:
        raise ValueError("No file name given.")
    if Path(path).suffix == "":
        path += ".csv"
    dataset = dataset or store.get()
    if dataset is None:
        raise ValueError("No data currently loaded.")

    is_json = Path(path).suffix.lower() == ".json"
    group = store.all() if (is_json and whole_workspace) else [dataset]
    savers.save_dataset(path, dataset, datasets=group if is_json else None)

    what = f"{len(group)} dataset(s)" if len(group) > 1 else (f"{dataset.n_rows} row(s)" if dataset.n_rows is not None else "annotations")
    _last_saved["text"] = f"saved {Path(path).name} ({what})"
    store.mark_saved(group)  # also notifies listeners -- they pick up last_saved_text()
    return _last_saved["text"]


def last_saved_text() -> str | None:
    return _last_saved["text"]


def suggest_filename(dataset: DataSet | None, ext: str = ".csv") -> str:
    """A safe default file name from the dataset's name, e.g. 'Linear (fit of data.csv)' -> 'Linear_fit_of_data'."""
    base = Path(dataset.name).stem if dataset and dataset.name else "data"
    base = re.sub(r"[^\w.-]+", "_", base).strip("_.") or "data"
    return base + ext
