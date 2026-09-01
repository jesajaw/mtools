"""
ODE Solver -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "ODE Solver"
TOOL_DESCRIPTION = "Solve ordinary differential equations. -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("ODE Solver not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
