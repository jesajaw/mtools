"""
Data preprocessing: prepares the workspace data for the next tool. The result REPLACES the data as the newest workspace entry (same columns, transformed), so tools chain: e.g. Preprocessing -> Linear fit. The numbers needed to undo a transformation (mean/std, min/max) are listed in the result.

Pick the operation with the Operation cell and the columns it acts on with the Columns cell ("all" = every column including e.g. fit/residual of a fit result; x, y or z = just that one):

- Standardize        (v - mean) / std, sample std (n-1)  -> mean 0, std 1
- Min-max scaling    linear map of min..max onto the target range (default 0, 1)
- Center             v - mean
- Log transform      ln(v + c) with offset c (default 0); every value + c must be positive
- Moving average     centered window of the given odd size, shrinking at both ends; assumes the row order is meaningful
- Remove outliers    drops every ROW in which a selected column lies outside [Q1 - k*IQR, Q3 + k*IQR] (Tukey's rule, default k = 1.5); all columns stay aligned
- Sort rows          ascending by the selected column (all = x); all columns are reordered together

Arrays that are not plain numeric columns of the same length are dropped from the result.
"""

import copy
import math

from . import _basic as b
from . import _ui
from data import results
from data.dataset import DataSet
from theme.widgets import ComputeToolWindow, ParameterBox

TOOL_NAME = "Data Preprocessing"
TOOL_DESCRIPTION = "Standardize, scale, center, log-transform, smooth, sort or remove outliers -- the result becomes the new data for the next tool."
TOOL_INSTRUCTIONS = "Click the cells to pick an operation and the columns it acts on, enter its parameter if it has one, load the data via the main window, then click Compute -- the transformed data replaces the data for the next tool; save or visualize as you wish."
RESULT_FORMAT = "rows before -> after,\nand the numbers needed to undo the transformation"

# key -> (label, parameter caption or None, parameter default)
OPERATIONS = {
    "zscore": ("Standardize (z-score)", None, ""),
    "minmax": ("Min-max scaling", "Target range (lo, hi)", "0, 1"),
    "center": ("Center (subtract mean)", None, ""),
    "log": ("Log transform ln(v + c)", "Offset c", "0"),
    "smooth": ("Moving average", "Window size (odd)", "3"),
    "outliers": ("Remove outliers (IQR rule)", "IQR factor k", "1.5"),
    "sort": ("Sort rows ascending", None, ""),
}
COLUMN_CHOICES = [("all", "all"), ("x", "x"), ("y", "y"), ("z", "z")]


def _select(cols: dict, choice: str) -> list[str]:
    if choice == "all":
        return list(cols)
    if choice not in cols:
        raise ValueError(f"The data has no column '{choice}'.")
    return [choice]


