"""
Data Preprocessing -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Data Preprocessing"
TOOL_DESCRIPTION = "Handling missing data, outlier detection, normalization, and standardization. -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Data Preprocessing not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
