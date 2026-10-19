"""
Crash recovery for results that only exist in memory.

While a session holds unsaved computed results (store.unsaved()), the whole workspace is mirrored to ``autosave.json`` (mtools JSON, atomically written, in settings.config_dir()). Once everything is saved, or the app is closed on purpose, the file is removed -- so a file that exists at the next start means the last session ended with unsaved work, and the app can offer to restore it.

* AutoSaver.tick() is what the GUI calls from a timer; it only writes when the workspace changed since the last write.
* pending() / restore() / discard() are the start-up side.
* Workspaces larger than MAX_VALUES numbers are not mirrored (a periodic multi-megapixel dump would stall the UI) -- tick() then reports it through AutoSaver.skipped.
"""

import json
from datetime import datetime
from pathlib import Path

from data import loaders, savers, settings, store
from data.dataset import DataSet

FILENAME = "autosave.json"
MAX_VALUES = 5_000_000


def path() -> Path:
    return settings.config_dir() / FILENAME


def _count_values(datasets) -> int:
    total = 0
    for ds in datasets:
        for a in list(ds.axes.values()) + list(ds.data.values()):
            n = len(a)
            total += n * (len(a.values[0]) if a.ndim == 2 and a.values else 1)
    return total


def write(datasets: list[DataSet] | None = None) -> bool:
    """Mirrors `datasets` (default: the whole workspace) to the autosave file. False if too large or not writable -- never raises."""
    datasets = store.all() if datasets is None else datasets
    if not datasets or _count_values(datasets) > MAX_VALUES:
        return False
    try:
        path().parent.mkdir(parents=True, exist_ok=True)
        savers.save_json(str(path()), datasets, extra={"autosave": True, "saved_at": datetime.now().isoformat(timespec="seconds")})
        return True
    except (OSError, ValueError, TypeError):
        return False


def discard() -> None:
    try:
        path().unlink()
    except OSError:
        pass


def pending() -> dict | None:
    """Info about a leftover autosave ({'saved_at', 'n_datasets', 'n_unsaved'}) or None if there is none (or it is unreadable)."""
    try:
        text, _ = loaders.read_text(str(path()))
        doc = json.loads(text)
        datasets = loaders.datasets_from_json(text)
    except (OSError, ValueError):
        return None
    unsaved = [d for d in datasets if d.source_tool and "source_path" not in d.metadata]
    return {"saved_at": doc.get("saved_at"), "n_datasets": len(datasets), "n_unsaved": len(unsaved)}


def restore() -> list[DataSet]:
    """Puts the autosaved datasets back into the workspace (computed results stay marked as unsaved) and removes the file."""
    text, _ = loaders.read_text(str(path()))
    datasets = loaders.datasets_from_json(text)  # not load_datasets(): that would stamp source_path and make results look saved
    store.add_many(datasets)
    discard()
    return datasets


class AutoSaver:
    """Call tick() periodically (e.g. every 30 s from the GUI loop).

    It only ever deletes a file it wrote itself. A leftover file from a crashed session is therefore never lost by accident: if the user ignores the restore offer, the first write of this session moves it aside to ``autosave.previous.json`` instead of overwriting it.
    """

    def __init__(self):
        self._written_revision = None
        self._owns = False    # True once this instance wrote the current autosave file
        self.skipped = False  # True while unsaved work exists that is too large to mirror

    def tick(self) -> bool:
        """Returns True if the autosave file was (re)written."""
        if not store.unsaved():
            self.skipped = False
            self.close()
            return False
        if store.revision() == self._written_revision:
            return False
        if not self._owns and path().exists():
            try:
                path().replace(path().with_name("autosave.previous.json"))
            except OSError:
                pass
        ok = write()
        self.skipped = not ok and bool(store.all())
        self._owns = self._owns or ok
        self._written_revision = store.revision() if ok else None
        return ok

    def close(self) -> None:
        """Nothing left to recover (everything saved, or the user chose to quit): remove the file this instance wrote."""
        if self._owns:
            discard()
        self._owns = False
        self._written_revision = None
