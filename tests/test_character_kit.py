"""v0.7 character kit: Craftpix base character + five class costumes + synthesised bow attack.
The Craftpix packs are not in the repo (licence), so render tests skip when they are not installed locally
(assets_local/craftpix-base or ARTSTUDIO_CHARKIT_DIR)."""
import json
import os
import unittest

from helpers import cleanup, studio, temp_workspace

from artstudio import charkit
from artstudio.procedural import BUILDERS
from artstudio.util import StudioError

HAVE = charkit.available()


class CharacterKitStaticTests(unittest.TestCase):
    def test_builder_registered(self):
        b = BUILDERS["character_kit"]
        self.assertEqual(b.GROUP, "Characters")
        self.assertEqual(set(b.PARAMS["preset"]["enum"]), {"base", "knight", "mage", "ranger", "priest", "berserker"})
        self.assertIn("Bow_Attack", b.PARAMS["action"]["enum"])
        self.assertEqual(len(b.PARAMS["action"]["enum"]), 14)
        self.assertEqual(b.pivot(), [32, 44])
        self.assertTrue(b.LOOP(action="Sword_Walk"))
        self.assertFalse(b.LOOP(action="Sword_Attack"))
        self.assertFalse(b.LOOP(action="Bow_Attack"))

    def test_missing_pack_is_a_clear_user_error(self):
        old = os.environ.get("ARTSTUDIO_CHARKIT_DIR")
        os.environ["ARTSTUDIO_CHARKIT_DIR"] = os.path.join(os.path.dirname(__file__), "no_such_pack_dir")
        try:
            with self.assertRaises(StudioError) as cm:
                BUILDERS["character_kit"].build()
            self.assertEqual(cm.exception.code, "charkit_base_missing")
            self.assertIn("redistribution", str(cm.exception))
        finally:
            if old is None:
                os.environ.pop("ARTSTUDIO_CHARKIT_DIR", None)
            else:
                os.environ["ARTSTUDIO_CHARKIT_DIR"] = old


@unittest.skipUnless(HAVE, "Craftpix base packs not installed (scripts/setup_character_base.py)")
class CharacterKitRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.pid = cls.s.ws.create_project("C")["id"]

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def test_every_preset_saves_layered_and_passes_qa(self):
        for p in charkit.PRESETS:
            for facing in ("front", "left", "right", "rear"):
                a = self.s.procedural(self.pid, "character_kit", {"preset": p, "facing": facing})
                self.assertEqual(a["animation"]["canvas"], [64, 64], (p, facing))
                self.assertEqual(a["animation"]["pivot"], [32, 44], (p, facing))
                n = len(a["animation"]["frames"])   # pack: back idle = 4 frames; identical frames merge into holds
                self.assertTrue(2 <= n <= (4 if facing == "rear" else 12), (p, facing, n))
                self.assertEqual(a["qa"]["deterministic"]["status"], "passed", (p, facing, a["qa"]["deterministic"]["issues"]))
                self.assertTrue(a["animation"]["loop"]["enabled"], "idle loops")
                doc = self.s.ws.engine_home(self.pid) / "documents" / a["procedural"]["doc_id"] / "doc.json"
                names = [l["name"] for l in json.loads(doc.read_text(encoding="utf-8"))["layers"]]
                self.assertTrue({"body", "gear"} <= set(names), (p, facing, names))

    def test_presets_look_different(self):
        firsts = {p: self.s.forge_preview("character_kit", {"preset": p})["frames"][0] for p in charkit.PRESETS}
        self.assertEqual(len(set(firsts.values())), len(firsts))

    def test_bow_attack_all_facings(self):
        frames, ms = charkit.render("ranger", "Bow_Attack")
        self.assertEqual(set(frames), set(charkit.DIRS))
        for d in charkit.DIRS:
            self.assertEqual(len(frames[d]), 7, d)
            self.assertEqual(sum(ms[d]), 1020, d)
        a = self.s.procedural(self.pid, "character_kit", {"preset": "ranger", "action": "Bow_Attack", "facing": "right"})
        self.assertFalse(a["animation"]["loop"]["enabled"])
        self.assertEqual(a["qa"]["deterministic"]["status"], "passed", a["qa"]["deterministic"]["issues"])

    def test_near_side_weapon_is_drawn_in_front(self):
        """Right-handed: facing right the sword is on the near side (front layer, over the face); facing left it is
        behind the body (back layer)."""
        frames, _ = charkit.render("knight", "Sword_Idle", dirs=["side_right", "side_left"])
        r, l = frames["side_right"][0], frames["side_left"][0]
        self.assertIsNotNone(r["front"].getbbox())
        self.assertIsNone(l["front"].getbbox())

    def test_both_bases_and_all_actions_render(self):
        for sex in charkit.SEXES:
            for act in charkit.ALL_ACTIONS:
                frames, ms = charkit.render("base", act, sex, dirs=["front"])
                self.assertTrue(frames["front"], (sex, act))
                self.assertEqual(len(frames["front"]), len(ms["front"]), (sex, act))
