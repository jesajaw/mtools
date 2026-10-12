"""
Shared UI pieces of the statistics tools (private helper, skipped by tool discovery).
"""

from ui.widgets import make_mode_cell

CELL_HEIGHT = 40


def mode_cell(parent, modes: list[tuple], prefix: str, on_change=None):
    """The standard single-line mode picker used by every statistics tool: click to cycle through `modes` = [(key, label), ...]. cell.mode() returns the current key."""
    cell = make_mode_cell(parent, modes=modes, on_change=on_change, label_prefix=prefix, height=CELL_HEIGHT)
    cell.pack(fill="x", pady=(0, 8))
    return cell


def samples_cell(parent, on_change=None):
    """Picks how two independent samples are laid out in the loaded data: as two columns (x | y), or as one value column x with the group label in y (needed when the groups differ in size, since loaded data is rectangular)."""
    return mode_cell(parent, [("columns", "columns x | y"), ("grouped", "x values, groups in y")], "Samples: ", on_change)
