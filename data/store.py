"""
Shared in-memory data workspace: every DataSet added this session, kept in order -- not just one overwritable slot. A tool's output becomes part of the workspace's history rather than replacing whatever was there, so a chain of results stays inspectable, not just the very last step.

Still process-global by design -- one workspace for the whole running app, mirroring "the data" as a single shared concept rather than a per-tool file.

Unsaved work: results computed by a tool exist only in memory until they are saved. The store tracks which ones (unsaved()) so the main window can warn before the app closes; data that came from a file is never "unsaved", and savers/main call mark_saved() after a successful export.
"""

import traceback

from data.dataset import DataSet

_history: list[DataSet] = []
_unsaved: list[DataSet] = []   # identity-tracked subset of _history: computed results not yet exported
_listeners: list = []
_current: DataSet | None = None  # explicit selection (see select()); None = the latest dataset
_revision = 0                    # bumped on every change -- lets autosave notice "something changed" cheaply


def subscribe(callback) -> None:
    # callback() is called after every change (add / replace / remove / clear / saved) -- lets the main window and open tool windows keep their status text in sync
    if callback not in _listeners:
        _listeners.append(callback)


def unsubscribe(callback) -> None:
    if callback in _listeners:
        _listeners.remove(callback)


def revision() -> int:
    # Counter that changes whenever the workspace does (add / replace / remove / rename / select / clear / saved)
    return _revision


def _notify() -> None:
    global _revision
    _revision += 1
    for callback in list(_listeners):
        try:
            callback()
        except Exception:
            traceback.print_exc()


def _track(dataset: DataSet) -> None:
    if dataset.source_tool and "source_path" not in dataset.metadata and not any(d is dataset for d in _unsaved):
        _unsaved.append(dataset)


def _untrack(dataset: DataSet) -> None:
    _unsaved[:] = [d for d in _unsaved if d is not dataset]


def is_loaded() -> bool:
    return bool(_history)


def add(dataset: DataSet) -> None:
    # Adds a DataSet to the workspace; a new dataset (e.g. a tool's result) always becomes the current one
    global _current
    _current = None
    _history.append(dataset)
    _track(dataset)
    _notify()


def add_many(datasets) -> None:
    # Adds several at once (e.g. a whole workspace file) with a single notification
    global _current
    _current = None
    for dataset in datasets:
        _history.append(dataset)
        _track(dataset)
    _notify()


def replace(old: DataSet, new: DataSet) -> None:
    # Swaps `old` for `new` in place (re-computing in the same tool window shouldn't pile up stale results); adds `new` if `old` is gone
    global _current
    for i, existing in enumerate(_history):
        if existing is old:
            _history[i] = new
            if _current is old:
                _current = new
            _untrack(old)
            _track(new)
            _notify()
            return
    add(new)


def remove(dataset: DataSet) -> None:
    # Drops one DataSet from the workspace (no-op if it isn't there)
    global _current
    if _current is dataset:
        _current = None
    before = len(_history)
    _history[:] = [d for d in _history if d is not dataset]
    _untrack(dataset)
    if len(_history) != before:
        _notify()


def get() -> DataSet | None:
    # The current DataSet -- what tools compute on and "Save" exports: the one picked with select(), otherwise the most recently added
    if _current is not None and any(d is _current for d in _history):
        return _current
    return _history[-1] if _history else None


def select(dataset: DataSet) -> None:
    # Makes the given dataset (which must be in the workspace) the current one until something new is added
    global _current
    if not any(d is dataset for d in _history):
        raise ValueError("This dataset is not in the workspace.")
    _current = dataset
    _notify()


def is_current(dataset: DataSet) -> bool:
    return get() is dataset


def rename(dataset: DataSet, name: str) -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("The name must not be empty.")
    dataset.name = name
    _notify()


def all() -> list[DataSet]:
    # Every DataSet added this session, oldest first
    return list(_history)


def latest_with(key: str) -> DataSet | None:
    # The most recently added DataSet that actually has `key` among its data or axes arrays
    for dataset in reversed(_history):
        if key in dataset.data or key in dataset.axes:
            return dataset
    return None


def label() -> str | None:
    # Convenience passthrough -- the most recent DataSet's name, or None if nothing is loaded (or it has none)
    current = get()
    return current.name if current else None


def unsaved() -> list[DataSet]:
    # Computed results that have not been exported yet
    return list(_unsaved)


def mark_saved(datasets) -> None:
    # Call after a successful export of `datasets` (a DataSet or a list of them)
    for dataset in ([datasets] if isinstance(datasets, DataSet) else datasets):
        _untrack(dataset)
    _notify()


def clear() -> None:
    global _current
    _current = None
    _history.clear()
    _unsaved.clear()
    _notify()
