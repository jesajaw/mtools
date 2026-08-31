"""
Scans tools/ two levels deep: category subfolders (e.g.
tools/regression/) and, inside each, individual tool modules (e.g.
linear.py). main.py does not need to know any category or tool by
name -- adding a new tool means adding a module to an existing
category folder, or a new category folder plus module, following the
schema in tool_base.py. No edit to main.py required.
"""

import importlib, os, pkgutil, sys, traceback
from types import ModuleType
from core.tool_base import ToolEntry

REQUIRED_ATTRS = ("TOOL_NAME", "TOOL_DESCRIPTION", "open_window")


def discover_tools(tools_package: ModuleType) -> list[ToolEntry]:
    """
    Iterates over category sub-packages of tools_package, then over
    the tool modules inside each. Categories or tools that fail to
    import or are missing attributes are skipped and logged to the
    console instead of crashing main.py.
    """
    _ensure_project_root_on_path(tools_package)
    entries: list[ToolEntry] = []

    for category_info in pkgutil.iter_modules(tools_package.__path__, tools_package.__name__ + "."):
        if not category_info.ispkg:
            continue  # only category folders (packages) live directly under tools/
        try:
            category_module = importlib.import_module(category_info.name)
        except Exception:
            print(f"[mtools] Could not load category '{category_info.name}':")
            traceback.print_exc()
            continue

        entries.extend(_discover_tools_in_category(category_module))

    entries.sort(key=lambda e: (e.category.lower(), e.name.lower()))
    return entries


def _discover_tools_in_category(category_module: ModuleType) -> list[ToolEntry]:
    entries: list[ToolEntry] = []
    category_name = category_module.__name__.rsplit(".", 1)[-1]

    for tool_info in pkgutil.iter_modules(category_module.__path__, category_module.__name__ + "."):
        if tool_info.ispkg:
            continue  # tools are single modules, not sub-packages
        module_basename = tool_info.name.rsplit(".", 1)[-1]
        if module_basename.startswith("_"):
            continue  # private helper module (e.g. _points.py), not a tool
        try:
            module = importlib.import_module(tool_info.name)
        except Exception:
            print(f"[mtools] Could not load tool module '{tool_info.name}':")
            traceback.print_exc()
            continue

        missing = [a for a in REQUIRED_ATTRS if not hasattr(module, a)]
        if missing:
            print(f"[mtools] Skipping tool module '{tool_info.name}', missing attributes: {missing}")
            continue

        entries.append(ToolEntry(
            module_name=tool_info.name,
            category=category_name,
            name=module.TOOL_NAME,
            description=module.TOOL_DESCRIPTION,
            open_window=module.open_window,
        ))
    return entries

def _ensure_project_root_on_path(tools_package: ModuleType) -> None:
    """Tool modules (e.g. tools/regression/linear.py) import shared,
    project-root-level modules like mathlib.py via a plain `import
    mathlib`. That only resolves if the project root is on sys.path --
    guaranteed when running `python main.py` from the project root,
    but not necessarily when some other file is run/debugged directly.
    This makes discovery work either way."""
    tools_dir = os.path.dirname(os.path.abspath(tools_package.__file__))
    project_root = os.path.dirname(tools_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)