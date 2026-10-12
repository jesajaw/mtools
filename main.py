"""
Entry point. Discovers the tools under tools/ (core.discover_tools) and opens the main window (ui.app.MainWindow), which builds a selection grid with one cell per tool.

To add a new tool: create a module under tools/ (TOOL_NAME, TOOL_DESCRIPTION, open_window) -- neither this file nor the ui package needs to be touched.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk

import tools
from core import discover_tools
from ui import style
from ui.app import MainWindow


def main() -> None:
    style.enable_dpi_awareness()
    root = tk.Tk()
    MainWindow(root, discover_tools(tools))
    root.mainloop()


if __name__ == "__main__":
    main()
