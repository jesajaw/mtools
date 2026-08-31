"""
Scans the tools/ package and imports each sub-package. main.py does not need to know any tool by name -- adding a new tool means adding a new folder under tools/ with an __init__.py following the schema in tool_base.py, no edit to main.py required.
"""

import importlib, pkgutil, traceback
from types import ModuleType
from core.tool_base import ToolEntry

REQUIRED_ATTRS = ("TOOL_NAME", "TOOL_DESCRIPTION", "open_window")


def discover_tools(tools_package: ModuleType) -> list[ToolEntry]:
    """
    Iterates over all sub-packages of tools_package, imports them and collects the ones that satisfy the tool interface.
    Modules that fail to import or are missing attributes are skipped and logged to the console instead of crashing main.py.
    """
    entries: list[ToolEntry] = []

    for info in pkgutil.iter_modules(tools_package.__path__, tools_package.__name__ + "."):
        if not info.ispkg:
            continue
        try:
            module = importlib.import_module(info.name)
        except Exception:
            print(f"[mtools] Could not load tool module '{info.name}':")
            traceback.print_exc()
            continue

        missing = [a for a in REQUIRED_ATTRS if not hasattr(module, a)]
        if missing:
            print(f"[mtools] Skipping tool module '{info.name}', missing attributes: {missing}")
            continue

        entries.append(ToolEntry(module_name=info.name, name=module.TOOL_NAME, description=module.TOOL_DESCRIPTION, open_window=module.open_window))

    entries.sort(key=lambda e: e.name.lower())
    return entries
