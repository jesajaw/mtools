"""
Peak Fitting -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Peak Fitting"
TOOL_DESCRIPTION = "Spectral analysis and peak fitting. -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Peak Fitting not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
