"""
Uniform result envelope for tools that produce a model/fit -- so every tool hands its result back to the workspace in the SAME shape and the next tool can pick it up without knowing which tool made it.

A fit result is an ordinary DataSet (see data/dataset.py):

    axes         -- copy of the input coordinates (x, y[, z]), so the result can be fed straight into the next tool
    data["fit"]       -- model values at the input points
    data["residual"]  -- response - fit (or the perpendicular distance, see metadata["residual_kind"])
    annotations  -- one Annotation(kind="parameter", name=<param>, data={"value": v}) per fitted parameter
    metadata     -- {"kind": "fit", "model": <tool>, "equation": <str>, "n": <rows>,
                     "stats": {"sse", "rmse", "r2"?}, "residual_kind": "vertical"|"perpendicular",
                     "source": <name of the input DataSet>, ... tool extras (degree, mode, formula, ...)}
    source_tool  -- TOOL_NAME of the tool that produced it

A statistics result (descriptive statistics, tests, intervals, error metrics, ...) is also an ordinary DataSet, built by stats_dataset():

    axes         -- copy of the input coordinates (x, y[, z]) when there is an input, so the next tool can still work on the data
    data         -- optional per-row arrays (e.g. a per-point error)
    annotations  -- one Annotation(kind="statistic", name=<label>, data={"value": v}, metadata={"group": <group>}) per reported number or text;
                    the group is a column name (x, y, ...) or a sub-result (slope, intercept) -- None for plain, ungrouped values
    metadata     -- {"kind": "statistics", "title": <heading, may span lines>, "tool": <tool>, "source": <input name>, ... tool extras}
    source_tool  -- TOOL_NAME of the tool that produced it

No tool formats anything itself: summarize() renders any such DataSet for display (several groups become a table with one column per group), parameters() / statistics() read the values back for the next tool.
"""

import copy
import math

from data.dataset import DataSet, DataArray, Annotation, COORDINATES



def fit_dataset(source: DataSet, tool: str, equation: str, params: dict, response, fitted, residual=None, residual_kind: str = "vertical", metadata: dict | None = None) -> DataSet:
    """Builds the standard fit result. `response` is the column that was fitted (y in 2D, z in 3D), `fitted` the model values for the same rows. `params` maps parameter name -> value."""
    n = len(response)
    if len(fitted) != n:
        raise ValueError("fit_dataset: `fitted` and `response` must have the same length.")
    if residual is None:
        residual = [r - f for r, f in zip(response, fitted)]

    sse = sum(r * r for r in residual)
    stats = {"sse": sse, "rmse": (sse / n) ** 0.5 if n else 0.0}
    if residual_kind == "vertical" and n:
        mean = sum(response) / n
        sst = sum((v - mean) ** 2 for v in response)
        if sst > 0:
            stats["r2"] = 1 - sse / sst

    meta = {"kind": "fit", "model": tool, "equation": equation, "n": n, "residual_kind": residual_kind, "stats": stats, "source": source.name}
    meta.update(metadata or {})

    return DataSet(
        axes=coordinates(source),
        data={
            "fit": DataArray(values=list(fitted), name="fit", label="Fitted values"),
            "residual": DataArray(values=list(residual), name="residual", label="Residual"),
        },
        annotations=[Annotation(kind="parameter", name=k, data={"value": float(v)}) for k, v in params.items()],
        metadata=meta,
        name=f"{tool} (fit of {source.name})" if source.name else f"{tool} (fit)",
        source_tool=tool,
    )


def coordinates(source: DataSet | None) -> dict:
    """Deep copy of the coordinate arrays (x, y, z) of `source`, so a result can be fed straight into the next tool. Empty if there is no source."""
    if source is None:
        return {}
    return {k: copy.deepcopy(source.get(k)) for k in COORDINATES if k in source.axes or k in source.data}


def add_statistics(dataset: DataSet, groups: dict) -> None:
    """Appends statistics to `dataset`. `groups` maps a group name (or None) to {label: value}; a value may be a number, a text or None (= undefined, shown as '-')."""
    for group, items in groups.items():
        for label, value in items.items():
            dataset.annotations.append(Annotation(kind="statistic", name=label, data={"value": value}, metadata={"group": group} if group else {}))


def stats_dataset(source: DataSet | None, tool: str, title: str, groups: dict, arrays: list | None = None, metadata: dict | None = None) -> DataSet:
    """
    Builds the standard statistics result. `source` is the input DataSet (None for tools that work without data), `title` the heading shown above the numbers (may span several lines),
    `groups` as in add_statistics(), `arrays` optional DataArrays with one value per input row.
    """
    meta = {"kind": "statistics", "title": title, "tool": tool, "source": source.name if source else None}
    meta.update(metadata or {})
    result = DataSet(
        axes=coordinates(source),
        data={a.name: a for a in (arrays or [])},
        metadata=meta,
        name=f"{tool} (of {source.name})" if source and source.name else tool,
        source_tool=tool,
    )
    add_statistics(result, groups)
    return result


def statistics(dataset: DataSet) -> dict:
    """The statistics of a result as {group: {label: value}} in the order they were added (group None = ungrouped)."""
    out: dict = {}
    for a in dataset.annotations_of("statistic"):
        out.setdefault(a.metadata.get("group"), {})[a.name] = a.data["value"]
    return out


def format_value(value) -> str:
    """One number or text for display: 6 significant digits, '-' for undefined."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6g}"
    return str(value)


def parameters(dataset: DataSet) -> dict:
    """The fitted parameters of a fit result as {name: value}."""
    return {a.name: a.data["value"] for a in dataset.annotations_of("parameter")}


def summarize(dataset: DataSet) -> str:
    """Generic text rendering of any result DataSet -- equation, parameters, fit statistics."""
    md = dataset.metadata
    if md.get("kind") == "statistics":
        return _summarize_statistics(dataset)
    lines = []
    if md.get("equation"):
        lines.append(md["equation"])
        lines.append("")
    for name, value in parameters(dataset).items():
        lines.append(f"{name} = {value:.6g}")
    stats = md.get("stats") or {}
    if stats:
        lines.append("")
        lines.extend(f"{k} = {v:.6g}" for k, v in stats.items())
    return "\n".join(lines).strip() + "\n"


def _summarize_statistics(dataset: DataSet) -> str:
    # ungrouped values as an aligned "label = value" list, named groups as one table (rows = labels, columns = groups) -- meant for a monospace display
    stats = statistics(dataset)
    lines = []
    title = dataset.metadata.get("title")
    if title:
        lines.extend([title, ""])

    plain = stats.get(None) or {}
    if plain:
        width = max(len(k) for k in plain)
        lines.extend(f"{k.ljust(width)} = {format_value(v)}" for k, v in plain.items())

    named = {g: items for g, items in stats.items() if g is not None}
    if named:
        if plain:
            lines.append("")
        labels = list(dict.fromkeys(label for items in named.values() for label in items))
        label_width = max(len(label) for label in labels)
        widths = {g: max(len(str(g)), *(len(format_value(items.get(label))) for label in labels)) for g, items in named.items()}
        lines.append("  ".join([" " * label_width] + [str(g).rjust(widths[g]) for g in named]))
        for label in labels:
            lines.append("  ".join([label.ljust(label_width)] + [format_value(items.get(label)).rjust(widths[g]) for g, items in named.items()]))
    return "\n".join(lines).rstrip() + "\n"
