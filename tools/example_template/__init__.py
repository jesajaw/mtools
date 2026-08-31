"""
Registration for the 'example_template' -- template for all further tools. Every tool package needs exactly these three names, main.py finds the rest automatically (see core/registry.py).
"""

from .gui import ToolWindow

TOOL_NAME = "Example Tool"
TOOL_DESCRIPTION = "Example A to B from a file."


def open_window(parent) -> None:
    ToolWindow(parent)
