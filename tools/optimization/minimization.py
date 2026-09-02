"""
Minimization -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Minimization"
TOOL_DESCRIPTION = "Minimize a function (e.g. gradient descent). -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Minimization not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
