"""
DataSet -- shared envelope every tool reads from and writes to the workspace through.
- holds one or more named DataArrays
- means a tool can keep both an original and a derived quantity around without losing either
- axes (x/y/...) are just DataArrays too, kept separately so a tool / Visualize can tell "this is a coordinate" from "this is a value" without guessing.
"""

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataArray:
    """
    A single named, unit-aware quantity.

    values -- a plain Python list (1D) or list of tuples/lists
        (higher-dimensional) -- whatever shape `dims` describes. No
        numpy; this is exactly the kind of data data/loaders.py
        already produces.
    name -- short identifier tools look this array up by (e.g.
        "height", "x", "slope").
    dims -- names of the array's dimensions, e.g. ("x",) for a 1D
        series or ("y", "x") for a 2D grid. Empty for a scalar.
    units -- e.g. "nm", "s" -- optional, purely informational.
    label -- human-readable description (e.g. "Surface height"),
        distinct from `name` which is the lookup key.
    uncertainty -- same shape as `values`, or None -- e.g. for
        error_propagation/ results. Optional and separate from
        `values` rather than a parallel array under its own name, so
        a tool doesn't have to know the naming convention to find it.
    metadata -- free-form extras that don't fit elsewhere.
    """
    values: Any
    name: str
    dims: tuple[str, ...] = ()
    units: str | None = None
    label: str | None = None
    uncertainty: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Annotation:
    """
    One record in a *list* of similarly-shaped items -- a detected
    peak, a grain, an optimization step -- where a DataArray (one
    uniform shape) doesn't fit: each item has a handful of named
    fields (a peak's center/width/amplitude; a grain's area/
    perimeter/centroid), and there can be any number of them.

    kind -- what this annotation IS, e.g. "peak", "grain", "step" --
        a downstream tool or Visualize groups/filters by this.
    data -- the item's own fields, free-form (e.g.
        {"center": 532.4, "width": 1.2, "amplitude": 0.8}).
    name -- optional human-readable label for this one item (e.g.
        "Peak 1"). Not required -- most annotations are identified by
        position in the list, not by name.
    metadata -- free-form extras that don't belong in `data`.
    """
    kind: str
    data: dict[str, Any]
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSet:
    """
    Canonical data container shared between tools.

    data -- named DataArrays holding actual values (e.g. "height",
        "slope", "intercept").
    axes -- named DataArrays that describe a coordinate/dimension
        rather than a value (e.g. "x", "y") -- kept separate from
        `data` so a tool or a future Visualize doesn't have to guess
        which is which.
    annotations -- a list of Annotations for results that are
        naturally a list of items rather than a uniform array (see
        Annotation above).
    metadata -- free-form extras about the dataset as a whole (not
        any one array) -- e.g. instrument, sample name.
    name -- optional human-readable label, shown in the main
        window's "Data" status (a filename, or "Output of Linear
        Regression").
    source_tool -- TOOL_NAME of whichever tool produced this (None
        for data loaded straight from a file).
    """
    data: dict[str, DataArray] = field(default_factory=dict)
    axes: dict[str, DataArray] = field(default_factory=dict)
    annotations: list[Annotation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    source_tool: str | None = None

    def get(self, key: str) -> DataArray:
        """Looks a named array up in `data` first, then `axes` --
        raises KeyError with a clear message if it's in neither."""
        if key in self.data:
            return self.data[key]
        if key in self.axes:
            return self.axes[key]
        raise KeyError(f"'{key}' not found in this DataSet's data or axes.")

    def add(self, array: DataArray) -> None:
        """Adds/replaces a named array in `data`."""
        self.data[array.name] = array

    def annotations_of(self, kind: str) -> list[Annotation]:
        """Every annotation of a given kind, e.g. all "peak" entries."""
        return [a for a in self.annotations if a.kind == kind]

    def copy(self) -> "DataSet":
        """A deep copy -- tools should build a new DataSet (or copy()
        an existing one and add to the copy) rather than mutating the
        one they were given, so a chain of results stays trustworthy."""
        return copy.deepcopy(self)