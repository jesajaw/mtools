"""
Logarithmic regression -- not implemented yet (y = a*ln(x) + b).
Placeholder so it shows up in the GUI.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Logarithmic"
TOOL_DESCRIPTION = "y = a*ln(x) + b -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("Logarithmic fit not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
