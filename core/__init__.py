"""Core discovery/interface logic shared by main.py and the tools."""

from .registry import discover_tools
from .tool_base import ToolEntry

__all__ = ["discover_tools", "ToolEntry"]