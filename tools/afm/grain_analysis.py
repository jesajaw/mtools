"""
Grain Analysis -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Grain Analysis"
TOOL_DESCRIPTION = "Segmentation and measurement of individual surface grains (size, height, volume) via thresholding. -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Grain Analysis not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
