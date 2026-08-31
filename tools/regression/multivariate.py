"""
Multivariate regression -- not started yet (original source was just
a comment, "#nä"). Placeholder so it shows up in the GUI.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Multivariate"
TOOL_DESCRIPTION = "Not started yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("Multivariate regression not started yet.")


def open_window(parent) -> None:
    ToolWindow(parent)