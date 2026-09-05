"""
Interface that every tool module must provide so main can find and display it automatically.
Tools live in category subfolders under tools/, one plain .py file per tool.
Category folders themselves just need an __init__.py to be a package -- no tool metadata there.

A tool module needs:

    TOOL_NAME: str            # display name in main window
    TOOL_DESCRIPTION: str     # descitopn in main window
    def open_window(parent) -> None
        # opens this tool's 2nd window (Toplevel)

See tools/example/template.py for a template.
"""

from dataclasses import dataclass
from typing import Callable, Protocol


class ToolModule(Protocol):
    TOOL_NAME: str
    TOOL_DESCRIPTION: str
    open_window: Callable[..., None]


@dataclass
class ToolEntry:
    # Metadata for a discovered tool, collected by the registry.
    module_name: str
    category: str
    name: str
    description: str
    open_window: Callable[..., None]
