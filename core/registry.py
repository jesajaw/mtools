"""
Scans tools/ two levels deep: category subfolders and individual tool modules
main does not need to know any category or tool by name -- adding a new tool means adding a module to an existing category folder, or a new category folder plus module, following the schema in tool_base.py
"""

import importlib, os, pkgutil, sys, traceback
from types import ModuleType
from core.tool_base import ToolEntry

REQUIRED_ATTRS = ("TOOL_NAME", "TOOL_DESCRIPTION", "open_window")


def discover_tools(tools_package: ModuleType) -> list[ToolEntry]:
    """
    Iterates over category sub-packages of tools_package, then over the tool modules inside each
    Categories or tools that fail to import or are missing attributes are skipped and logged
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

        category_name = category_info.name.rsplit(".", 1)[-1]
        entries.extend(_discover_tools_in_category(category_module, category_name, subcategory=None))

    entries.sort(key=lambda e: (e.category.lower(), e.name.lower()))
    return entries


def _ensure_project_root_on_path(tools_package: ModuleType) -> None:
    """
    Tool modules import shared modules at the project level, such as `mathlib.py`, using a simple command: `import mathlib`.
    This works only if the project directory is in `sys.path`—which is guaranteed when `python main.py` is run from the project directory, but not necessarily when another file is run or debugged directly.
    As a result, detection works in both cases.
    """
    tools_dir = os.path.dirname(os.path.abspath(tools_package.__file__))
    project_root = os.path.dirname(tools_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def _discover_tools_in_category(category_module: ModuleType, category_name: str, subcategory: str | None) -> list[ToolEntry]:
    """
    Recursively walks a category package: a tool module found directly inside is registered with the given subcategory (None at the top level);
    a sub-package found inside (e.g. tools/fitting/regression/) is walked the same way, one level deeper, with its own folder name as the subcategory --
    no depth limit, though the UI only ever renders one level of nesting. category_name is always the top-level folder, unchanged no matter how deep a tool lives.
    """
    entries: list[ToolEntry] = []

    for tool_info in pkgutil.iter_modules(category_module.__path__, category_module.__name__ + "."):
        module_basename = tool_info.name.rsplit(".", 1)[-1]
        if module_basename.startswith("_"):
            continue  # private helper module/package (e.g. _points.py), not a tool

        if tool_info.ispkg:
            try:
                subcategory_module = importlib.import_module(tool_info.name)
            except Exception:
                print(f"[mtools] Could not load subcategory '{tool_info.name}':")
                traceback.print_exc()
                continue
            entries.extend(_discover_tools_in_category(subcategory_module, category_name, subcategory=module_basename))
            continue

        try:
            module = importlib.import_module(tool_info.name)
        except Exception:
            print(f"[mtools] Could not load tool module '{tool_info.name}':")
            traceback.print_exc()
            continue

        if category_name == "example":
            continue

        missing = [a for a in REQUIRED_ATTRS if not hasattr(module, a)]
        if missing:
            print(f"[mtools] Skipping tool module '{tool_info.name}', missing attributes: {missing}")
            continue

        entries.append(ToolEntry(
            module_name=tool_info.name,
            category=category_name,
            subcategory=subcategory,
            name=module.TOOL_NAME,
            description=module.TOOL_DESCRIPTION,
            open_window=module.open_window,
        ))
    return entries