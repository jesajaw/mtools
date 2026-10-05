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

No tool formats anything itself: summarize() renders any such DataSet for display, parameters() reads the values back for the next tool.
"""

import copy

from data.dataset import DataSet, DataArray, Annotation

COORDINATES = ("x", "y", "z")


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

    axes = {k: copy.deepcopy(source.get(k)) for k in COORDINATES if k in source.axes or k in source.data}
    return DataSet(
        axes=axes,
        data={
            "fit": DataArray(values=list(fitted), name="fit", label="Fitted values"),
            "residual": DataArray(values=list(residual), name="residual", label="Residual"),
        },
        annotations=[Annotation(kind="parameter", name=k, data={"value": float(v)}) for k, v in params.items()],
        metadata=meta,
        name=f"{tool} (fit of {source.name})" if source.name else f"{tool} (fit)",
        source_tool=tool,
    )


def parameters(dataset: DataSet) -> dict:
    """The fitted parameters of a fit result as {name: value}."""
    return {a.name: a.data["value"] for a in dataset.annotations_of("parameter")}


def summarize(dataset: DataSet) -> str:
    """Generic text rendering of any result DataSet -- equation, parameters, fit statistics."""
    md = dataset.metadata
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
