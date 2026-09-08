"""
Shared in-memory data workspace: every DataSet added this session, kept in order -- not just one overwritable slot. A tool's output becomes part of the workspace's history rather than replacing whatever was there, so a chain of results stays inspectable, not just the very last step.

Still process-global by design -- one workspace for the whole running app, mirroring "the data" as a single shared concept rather than a per-tool file.
"""

from data.dataset import DataSet

_history: list[DataSet] = []


def is_loaded() -> bool:
    return bool(_history)


def add(dataset: DataSet) -> None:
    # Adds a DataSet to the workspace
    _history.append(dataset)


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