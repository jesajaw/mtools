"""
Hypothesis Testing -- not implemented yet.
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Hypothesis Testing"
TOOL_DESCRIPTION = "t-tests, ANOVA, Chi-Square tests -- evaluate hypotheses and determine significance (p-values). -- not implemented yet."


class ToolWindow(ComputeToolWindow):
    input_label = "Input file"
    input_filetypes = (("All files", "*.*"),)

    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, data):
        raise NotImplementedError("Hypothesis Testing not implemented yet.")


def open_window(parent) -> None:
    ToolWindow(parent)
