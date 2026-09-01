"""
Descriptive Statistics -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Descriptive Statistics"
TOOL_DESCRIPTION = "Central tendency (mean, median, mode) and dispersion (variance, standard deviation, range, IQR). -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("Descriptive Statistics not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
