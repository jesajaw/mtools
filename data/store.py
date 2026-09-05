"""
Shared in-memory data workspace ("current data set" for the running app).
One tool's output can become the next tool's input without a file round-trip.

This is process-global, on purpose -- there's exactly one workspace for the whole app, mirroring the single "Input | Output" bar in the main window.
"""

_data = None
_label: str | None = None


def is_loaded() -> bool:
    return _data is not None


def get():
    # Returns the current data, or None if nothing is loaded
    return _data


def label() -> str | None:
    # description of the current data (e.g. a filename, or "Output of Geometry"), or None if nothing is loaded
    return _label


def set(new_data, new_label: str) -> None:
    global _data, _label
    _data = new_data
    _label = new_label


def clear() -> None:
    global _data, _label
    _data = None
    _label = None
