"""
Example tool: one file per tool, living inside a category folder
(see tools/regression/ for real ones). To start a new tool: copy
this file into an existing or new category folder, adjust
TOOL_NAME/TOOL_DESCRIPTION, and implement compute() (and
format_result()/save_result() if the default str()/plain-text
behavior isn't enough).
"""

from theme.widgets import ComputeToolWindow

TOOL_NAME = "Example Tool"
TOOL_DESCRIPTION = "Example A to B from a file."


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        super().__init__(parent, title=TOOL_NAME, description=TOOL_DESCRIPTION)

    def compute(self, path: str):
        raise NotImplementedError(
            "compute() is a placeholder -- implement your tool's logic here."
        )


def open_window(parent) -> None:
    ToolWindow(parent)
