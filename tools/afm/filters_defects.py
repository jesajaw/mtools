"""
Filters & Defects -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Filters & Defects"
TOOL_DESCRIPTION = "Noise reduction (Gaussian, median) and correction of measurement artifacts like line scars or bad data points. -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Filters & Defects not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
