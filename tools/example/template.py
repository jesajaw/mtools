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