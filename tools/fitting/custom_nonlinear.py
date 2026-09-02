"""
Custom non-linear curve fitting -- not implemented yet. Meant for
arbitrary user-supplied model functions (beyond the specific
linear/polynomial/exponential/logarithmic cases already covered),
fit via general nonlinear least squares.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Custom Non-linear Fit"
TOOL_DESCRIPTION = "Fit an arbitrary user-defined model function -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Points file"
    input_filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Custom non-linear fitting not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
