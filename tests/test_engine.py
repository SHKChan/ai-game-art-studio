"""Pixel Forge (artstudio.engine) tests: tool semantics, persistence, determinism and compatibility with
recipes recorded by the original Atelier editor (showcase fixtures, MIT © 2026 Marmik Shah)."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

from helpers import ROOT, cleanup

from artstudio.engine import Engine, EngineError

FIX = ROOT / "tests" / "fixtures" / "showcase"


def binarize(a):
    a = a.copy()
    on = a[..., 3] >= 128
    a[~on] = 0
    a[on, 3] = 255
    return a


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.e = Engine(self.tmp)

    def tearDown(self):
        cleanup(self.tmp)

    def test_basic_tools_and_persistence(self):
        d = self.e.call("doc_new", {"name": "t", "width": 16, "height": 16})["doc_id"]
        self.e.call("doc_palette", {"doc_id": d, "op": "set", "colors": ["#ff0000", "#00ff00"]})
        self.e.call("doc_layer", {"doc_id": d, "op": "add", "name": "top"})
        self.e.call("doc_draw", {"doc_id": d, "layer": 0, "frame": 0, "op": "rect", "x0": 2, "y0": 2, "x1": 5, "y1": 5, "color": 0, "fill": True})
        self.e.call("doc_paint_grid", {"doc_id": d, "layer": 1, "frame": 0, "x": 4, "y": 4, "legend": {"g": 1}, "rows": ["gg", "gg"]})
        self.e.call("doc_frame", {"doc_id": d, "op": "add", "copy_from": 0, "duration_ms": 80})
        self.e.call("doc_fx", {"doc_id": d, "layer": 0, "frame": 1, "op": "outline", "color": "#000000"})
        fresh = Engine(self.tmp)  # reload from disk
        fr, durs, _ = fresh.export_frames(d)
        self.assertEqual(durs, [100, 80])
        a = np.array(fr[0])
        self.assertEqual(tuple(a[2, 2]), (255, 0, 0, 255))
        self.assertEqual(tuple(a[5, 5]), (0, 255, 0, 255))  # top layer wins
        self.assertEqual(tuple(np.array(fr[1])[1, 3]), (0, 0, 0, 255))  # outline on frame 1 only
        self.assertEqual(tuple(a[1, 3])[3], 0)
        recipe = (self.tmp / "documents" / d / "doc.recipe").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(recipe[0])["name"], "doc_new")

    def test_errors_are_explicit(self):
        d = self.e.call("doc_new", {"name": "t", "width": 4, "height": 4})["doc_id"]
        with self.assertRaises(EngineError):
            self.e.call("doc_teleport", {"doc_id": d})
        with self.assertRaises(EngineError):
            self.e.call("doc_paint_grid", {"doc_id": d, "layer": 0, "frame": 0, "legend": {"a": "#fff"}, "rows": ["ab"]})
        with self.assertRaises(EngineError):
            self.e.call("doc_draw", {"doc_id": d, "layer": 3, "frame": 0, "op": "fill_cel", "color": "#ffffff"})

    def test_replay_is_deterministic(self):
        d = self.e.call("doc_new", {"name": "t", "width": 8, "height": 8})["doc_id"]
        self.e.call("doc_draw", {"doc_id": d, "layer": 0, "frame": 0, "op": "ellipse", "cx": 4, "cy": 4, "rx": 3, "ry": 2, "color": "#3366ff", "fill": True})
        d2 = self.e.replay(self.tmp / "documents" / d / "doc.recipe")
        self.assertNotEqual(d, d2)
        self.assertEqual(self.e.export_frames(d)[0][0].tobytes(), self.e.export_frames(d2)[0][0].tobytes())

    def test_atelier_showcase_recipes_replay_pixel_identical(self):
        for name in ("potion", "slash"):
            did = self.e.replay(FIX / f"{name}.recipe")
            frames, durs, _ = self.e.export_frames(did)
            with Image.open(FIX / f"{name}.gif") as g:
                ref = [f.convert("RGBA") for f in ImageSequence.Iterator(g)]
            self.assertEqual(len(frames), len(ref), name)
            s = ref[0].width // frames[0].width
            for i, (mine, theirs) in enumerate(zip(frames, ref)):
                up = np.array(mine.resize((mine.width * s, mine.height * s), Image.Resampling.NEAREST))
                self.assertTrue(np.array_equal(binarize(up), binarize(np.array(theirs))), f"{name} frame {i}")

    def test_matches_frames_rendered_by_atelier(self):
        """Call lists covering every drawing primitive; reference PNGs rendered by the original Atelier binary."""
        ref = ROOT / "tests" / "fixtures" / "atelier_reference"
        for name in ("sword_icon", "primitives"):
            calls = [json.loads(l) for l in (ref / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
            frames, durs, _ = self.e.export_frames(self.e.run(calls))
            self.assertEqual(durs, json.loads((ref / f"{name}.durations.json").read_text(encoding="utf-8")), name)
            for i, mine in enumerate(frames):
                with Image.open(ref / f"{name}_f{i}.png") as im:
                    theirs = np.array(im.convert("RGBA"))
                a = np.array(mine)
                a[a[..., 3] == 0] = 0
                theirs[theirs[..., 3] == 0] = 0
                self.assertTrue(np.array_equal(a, theirs), f"{name} frame {i}")


if __name__ == "__main__":
    unittest.main()
