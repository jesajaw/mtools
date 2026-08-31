"""
Exponential regression -- not implemented yet (y = a*e^(b*x) + c).
Placeholder so it shows up in the GUI; swap compute() for a real
nonlinear fit once that's worked out.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Exponential"
TOOL_DESCRIPTION = "y = a*e^(b*x) + c -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("Exponential fit not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)