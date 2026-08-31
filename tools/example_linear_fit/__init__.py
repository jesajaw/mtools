"""
Registration for the 'Linear Regression' tool -- template for all further tools. Every tool package needs exactly these three names, main.py finds the rest automatically (see core/registry.py).
"""

from .gui import ToolWindow

TOOL_NAME = "Linear Regression"
TOOL_DESCRIPTION = "Fits y = a*x + b to (x, y) values from a CSV file (least squares)."


def open_window(parent) -> None:
    ToolWindow(parent)
