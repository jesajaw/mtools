"""Points-file loading for the fitting tools -- thin wrapper around
the shared, cross-category loader in data/loaders.py (not a tool
itself, leading underscore -- core.registry skips it)."""

from data.loaders import load_points

__all__ = ["load_points"]