"""
Quadratic regression -- not implemented yet (y = a*x^2 + b*x + c).
Placeholder so it shows up in the GUI. NOTE: this overlaps with
'Polynomial' (tools/regression/polynomial.py), which already does
exactly this fit via normal equations -- worth deciding whether
'Quadratic' stays a separate tool or gets folded into 'Polynomial'.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Quadratic"
TOOL_DESCRIPTION = "y = a*x^2 + b*x + c -- not implemented yet (see note: overlaps with Polynomial)."


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError("Quadratic fit not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
