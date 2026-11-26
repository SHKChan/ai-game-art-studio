"""Pixel Forge: skill builders and quick edits (speed, palette, HSV, outline, glow, flip, scale) — edits must be
replayable from the saved recipe and validated."""
import json
import unittest

import numpy as np
from helpers import cleanup, studio, temp_workspace

from artstudio.animation import load_frames
from artstudio.procedural import BUILDERS
from artstudio.procedural.edits import EditError, adjust, normalize
from artstudio.util import StudioError

SKILLS = ["heal", "buff_aura", "lightning_strike", "shield_barrier", "frost_nova", "poison_cloud"]


class ForgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.pid = cls.s.ws.create_project("F")["id"]

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def test_skill_variants_render_and_differ(self):
        for b in SKILLS:
            variants = BUILDERS[b].PARAMS["color"]["enum"]
            firsts = []
            for v in variants:
                r = self.s.forge_preview(b, {"color": v})
                self.assertEqual(len(r["frames"]), 8, (b, v))
                self.assertEqual(r["size"], [64, 64])
                self.assertEqual(len(set(r["frames"])), len(r["frames"]), f"{b}/{v}: every frame should differ")
                firsts.append(r["frames"][3])
            self.assertEqual(len(set(firsts)), len(variants), f"{b}: colour variants should differ")

    def test_thickness_params(self):
        thin = self.s.forge_preview("lightning_strike", {"thickness": 1})["frames"][3]
        thick = self.s.forge_preview("lightning_strike", {"thickness": 3})["frames"][3]
        self.assertNotEqual(thin, thick)
        self.assertNotEqual(self.s.forge_preview("sword_slash", {"thickness": 0.6})["frames"][3],
                            self.s.forge_preview("sword_slash", {"thickness": 1.5})["frames"][3])

    def test_speed_scale_flip_palette(self):
        base = self.s.forge_preview("fireball")
        r = self.s.forge_preview("fireball", {}, {"speed": 2.0, "scale": 2, "flip": True, "hue": 120})
        self.assertEqual(r["size"], [128, 128])
        self.assertEqual(r["durations"], [max(10, round(d / 2)) for d in base["durations"]])
        self.assertNotEqual(r["palette"], r["base_palette"])
        self.assertEqual(r["palette"][0], adjust(r["base_palette"][0], 120, 1, 1))
        pal = list(base["base_palette"]); pal[3] = "#00ff00"
        self.assertEqual(self.s.forge_preview("fireball", {}, {"palette": pal})["palette"][3], "#00ff00")

    def test_outline_and_glow_add_layers_and_pixels(self):
        a = self.s.procedural(self.pid, "frost_nova", {"color": "arcane"}, edits={"outline": 1, "glow": 2, "outline_color": "#ff00ff"})
        doc = self.s.ws.engine_home(self.pid) / "documents" / a["procedural"]["doc_id"] / "doc.json"
        layers = [l["name"] for l in json.loads(doc.read_text(encoding="utf-8"))["layers"]]
        self.assertEqual(layers[:2], ["outline", "glow"])
        self.assertEqual(a["procedural"]["edits"]["outline"], 1)
        frames = [np.asarray(im) for _, im in load_frames(self.s.ws, a)]
        magenta = sum(int(((f[..., 0] == 255) & (f[..., 1] == 0) & (f[..., 2] == 255) & (f[..., 3] == 255)).sum()) for f in frames)
        self.assertGreater(magenta, 50)

    def test_edited_asset_replays_identically_and_loops(self):
        a = self.s.procedural(self.pid, "heal", {"color": "blue"}, edits={"speed": 1.5, "glow": 1, "flip": True, "loop": False})
        self.assertFalse(a["animation"]["loop"]["enabled"])
        self.assertTrue(self.s.procedural(self.pid, "poison_cloud")["animation"]["loop"]["enabled"])
        rec = self.s.ws.asset_dir(self.pid, a["id"]) / a["procedural"]["recipe"]
        b = self.s.replay_recipe(self.pid, rec, "replayed")
        self.assertEqual([im.tobytes() for _, im in load_frames(self.s.ws, a)], [im.tobytes() for _, im in load_frames(self.s.ws, b)])
        self.assertEqual([f["duration_ms"] for f in a["animation"]["frames"]], [60] * 8)

    def test_edit_validation(self):
        for bad in ({"speed": 0}, {"outline": 9}, {"palette": ["red"]}, {"nope": 1}, {"glow_color": "#12"}):
            with self.assertRaises(EditError):
                normalize(bad)
        with self.assertRaises(StudioError):
            self.s.forge_preview("not_a_builder")
        self.assertTrue(self.s.forge_thumbnail("heal").is_file())


if __name__ == "__main__":
    unittest.main()
