"""
Shared in-memory data workspace: every DataSet added this session, kept in order -- not just one overwritable slot. A tool's output becomes part of the workspace's history rather than replacing whatever was there, so a chain of results stays inspectable, not just the very last step.

Still process-global by design -- one workspace for the whole running app, mirroring "the data" as a single shared concept rather than a per-tool file.
"""

import traceback

from data.dataset import DataSet

_history: list[DataSet] = []
_listeners: list = []


def subscribe(callback) -> None:
    # callback() is called after every change (add / replace / clear) -- lets the main window and open tool windows keep their status text in sync
    if callback not in _listeners:
        _listeners.append(callback)


def unsubscribe(callback) -> None:
    if callback in _listeners:
        _listeners.remove(callback)


def _notify() -> None:
    for callback in list(_listeners):
        try:
            callback()
        except Exception:
            traceback.print_exc()


def is_loaded() -> bool:
    return bool(_history)


def add(dataset: DataSet) -> None:
    # Adds a DataSet to the workspace
    _history.append(dataset)
    _notify()


def replace(old: DataSet, new: DataSet) -> None:
    # Swaps `old` for `new` in place (re-computing in the same tool window shouldn't pile up stale results); adds `new` if `old` is gone
    for i, existing in enumerate(_history):
        if existing is old:
            _history[i] = new
            _notify()
            return
    add(new)


def get() -> DataSet | None:
    # most recently added DataSet
    return _history[-1] if _history else None


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


def clear() -> None:
    _history.clear()
    _notify()