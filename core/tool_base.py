"""
Interface that every tool package under tools/<name>/__init__.py must provide so main.py can find and display it automatically.

A tool package needs the following in its __init__.py:

    TOOL_NAME: str            # display name in the main window
    TOOL_DESCRIPTION: str     # one or two sentences, plain text, no tooltips
    def open_window(parent) -> None
        # opens this tool's 2nd window (Toplevel)

See tools/example_linear_fit/ for a template.
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
    name: str
    description: str
    open_window: Callable[..., None]
