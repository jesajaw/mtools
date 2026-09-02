"""
Root Finding -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Root Finding"
TOOL_DESCRIPTION = "Find roots of a function (bisection, Newton's method). -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Root Finding not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