def moving_average(values: list[float], window: int) -> list[float]:
    half = window // 2
    n = len(values)
    out = []
    for i in range(n):
        chunk = values[max(0, i - half): min(n, i + half + 1)]
        out.append(math.fsum(chunk) / len(chunk))
    return out


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._op, self._columns = "zscore", "all"
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, [(key, spec[0]) for key, spec in OPERATIONS.items()], "Operation: ", self._on_operation_change)
        _ui.mode_cell(parent, COLUMN_CHOICES, "Columns: ", lambda key: setattr(self, "_columns", key))
        self.box = ParameterBox(parent, "Parameter")
        self.box.pack(fill="x", pady=(0, 8))
        self.box.add("param", "", "")
        self._apply_operation(self._op)

    def _on_operation_change(self, key: str) -> None:
        self._op = key
        self._apply_operation(key)

    def _apply_operation(self, key: str) -> None:
        _label, caption, default = OPERATIONS[key]
        self.box.set_enabled("param", True)
        self.box.set_label("param", caption or "(this operation has no parameter)")
        self.box.set("param", default)
        self.box.set_enabled("param", caption is not None)

    # -- the operations --------------------------------------------------------

    def compute(self, dataset):
        cols = b.columns(dataset)
        n = len(next(iter(cols.values())))
        target = _select(cols, self._columns)
        op = self._op
        param = self.box.get("param")
        new = {name: list(values) for name, values in cols.items()}
        groups: dict = {}
        info: dict = {}

        if op == "zscore":
            for name in target:
                m, s = b.mean(cols[name]), b.std(cols[name])
                if not s:
                    raise ValueError(f"Column '{name}' is constant (or has a single value) and cannot be standardized.")
                new[name] = [(v - m) / s for v in cols[name]]
                groups[name] = {"mean": m, "std dev": s}
        elif op == "minmax":
            parts = [p for p in param.replace(";", ",").split(",") if p.strip()]
            if len(parts) != 2:
                raise ValueError("Target range needs two numbers: lo, hi.")
            lo, hi = b.parse_float(parts[0], "lo"), b.parse_float(parts[1], "hi")
            if not lo < hi:
                raise ValueError("Target range needs lo < hi.")
            for name in target:
                vmin, vmax = min(cols[name]), max(cols[name])
                if vmin == vmax:
                    raise ValueError(f"Column '{name}' is constant and cannot be scaled.")
                new[name] = [lo + (v - vmin) / (vmax - vmin) * (hi - lo) for v in cols[name]]
                groups[name] = {"min": vmin, "max": vmax}
        elif op == "center":
            for name in target:
                m = b.mean(cols[name])
                new[name] = [v - m for v in cols[name]]
                groups[name] = {"mean": m}
        elif op == "log":
            c = b.parse_float(param, "offset c")
            for name in target:
                if any(v + c <= 0 for v in cols[name]):
                    raise ValueError(f"Column '{name}' has values with v + c <= 0 -- the logarithm is undefined (raise the offset c).")
                new[name] = [math.log(v + c) for v in cols[name]]
            info["offset c"] = c
        elif op == "smooth":
            w = b.parse_float(param, "window size")
            if w != int(w) or int(w) < 1 or int(w) % 2 == 0:
                raise ValueError("The window size must be an odd whole number (1, 3, 5, ...).")
            if int(w) > n:
                raise ValueError(f"The window ({int(w)}) is larger than the number of rows ({n}).")
            for name in target:
                new[name] = moving_average(cols[name], int(w))
            info["window"] = int(w)
        elif op == "outliers":
            k = b.parse_float(param, "IQR factor k")
            if k < 0:
                raise ValueError("The IQR factor k must not be negative.")
            keep = set(range(n))
            for name in target:
                ordered = sorted(cols[name])
                q1, q3 = b.quantile(ordered, 0.25), b.quantile(ordered, 0.75)
                low, high = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
                keep &= {i for i, v in enumerate(cols[name]) if low <= v <= high}
                groups[name] = {"lower fence": low, "upper fence": high}
            if not keep:
                raise ValueError("Every row is an outlier with this factor -- raise k.")
            new = {name: [values[i] for i in sorted(keep)] for name, values in cols.items()}
        else:  # sort
            key_column = target[0]
            order = sorted(range(n), key=cols[key_column].__getitem__)
            new = {name: [values[i] for i in order] for name, values in cols.items()}
            info["sorted by"] = key_column

        rows_after = len(next(iter(new.values())))
        plain = {"rows": f"{n} -> {rows_after}" if rows_after != n else n, "columns": ", ".join(target)}
        plain.update(info)
        stats = {None: plain, **groups}
        return self._build(dataset, new, rows_after, OPERATIONS[op][0], stats, {"operation": op, "columns": target})

    def _build(self, source: DataSet, new: dict, rows: int, label: str, stats: dict, metadata: dict) -> DataSet:
        # same layout as the source (axes stay axes, data stays data) with the transformed values; arrays that are not plain columns drop out
        axes = {}
        for key, array in source.axes.items():
            axes[key] = copy.deepcopy(array)
            axes[key].values = new[key]
        data = {}
        for key, array in source.data.items():
            if key in new:
                data[key] = copy.deepcopy(array)
                data[key].values = new[key]
        result = DataSet(axes=axes, data=data, name=f"{source.name} ({label})" if source.name else label, source_tool=TOOL_NAME)
        result.metadata = {"kind": "statistics", "title": f"{label}\ncolumns: {', '.join(metadata['columns'])}", "tool": TOOL_NAME, "source": source.name, "n": rows, **metadata}
        results.add_statistics(result, stats)
        return result


def open_window(parent) -> None:
    ToolWindow(parent)
