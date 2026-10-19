"""
Tiny persistent settings store (JSON), e.g. the folder the file dialogs reopen in. Best effort by design: a missing, unreadable or corrupt file just means defaults, and a failed write never raises -- settings must never get in the way of the actual work.

Location: $MTOOLS_HOME if set, else %APPDATA%/mtools (Windows), else $XDG_CONFIG_HOME/mtools or ~/.config/mtools.
"""

import json
import os
import sys
from pathlib import Path


def config_dir() -> Path:
    if os.environ.get("MTOOLS_HOME"):
        return Path(os.environ["MTOOLS_HOME"])
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "mtools"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "mtools"


def _file() -> Path:
    return config_dir() / "settings.json"


def load() -> dict:
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value) -> bool:  # noqa: A001 -- reads naturally as settings.set(...)
    """Stores one value. Returns False (and changes nothing) if the settings file can't be written."""
    from data import savers  # late: savers imports loaders, keep this module import-light

    data = load()
    if data.get(key) == value:
        return True
    data[key] = value
    try:
        config_dir().mkdir(parents=True, exist_ok=True)
        with savers.atomic_open(str(_file()), newline=None) as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
        return True
    except (OSError, TypeError, ValueError):
        return False
