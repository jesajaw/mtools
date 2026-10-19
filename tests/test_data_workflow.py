"""Tests for the file/workspace workflow (no GUI needed): python -m unittest discover -s tests -t ."""

import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import loaders, savers, results, session, store
from data.dataset import DataSet, DataArray, Annotation


def make_fit() -> DataSet:
    src = DataSet(name="s.csv", axes={"x": DataArray([1.0, 2.0, 3.0], "x", units="nm", label="Laenge"), "y": DataArray([2.0, 4.0, 6.1], "y")})
    ds = results.fit_dataset(src, "Linear", "y = a*x + b", {"a": 2.0, "b": 0.0}, [2.0, 4.0, 6.1], [2.0, 4.0, 6.0])
    ds.annotations.append(Annotation("peak", {"center": 1.5}, name="P1"))
    return ds


class TmpDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        store.clear()
        session._last_saved["text"] = None
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(store.clear)

    def path(self, name):
        return os.path.join(self.dir, name)

    def write(self, name, content, encoding="utf-8"):
        p = self.path(name)
        Path(p).write_bytes(content.encode(encoding) if isinstance(content, str) else content)
        return p


class ParserTests(TmpDirCase):
    def test_delimiters_and_decimals(self):
        cases = {
            "1;2\n3;4": [(1, 2), (3, 4)],
            "1,5;2,5\n3,5;4,5": [(1.5, 2.5), (3.5, 4.5)],
            "1\t2\n3\t4": [(1, 2), (3, 4)],
            "1,2\n3,4": [(1, 2), (3, 4)],
            "1.5 2.5\n3.5 4.5": [(1.5, 2.5), (3.5, 4.5)],
            "1,5 2,5\n3,5 4,5": [(1.5, 2.5), (3.5, 4.5)],
            "1.234,5;2\n6,5;7": [(1234.5, 2), (6.5, 7)],
            "1|2\n3|4": [(1, 2), (3, 4)],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(loaders.parse_points(text), [tuple(map(float, r)) for r in expected])

    def test_single_column_and_three_columns(self):
        self.assertEqual(loaders.parse_points("1\n2\n3"), [1.0, 2.0, 3.0])
        self.assertEqual(loaders.parse_points("1;2;3\n4;5;6"), [(1, 2, 3), (4, 5, 6)])

    def test_more_than_three_columns(self):
        ds = loaders.parse_dataset("1;2;3;4;5\n6;7;8;9;10")
        self.assertEqual(list(ds.axes), ["x", "y", "z"])
        self.assertEqual(list(ds.data), ["col4", "col5"])
        self.assertEqual(ds.data["col5"].values, [5.0, 10.0])

    def test_header_units_and_labels(self):
        ds = loaders.parse_dataset("Time [s];Signal (V)\n1;2\n3;4")
        self.assertEqual((ds.axes["x"].label, ds.axes["x"].units), ("Time", "s"))
        self.assertEqual((ds.axes["y"].label, ds.axes["y"].units), ("Signal", "V"))
        self.assertEqual(ds.axes["y"].values, [2.0, 4.0])

    def test_missing_values_never_shift_columns(self):
        ds = loaders.parse_dataset("1;;3\n4;5;6\n7;8;9")
        self.assertEqual(ds.axes["x"].values, [4.0, 7.0])
        self.assertEqual(ds.axes["z"].values, [6.0, 9.0])
        self.assertEqual(ds.metadata["skipped_rows"], 1)
        kept = loaders.parse_dataset("1;;3\n4;5;6", on_missing="keep")
        self.assertTrue(math.isnan(kept.axes["y"].values[0]))
        with self.assertRaises(ValueError):
            loaders.parse_dataset("1;;3\n4;5;6", on_missing="error")

    def test_ragged_rows_are_counted_not_merged(self):
        ds = loaders.parse_dataset("1;2\n3;4\n5\n6;7")
        self.assertEqual(ds.axes["x"].values, [1.0, 3.0, 6.0])
        self.assertEqual(ds.metadata["skipped_rows"], 1)

    def test_garbage_gives_clear_errors(self):
        for text in ("hello world\nfoo bar", "   \n\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                loaders.parse_points(text)

    def test_trailing_delimiter_is_not_a_column(self):
        self.assertEqual(loaders.parse_points("1;2;\n3;4;"), [(1, 2), (3, 4)])

    def test_nan_token_and_underscores(self):
        ds = loaders.parse_dataset("1;2\n3;nan\n5;6", on_missing="keep")
        self.assertTrue(math.isnan(ds.axes["y"].values[1]))
        self.assertEqual(loaders.parse_dataset("1_0\n5").axes["x"].values, [5.0])  # "1_0" is text, not 10

    def test_encodings(self):
        for enc in ("utf-8", "utf-8-sig", "cp1252", "utf-16"):
            with self.subTest(enc=enc):
                p = self.write(f"{enc}.csv", "Länge [µm];Wert\n1,5;2,5\n", encoding=enc)
                ds = loaders.load_dataset(p)
                self.assertEqual(ds.axes["x"].values, [1.5])
                self.assertEqual(ds.axes["x"].units, "µm")

    def test_unsupported_and_empty(self):
        with self.assertRaises(ValueError):
            loaders.load_dataset(self.write("a.xlsx", "x"))
        with self.assertRaises(ValueError):
            loaders.load_dataset(self.write("empty.csv", ""))


class RoundTripTests(TmpDirCase):
    def test_fit_result_roundtrip_all_formats(self):
        fit = make_fit()
        for ext in (".csv", ".tsv", ".json"):
            with self.subTest(ext=ext):
                p = self.path("fit" + ext)
                savers.save_dataset(p, fit)
                back = loaders.load_dataset(p)
                self.assertEqual(list(back.axes), ["x", "y"])
                self.assertEqual(list(back.data), ["fit", "residual"])
                self.assertEqual(back.data["residual"].values, fit.data["residual"].values)  # exact floats
                self.assertEqual(back.axes["x"].units, "nm")
                self.assertEqual(back.axes["x"].label, "Laenge")
                self.assertEqual(results.parameters(back), {"a": 2.0, "b": 0.0})
                self.assertEqual(back.metadata["model"], "Linear")
                self.assertEqual([a.name for a in back.annotations_of("peak")], ["P1"])

    def test_excel_de_flavour(self):
        p = self.path("de.csv")
        savers.save_dataset_csv(p, make_fit(), delimiter=";", decimal=",")
        self.assertIn("2,0", Path(p).read_text(encoding="utf-8"))
        back = loaders.load_dataset(p)
        self.assertEqual(back.data["fit"].values, [2.0, 4.0, 6.0])

    def test_json_keeps_grids_nan_and_session(self):
        grid = DataSet(name="afm", data={"h": DataArray([[1.0, math.nan], [math.inf, 4.0]], "h", dims=("y", "x"), units="nm", uncertainty=[[0.1, 0.1], [0.1, 0.1]])}, metadata={"r2": math.nan, "t": (1, 2)})
        p = self.path("ws.json")
        savers.save_json(p, [grid, make_fit()])
        json.loads(Path(p).read_text(encoding="utf-8"))  # strictly valid JSON (no bare NaN)
        a, b = loaders.load_datasets(p)
        h = a.data["h"]
        self.assertTrue(math.isnan(h.values[0][1]))
        self.assertEqual(h.values[1][0], math.inf)
        self.assertEqual((h.dims, h.units, h.ndim), (("y", "x"), "nm", 2))
        self.assertEqual(a.metadata["t"], [1, 2])
        self.assertIsNone(a.metadata["r2"])
        self.assertEqual(b.metadata["model"], "Linear")

    def test_json_version_and_foreign_files(self):
        with self.assertRaises(ValueError):
            loaders.load_dataset(self.write("a.json", '{"hello": 1}'))
        with self.assertRaises(ValueError):
            loaders.load_dataset(self.write("b.json", '{"format": "mtools", "version": 99, "datasets": []}'))
        with self.assertRaises(ValueError):
            loaders.load_dataset(self.write("c.json", "{not json"))

    def test_csv_refuses_to_lose_data(self):
        ragged = DataSet(axes={"x": DataArray([1.0, 2.0, 3.0], "x")}, data={"f": DataArray([1.0, 2.0], "f")})
        grid = DataSet(data={"h": DataArray([[1.0, 2.0]], "h")})
        for ds in (ragged, grid, DataSet()):
            with self.subTest(ds=ds.name), self.assertRaises(ValueError):
                savers.save_dataset_csv(self.path("bad.csv"), ds)
        self.assertFalse(os.path.exists(self.path("bad.csv")))

    def test_annotation_only_csv_is_a_table(self):
        ds = DataSet(annotations=[Annotation("peak", {"center": 1.5, "width": 0.2}), Annotation("peak", {"center": 3.0})])
        p = self.path("peaks.csv")
        savers.save_dataset_csv(p, ds)
        self.assertEqual(Path(p).read_text().splitlines()[0], "kind,name,center,width")

    def test_failed_save_keeps_existing_file(self):
        p = self.write("keep.csv", "precious")
        with self.assertRaises(ValueError):
            savers.save_dataset_csv(p, DataSet(data={"h": DataArray([[1.0]], "h")}))
        self.assertEqual(Path(p).read_text(), "precious")

        from unittest import mock
        with mock.patch.object(savers, "_fmt", side_effect=RuntimeError("disk exploded")), self.assertRaises(RuntimeError):
            savers.save_dataset_csv(p, make_fit())  # fails half-way through the rows
        self.assertEqual(Path(p).read_text(), "precious")
        self.assertEqual([f for f in os.listdir(self.dir) if f.endswith(".tmp")], [])


class StoreSessionTests(TmpDirCase):
    def test_unsaved_tracking(self):
        loaded = session.load_file(self.write("d.csv", "1;2\n3;4"))
        self.assertEqual(store.unsaved(), [])  # loading from a file is not unsaved work
        result = make_fit()
        store.add(result)
        self.assertEqual(store.unsaved(), [result])
        newer = make_fit()
        store.replace(result, newer)
        self.assertEqual(store.unsaved(), [newer])
        session.save_file(self.path("out.csv"), newer)
        self.assertEqual(store.unsaved(), [])
        self.assertEqual(len(store.all()), 2)
        self.assertEqual(store.get(), newer)
        self.assertIsNotNone(loaded)

    def test_reloaded_result_is_not_flagged_unsaved(self):
        p = self.path("r.json")
        savers.save_dataset(p, make_fit())
        session.load_file(p)
        self.assertEqual(store.unsaved(), [])

    def test_workspace_json_saves_everything(self):
        session.load_file(self.write("d.csv", "1;2\n3;4"))
        store.add(make_fit())
        msg = session.save_file(self.path("all.json"), whole_workspace=True)
        self.assertIn("2 dataset(s)", msg)
        self.assertEqual(store.unsaved(), [])
        store.clear()
        self.assertEqual(len(session.load_file(self.path("all.json"))), 2)
        self.assertEqual(len(store.all()), 2)

    def test_csv_saves_only_the_latest_and_default_extension(self):
        session.load_file(self.write("d.csv", "1;2\n3;4"))
        store.add(make_fit())
        session.save_file(self.path("latest"))  # no extension -> .csv
        back = loaders.load_dataset(self.path("latest.csv"))
        self.assertIn("fit", back.data)

    def test_failed_load_adds_nothing_and_listeners_fire(self):
        calls = []
        store.subscribe(lambda: calls.append(1))
        with self.assertRaises(ValueError):
            session.load_file(self.write("bad.csv", "just text"))
        self.assertEqual((len(store.all()), calls), (0, []))
        session.load_file(self.write("ok.csv", "1;2"))
        self.assertEqual(len(calls), 1)

    def test_save_without_data_and_suggest_filename(self):
        with self.assertRaises(ValueError):
            session.save_file(self.path("x.csv"))
        self.assertEqual(session.suggest_filename(make_fit()), "Linear_fit_of_s.csv")
        self.assertEqual(session.suggest_filename(None), "data.csv")

    def test_describe(self):
        ds = loaders.parse_dataset("1;2\n3;\n5;6", name="a.csv")
        self.assertIn("2 row(s)", ds.describe())
        self.assertIn("1 incomplete/invalid row(s) skipped", ds.describe())


class StatisticsResultTests(TmpDirCase):
    def make(self, with_data=True):
        src = DataSet(name="d.csv", axes={"x": DataArray([1.0, 2.0, 3.0], "x"), "y": DataArray([2.0, 4.0, 7.0], "y")}) if with_data else None
        groups = {"x": {"mean": 2.0, "n": 3}, "y": {"mean": 4.333, "n": 3}, None: {"note": "ok", "undefined": None}}
        return results.stats_dataset(src, "Descriptive Statistics", "Descriptive\nstatistics", groups)

    def test_json_roundtrip_keeps_statistics(self):
        for with_data in (True, False):
            with self.subTest(with_data=with_data):
                ds = self.make(with_data)
                p = self.path(f"s{with_data}.json")
                savers.save_dataset(p, ds)
                back = loaders.load_dataset(p)
                self.assertEqual(results.statistics(back), results.statistics(ds))
                self.assertEqual(back.metadata["title"], "Descriptive\nstatistics")

    def test_csv_keeps_user_readable_block_and_table(self):
        p = self.path("s.csv")
        savers.save_dataset_csv(p, self.make(True))
        text = Path(p).read_text(encoding="utf-8")
        self.assertIn("# tool: Descriptive Statistics", text)
        self.assertIn("# x.mean = 2.0", text)
        self.assertNotIn("# annotation:", text)  # not duplicated as JSON
        self.assertEqual(loaders.load_dataset(p).axes["y"].values, [2.0, 4.0, 7.0])  # the numbers still load as data

    def test_result_without_arrays_is_saved_as_table(self):
        p = self.path("nodata.csv")
        savers.save_dataset_csv(p, self.make(False))
        lines = Path(p).read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(l == "kind,group,name,value" for l in lines), lines)
        self.assertTrue(any(l.startswith("statistic,x,mean,2.0") for l in lines))
        self.assertTrue(any(l.startswith("statistic,,undefined,") for l in lines))


class WorkspaceWithManyColumns(TmpDirCase):
    def test_statistics_tools_can_see_all_columns(self):
        p = self.write("wide.csv", "a;b;c;d;e\n1;2;3;4;5\n6;7;8;9;10")
        ds = session.load_file(p)[0]
        self.assertEqual(list(ds.axes) + list(ds.data), ["x", "y", "z", "d", "e"])  # extra columns keep their header names


class LegacyApiTests(TmpDirCase):
    def test_old_entry_points_still_work(self):
        p = self.write("pts.txt", "x y\n1 2\n3 4")
        self.assertEqual(loaders.load_points(p), [(1.0, 2.0), (3.0, 4.0)])
        savers.save_points_csv(self.path("o.csv"), [(1.0, 2.0)])
        savers.save_text(self.path("o.txt"), "hi")
        self.assertEqual(Path(self.path("o.txt")).read_text(), "hi")
        with self.assertRaises(ValueError):
            loaders.parse_points("1;2;3;4\n5;6;7;8")


if __name__ == "__main__":
    unittest.main()
