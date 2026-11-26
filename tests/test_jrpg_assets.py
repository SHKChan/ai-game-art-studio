"""v0.6 Pixel Forge additions: top-down grid skills (lava burn …) and JRPG item / skill / status icons.
Every variant must render, be layered, pass deterministic QA and differ from its siblings."""
import json
import unittest

from helpers import cleanup, studio, temp_workspace

from artstudio.procedural import BUILDERS

GROUND = {  # builder → (default tiles, frames)
    "lava_burn": (3, 16), "meteor": (3, 12), "fire_pillar": (1, 12), "earth_spike": (3, 9), "whirlpool": (3, 8),
    "gale": (1, 8), "ice_field": (3, 13), "holy_judgment": (3, 11), "dark_vortex": (3, 8), "life_drain": (1, 10),
}
ICONS = {"weapon_icon": "kind", "armor_icon": "kind", "consumable_icon": "kind", "material_icon": "kind",
         "skill_icon": "skill", "status_icon": "status", "ui_icon": "kind"}


class JrpgAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.pid = cls.s.ws.create_project("J")["id"]

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def test_ground_skills_save_layered_and_pass_qa(self):
        for b, (tiles, n) in GROUND.items():
            a = self.s.procedural(self.pid, b)
            self.assertEqual(len(a["animation"]["frames"]), n, b)
            w, h = a["animation"]["canvas"]
            self.assertEqual(w, tiles * 32, b)
            self.assertGreater(h, w, f"{b}: ground effects keep headroom above the cells")
            self.assertEqual([w, h], self.s.forge_preview(b)["size"], f"{b}: saved canvas must equal the drawn canvas (no shift / growth)")
            self.assertEqual(a["qa"]["deterministic"]["status"], "passed", (b, a["qa"]["deterministic"]["issues"]))
            doc = self.s.ws.engine_home(self.pid) / "documents" / a["procedural"]["doc_id"] / "doc.json"
            meta = json.loads(doc.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(meta["layers"]), 2, b)
            self.assertTrue(meta["tags"], f"{b}: frame tags expected")
            self.assertEqual(a["animation"]["pivot"], [w // 2, h - w // 2], f"{b}: pivot = centre of the ground cells")
            self.assertTrue(a["animation"]["full_bleed"], b)

    def test_ground_skill_variants_and_tiles(self):
        for b in GROUND:
            colors = BUILDERS[b].PARAMS["color"]["enum"]
            mids = set()
            for c in colors:
                r = self.s.forge_preview(b, {"color": c})
                self.assertEqual(len(set(r["frames"])), len(r["frames"]), f"{b}/{c}: every frame should differ")
                mids.add(r["frames"][len(r["frames"]) // 2])
            self.assertEqual(len(mids), len(colors), b)
            lo = BUILDERS[b].PARAMS["tiles"]["min"]
            self.assertEqual(self.s.forge_preview(b, {"tiles": lo + 1})["size"][0], (lo + 1) * 32, b)

    def test_lava_burn_phases_and_loops(self):
        full = self.s.forge_preview("lava_burn")
        burn = self.s.forge_preview("lava_burn", {"phase": "burn"})
        self.assertEqual(len(burn["frames"]), 6)
        self.assertEqual(burn["frames"], full["frames"][6:12], "the burn loop is the middle of the full cast")
        for b in ("whirlpool", "gale", "dark_vortex"):
            self.assertTrue(self.s.forge_preview(b)["loop"], b)
            self.assertEqual(len(self.s.forge_preview(b, {"frames": 12})["frames"]), 12, b)

    def test_icons_every_kind_renders_and_differs(self):
        for b, key in ICONS.items():
            seen = set()
            for k in BUILDERS[b].PARAMS[key]["enum"]:
                r = self.s.forge_preview(b, {key: k})
                self.assertEqual(len(r["frames"]), 1)
                self.assertIn(r["size"], ([48, 48], [32, 32], [16, 16]))
                seen.add(r["frames"][0])
            self.assertEqual(len(seen), len(BUILDERS[b].PARAMS[key]["enum"]), b)

    def test_icon_materials_colours_and_frames(self):
        for b, axis in (("weapon_icon", "material"), ("armor_icon", "material"), ("material_icon", "color"), ("skill_icon", "element")):
            vals = [v for v in BUILDERS[b].PARAMS[axis]["enum"] if v != "auto"]
            self.assertEqual(len({self.s.forge_preview(b, {axis: v})["frames"][0] for v in vals}), len(vals), b)
        plain = self.s.forge_preview("consumable_icon")["frames"][0]
        framed = {self.s.forge_preview("consumable_icon", {"frame": f})["frames"][0] for f in BUILDERS["consumable_icon"].PARAMS["frame"]["enum"][1:]}
        self.assertEqual(len(framed), 5)
        self.assertNotIn(plain, framed)

    def test_icons_save_with_layers_and_replay(self):
        a = self.s.procedural(self.pid, "weapon_icon", {"kind": "katana", "material": "mithril", "frame": "legendary"})
        self.assertEqual(a["qa"]["deterministic"]["status"], "passed", a["qa"]["deterministic"]["issues"])
        plain = self.s.procedural(self.pid, "weapon_icon", {"kind": "bow"})
        self.assertFalse(plain["animation"].get("full_bleed"), "an unframed icon keeps the normal edge check")
        self.assertEqual(plain["qa"]["deterministic"]["status"], "passed", plain["qa"]["deterministic"]["issues"])
        doc = self.s.ws.engine_home(self.pid) / "documents" / a["procedural"]["doc_id"] / "doc.json"
        self.assertEqual([l["name"] for l in json.loads(doc.read_text(encoding="utf-8"))["layers"]], ["frame", "item", "shine"])
        self.assertEqual(a["animation"]["canvas"], [48, 48])
        rec = self.s.ws.asset_dir(self.pid, a["id"]) / a["procedural"]["recipe"]
        from artstudio.animation import load_frames
        b = self.s.replay_recipe(self.pid, rec, "replayed")
        self.assertEqual([im.tobytes() for _, im in load_frames(self.s.ws, a)], [im.tobytes() for _, im in load_frames(self.s.ws, b)])

    def test_icon_sizes_and_tiers_change_the_design(self):
        for b in ("weapon_icon", "armor_icon", "consumable_icon", "material_icon", "skill_icon", "ui_icon"):
            for n in (32, 48, 64):
                self.assertEqual(self.s.forge_preview(b, {"size": n})["size"], [n, n], (b, n))
        # tiers are new shapes, not recolours: the opaque silhouettes differ between materials
        import base64
        import io

        import numpy as np
        from PIL import Image

        def mask(r):
            im = Image.open(io.BytesIO(base64.b64decode(r["frames"][0].split(",")[1])))
            return np.asarray(im)[..., 3] > 0
        for b, axis, vals in (("weapon_icon", "material", ["bronze", "iron", "mithril", "gold", "dark"]),
                              ("armor_icon", "material", ["bronze", "iron", "mithril", "gold", "dark"]),
                              ("consumable_icon", "grade", ["minor", "normal", "greater"]),
                              ("material_icon", "color", ["red", "blue", "green", "purple", "gold", "silver"])):
            kinds = BUILDERS[b].PARAMS["kind"]["enum"]
            for k in kinds:
                masks = [mask(self.s.forge_preview(b, {"kind": k, axis: v})).tobytes() for v in vals]
                self.assertGreaterEqual(len(set(masks)), len(vals) - 1, f"{b}/{k}: {axis} should change the shape")

    def test_ui_kit(self):
        for theme in ("classic_blue", "wood_gold", "stone_iron", "parchment"):
            for kind in BUILDERS["ui_panel"].PARAMS["kind"]["enum"]:
                r = self.s.forge_preview("ui_panel", {"kind": kind, "theme": theme, "width": 96, "height": 48})
                self.assertEqual(r["size"], [96, 48], (kind, theme))
            for shape in ("rect", "square", "round"):
                r = self.s.forge_preview("ui_button", {"shape": shape, "theme": theme})
                self.assertEqual(len(r["frames"]), 4, "normal / hover / pressed / disabled")
                self.assertEqual(len(set(r["frames"])), 4, (shape, theme))
            for kind in ("portrait", "slot", "skill_slot"):
                self.s.forge_preview("ui_frame", {"kind": kind, "theme": theme})
        empty = self.s.forge_preview("ui_bar", {"fill": 0.0})["frames"][0]
        full = self.s.forge_preview("ui_bar", {"fill": 1.0})["frames"][0]
        self.assertNotEqual(empty, full)
        for part in ("frame", "fill"):
            self.assertNotEqual(self.s.forge_preview("ui_bar", {"part": part})["frames"][0], full)
        icons = {self.s.forge_preview("ui_icon", {"kind": k})["frames"][0] for k in BUILDERS["ui_icon"].PARAMS["kind"]["enum"]}
        self.assertEqual(len(icons), len(BUILDERS["ui_icon"].PARAMS["kind"]["enum"]))
        self.assertNotEqual(self.s.forge_preview("ui_icon", {"style": "mono"})["frames"][0], self.s.forge_preview("ui_icon")["frames"][0])
        b = self.s.procedural(self.pid, "ui_button", {"theme": "wood_gold"})
        self.assertEqual(b["qa"]["deterministic"]["status"], "passed", b["qa"]["deterministic"]["issues"])
        self.assertTrue(b["animation"]["full_bleed"])
        self.assertEqual(b["animation"]["canvas"], [96, 32])

    def test_bad_params_are_rejected(self):
        from artstudio.providers.base import GenerationError
        from artstudio.util import StudioError
        for b, p in (("weapon_icon", {"kind": "laser"}), ("lava_burn", {"tiles": 9}), ("status_icon", {"status": "nope"})):
            with self.assertRaises((StudioError, GenerationError), msg=b):
                self.s.forge_preview(b, p)


if __name__ == "__main__":
    unittest.main()
