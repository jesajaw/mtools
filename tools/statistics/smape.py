"""
SMAPE -- symmetric mean absolute percentage error between actual values A and forecasts F, a common accuracy measure for forecasts. Unlike a plain MAPE it stays bounded when actual values are close to zero:

    standard   SMAPE = 100% / n * sum( 2 * |F - A| / (|A| + |F|) )     range 0 .. 200 %
    halved     SMAPE = 100% / n * sum(     |F - A| / (|A| + |F|) )     range 0 .. 100 %

A pair with A = F = 0 is a perfect forecast and counts as an error of 0 (it stays in n and is reported). Because the formula is symmetric in A and F, it does not matter which of the two columns holds the actual values.

What is compared is chosen with the Compare cell:
- auto      the output of a fit tool: the fitted response (y, or z for 3D fits) against the model values; otherwise two loaded columns x (actual) and y (forecast)
- x vs y, x vs z, y vs z   a fixed pair of columns, needed e.g. for three loaded columns

The result lists the SMAPE, n, the largest point error and the row it occurs in, the median point error, and carries the point-wise error (in %) as an extra array "smape", so the worst points can be found or plotted.
"""

from . import _basic as b
from . import _ui
from data import results
from data.dataset import DataArray
from theme.widgets import ComputeToolWindow

TOOL_NAME = "SMAPE"
TOOL_DESCRIPTION = "Symmetric mean absolute percentage error between actual values and forecasts (or a fit and its data), with the point-wise error."
TOOL_INSTRUCTIONS = "Load two columns (actual, forecast) via the main window -- or run a fit tool first to compare its fit with the data -- pick what to compare and the scale, then click Compute and after that, save or visualize as you wish."
RESULT_FORMAT = "SMAPE (%), n, A = F = 0 pairs,\nlargest and median point error (%)"

COMPARE = [("auto", "auto"), ("xy", "x vs y"), ("xz", "x vs z"), ("yz", "y vs z")]
SCALES = [("standard", "0 - 200 % (standard)"), ("halved", "0 - 100 % (halved)")]
FACTOR = {"standard": 200.0, "halved": 100.0}


def point_errors(actual, forecast, scale: str = "standard") -> tuple[list[float], int]:
    """Point-wise SMAPE terms in % and the number of pairs with A = F = 0 (counted as 0)."""
    factor = FACTOR[scale]
    terms, zero_pairs = [], 0
    for a, f in zip(actual, forecast):
        denominator = abs(a) + abs(f)
        if denominator == 0:
            terms.append(0.0)
            zero_pairs += 1
        else:
            terms.append(factor * abs(f - a) / denominator)
    return terms, zero_pairs


def smape(actual, forecast, scale: str = "standard") -> float:
    terms, _ = point_errors(actual, forecast, scale)
    return sum(terms) / len(terms)


def _pair(dataset, cols: dict, mode: str) -> tuple[str, str]:
    if mode != "auto":
        names = (mode[0], mode[1])
        for name in names:
            if name not in cols:
                raise ValueError(f"The data has no column '{name}' to compare.")
        return names
    if dataset.metadata.get("kind") == "fit" and "fit" in cols:
        response = "z" if dataset.metadata.get("dimension") == 3 else "y"
        if response not in cols:
            raise ValueError(f"This fit has no '{response}' column to compare its fit against (it was fitted on a single column).")
        return response, "fit"
    coordinate_columns = [name for name in ("x", "y", "z") if name in cols]
    if len(coordinate_columns) == 2:
        return coordinate_columns[0], coordinate_columns[1]
    if len(coordinate_columns) < 2:
        raise ValueError("SMAPE needs two columns (actual, forecast) -- or the output of a fit tool.")
    raise ValueError("Three columns are loaded -- pick the pair to compare with the Compare cell.")


class ToolWindow(ComputeToolWindow):
    def __init__(self, parent):
        self._compare, self._scale = "auto", "standard"
        super().__init__(parent, title=TOOL_NAME, instructions=TOOL_INSTRUCTIONS, result_format=RESULT_FORMAT)

    def _build_extra(self, parent) -> None:
        _ui.mode_cell(parent, COMPARE, "Compare: ", lambda key: setattr(self, "_compare", key))
        _ui.mode_cell(parent, SCALES, "Scale: ", lambda key: setattr(self, "_scale", key))

    def compute(self, dataset):
        cols = b.columns(dataset)
        actual_name, forecast_name = _pair(dataset, cols, self._compare)
        terms, zero_pairs = point_errors(cols[actual_name], cols[forecast_name], self._scale)
        n = len(terms)
        worst = max(range(n), key=terms.__getitem__)
        label = dict(SCALES)[self._scale]
        stats = {
            "SMAPE (%)": sum(terms) / n,
            "n": n,
            "A = F = 0 pairs": zero_pairs,
            "largest error (%)": terms[worst],
            "worst row": worst + 1,
            "median error (%)": b.median(terms),
        }
        title = f"SMAPE, scale {label}\ncompared: {actual_name} vs {forecast_name}"
        arrays = [DataArray(values=terms, name="smape", units="%", label="Point-wise SMAPE term")]
        return results.stats_dataset(dataset, TOOL_NAME, title, {None: stats}, arrays=arrays, metadata={"scale": self._scale, "compared": [actual_name, forecast_name]})


def open_window(parent) -> None:
    ToolWindow(parent)
