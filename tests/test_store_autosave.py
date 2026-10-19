"""Store selection, settings, autosave/recovery and .npy loading (no GUI needed)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import autosave, loaders, results, session, settings, store
from data.dataset import DataSet, DataArray


def result(name="r") -> DataSet:
    src = DataSet(name="s.csv", axes={"x": DataArray([1.0, 2.0, 3.0], "x"), "y": DataArray([2.0, 4.0, 6.1], "y")})
    ds = results.fit_dataset(src, "Linear", "y = a*x + b", {"a": 2.0, "b": 0.0}, [2.0, 4.0, 6.1], [2.0, 4.0, 6.0])
    ds.name = name
    return ds


def loaded(name="d.csv") -> DataSet:
    return DataSet(name=name, axes={"x": DataArray([1.0, 2.0], "x")}, metadata={"source_path": "/x/" + name})


class Isolated(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        patcher = mock.patch.dict(os.environ, {"MTOOLS_HOME": os.path.join(self.dir, "cfg")})
        patcher.start()
        self.addCleanup(patcher.stop)
        store.clear()
        self.addCleanup(store.clear)
        self.addCleanup(self._tmp.cleanup)


class StoreTests(Isolated):
    def test_selection_and_new_results(self):
        a, b = loaded("a"), loaded("b")
        store.add(a); store.add(b)
        self.assertIs(store.get(), b)
        store.select(a)
        self.assertIs(store.get(), a)
        self.assertTrue(store.is_current(a))
        c = result()
        store.add(c)  # a fresh result always becomes current again, so chains keep working
        self.assertIs(store.get(), c)

    def test_select_unknown_dataset_fails(self):
        with self.assertRaises(ValueError):
            store.select(loaded())

    def test_replace_and_remove_keep_selection_sane(self):
        a, r = loaded("a"), result("r1")
        store.add(a); store.add(r)
        store.select(r)
        r2 = result("r2")
        store.replace(r, r2)
        self.assertIs(store.get(), r2)
        store.remove(r2)
        self.assertIs(store.get(), a)
        self.assertEqual(store.unsaved(), [])

    def test_rename_and_revision(self):
        a = loaded("a")
        store.add(a)
        rev = store.revision()
        store.rename(a, "  new name ")
        self.assertEqual(a.name, "new name")
        self.assertGreater(store.revision(), rev)
        with self.assertRaises(ValueError):
            store.rename(a, "   ")

    def test_save_uses_selected_dataset(self):
        a = DataSet(name="a", axes={"x": DataArray([1.0, 2.0], "x")}, metadata={"source_path": "p"})
        store.add(a); store.add(result("b"))
        store.select(a)
        session.save_file(os.path.join(self.dir, "o.csv"))
        self.assertEqual(loaders.load_dataset(os.path.join(self.dir, "o.csv")).axes["x"].values, [1.0, 2.0])


class SettingsTests(Isolated):
    def test_roundtrip_and_defaults(self):
        self.assertEqual(settings.get("nope", 5), 5)
        self.assertTrue(settings.set("last_dir", "/tmp/x"))
        self.assertEqual(settings.get("last_dir"), "/tmp/x")
        self.assertTrue(settings.set("other", [1, 2]))
        self.assertEqual(settings.get("last_dir"), "/tmp/x")  # earlier keys survive

    def test_corrupt_file_means_defaults_and_unwritable_never_raises(self):
        settings.set("a", 1)
        (settings.config_dir() / "settings.json").write_text("{broken")
        self.assertEqual(settings.get("a", "d"), "d")
        blocker = Path(self.dir) / "file"
        blocker.write_text("x")
        with mock.patch.dict(os.environ, {"MTOOLS_HOME": str(blocker / "sub")}):
            self.assertFalse(settings.set("a", 1))


class AutosaveTests(Isolated):
    def test_lifecycle(self):
        saver = autosave.AutoSaver()
        store.add(loaded())
        self.assertFalse(saver.tick())                    # nothing unsaved -> nothing mirrored
        self.assertFalse(autosave.path().exists())
        r = result()
        store.add(r)
        self.assertTrue(saver.tick())
        self.assertTrue(autosave.path().exists())
        self.assertFalse(saver.tick())                    # unchanged -> no rewrite
        store.rename(r, "renamed")
        self.assertTrue(saver.tick())
        info = autosave.pending()
        self.assertEqual((info["n_datasets"], info["n_unsaved"]), (2, 1))
        session.save_file(os.path.join(self.dir, "out.csv"), r)
        saver.tick()
        self.assertFalse(autosave.path().exists())        # everything saved -> nothing to recover

    def test_restore_keeps_results_unsaved_and_removes_file(self):
        store.add(result("keep me"))
        self.assertTrue(autosave.write())
        store.clear()
        restored = autosave.restore()
        self.assertEqual([d.name for d in store.all()], ["keep me"])
        self.assertEqual(len(store.unsaved()), 1)
        self.assertEqual(len(restored), 1)
        self.assertFalse(autosave.path().exists())
        self.assertIsNone(autosave.pending())

    def test_leftover_from_crash_is_moved_aside_not_overwritten_or_deleted(self):
        store.add(result("old"))
        autosave.write()
        store.clear()
        saver = autosave.AutoSaver()                      # new session, user ignored the restore offer
        saver.tick(); saver.close()                       # nothing unsaved: must not delete the foreign file
        self.assertTrue(autosave.path().exists())
        store.add(result("new"))
        saver.tick()
        previous = autosave.path().with_name("autosave.previous.json")
        self.assertTrue(previous.exists())
        self.assertEqual(loaders.datasets_from_json(previous.read_text(encoding="utf-8"))[0].name, "old")
        saver.close()
        self.assertFalse(autosave.path().exists())

    def test_corrupt_autosave_is_ignored(self):
        autosave.path().parent.mkdir(parents=True)
        autosave.path().write_text("{nope")
        self.assertIsNone(autosave.pending())

    def test_too_large_workspace_is_skipped_but_reported(self):
        store.add(result())
        saver = autosave.AutoSaver()
        with mock.patch.object(autosave, "MAX_VALUES", 2):
            self.assertFalse(saver.tick())
        self.assertTrue(saver.skipped)
        self.assertFalse(autosave.path().exists())


class NpyTests(Isolated):
    def setUp(self):
        super().setUp()
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        self.np = np

    def save(self, name, array, **kw):
        p = os.path.join(self.dir, name)
        self.np.save(p, array, **kw)
        return p

    def test_1d_and_2d(self):
        ds = loaders.load_dataset(self.save("a.npy", self.np.array([1, 2, self.np.nan])))
        self.assertEqual(list(ds.axes), ["x"])
        img = loaders.load_dataset(self.save("b.npy", self.np.arange(6).reshape(2, 3)))
        z = img.data["z"]
        self.assertEqual((z.ndim, z.dims, z.values[1]), (2, ("y", "x"), [3.0, 4.0, 5.0]))
        self.assertIn("2x3 grid", img.describe())

    def test_rejects_text_objects_and_3d(self):
        for arr, kw in ((self.np.array(["a"]), {}), (self.np.zeros((2, 2, 2)), {}), (self.np.array([{"x": 1}], dtype=object), {"allow_pickle": True})):
            with self.subTest(dtype=arr.dtype), self.assertRaises(ValueError):
                loaders.load_dataset(self.save("x.npy", arr, **kw))

    def test_json_roundtrip_of_an_image(self):
        img = loaders.load_dataset(self.save("b.npy", self.np.arange(6).reshape(2, 3)))
        from data import savers
        p = os.path.join(self.dir, "img.json")
        savers.save_dataset(p, img)
        self.assertEqual(loaders.load_dataset(p).data["z"].values, img.data["z"].values)


if __name__ == "__main__":
    unittest.main()
