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


def costume_flat(groups):
    from artstudio.charkit.costume import flatten
    return flatten(groups)


class CharacterKitStaticTests(unittest.TestCase):
    def test_builder_registered(self):
        b = BUILDERS["character_kit"]
        self.assertEqual(b.GROUP, "Characters")
        self.assertEqual(set(b.PARAMS["preset"]["enum"]), {"base", "knight", "mage", "ranger", "priest", "berserker", "necromancer", "skeleton"})
        for a in ("Bow_Attack", "Cast_Spell", "Summon_Rise"):
            self.assertIn(a, b.PARAMS["action"]["enum"])
        self.assertEqual(len(b.PARAMS["action"]["enum"]), 16)
        self.assertEqual(b.pivot(), [32, 44])
        self.assertTrue(b.LOOP(action="Sword_Walk"))
        self.assertFalse(b.LOOP(action="Sword_Attack"))
        self.assertFalse(b.LOOP(action="Bow_Attack"))
        self.assertFalse(b.LOOP(action="Cast_Spell"))
        self.assertFalse(b.LOOP(action="Summon_Rise"))

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

    def test_bow_string_follows_the_draw_hand(self):
        """Side views: while the arrow is nocked the string's pull point is the draw hand — a skin pixel sits where the
        two string lines meet, and it moves back towards the face as the draw deepens."""
        from artstudio.charkit import bow
        frames, _ = charkit.render("ranger", "Bow_Attack", dirs=["side_right", "side_left"])
        for d, sgn in (("side_right", 1), ("side_left", -1)):
            xs = []
            for i in (1, 2, 3):                                   # nock, draw, full draw
                f = costume_flat(frames[d][i])
                px = f.load()
                string = [(x, y) for y in range(64) for x in range(64) if px[x, y] == bow.STRING]
                self.assertTrue(string, (d, i))
                tip = min(string, key=lambda q: sgn * q[0])        # rear-most string pixel = the pull point
                near = [(tip[0] + a, tip[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
                self.assertTrue(any(px[q][:3] != bow.STRING[:3] and px[q][3] and px[q] not in (bow.SHAFT, bow.FLETCH)
                                    for q in near), (d, i))
                xs.append(tip[0])
            self.assertTrue(sgn * xs[0] > sgn * xs[1] > sgn * xs[2], (d, xs))   # hand moves back as it draws

    def test_casters_cast_instead_of_swinging(self):
        from artstudio.charkit import cast
        for p in ("mage", "priest", "necromancer"):
            frames, ms = charkit.render(p, "Sword_Attack")
            self.assertEqual(sum(ms["front"]), sum(x[2] for x in cast.PHASES), p)
            same, _ = charkit.render(p, "Cast_Spell")
            self.assertEqual(costume_flat(frames["side_right"][4]).tobytes(),
                             costume_flat(same["side_right"][4]).tobytes(), p)
        knight, ms = charkit.render("knight", "Sword_Attack")
        self.assertNotEqual(sum(ms["front"]), sum(x[2] for x in cast.PHASES))    # fighters still swing

    def test_skeleton_and_summon_rise(self):
        frames, _ = charkit.render("skeleton", "Sword_Idle", dirs=["front"])
        f = costume_flat(frames["front"][0])
        skin = {(225, 178, 110), (190, 134, 95), (246, 202, 116)}
        self.assertFalse(any(p[3] and p[:3] in skin for p in f.getdata()), "no skin left on the skeleton")
        # undead: jerky (every other frame dropped) and slower than the living base
        walk, wms = charkit.render("skeleton", "Sword_Walk", dirs=["side_right"])
        bwalk, bms = charkit.render("base", "Sword_Walk", dirs=["side_right"])
        self.assertLess(len(walk["side_right"]), len(bwalk["side_right"]))
        self.assertGreater(sum(wms["side_right"]), sum(bms["side_right"]))
        chop, cms = charkit.render("skeleton", "Sword_Attack")          # short chop, no swing trail
        self.assertEqual(len(chop["front"]), len(charkit.STIFF_POSES["Sword_Attack"]))
        knight, _ = charkit.render("knight", "Sword_Attack", dirs=["front"])
        self.assertIsNotNone(knight["front"][4]["front"].getbbox())
        # the torso is a pole: the middle of the chest row is mostly empty
        from artstudio.charkit import skeleton as sk
        body = frames["front"][0]["body"]
        self.assertGreater(sum(1 for x in range(64) for y in range(30, 40) if body.getpixel((x, y))[3] == 0), 300)
        # small wooden shield with a metal band on the off hand
        front = frames["front"][0]["front"]
        wood = {sk.doll.hx(c)[:3] for c in sk.doll.RAMPS["brown"]}
        self.assertTrue(any(p[3] and p[:3] in wood for p in front.getdata()))
        rise, ms = charkit.render("skeleton", "Summon_Rise")
        for d in charkit.DIRS:
            first, last = rise[d][0], rise[d][-1]
            self.assertIsNone(first["body"].getbbox(), d)                         # still under ground
            self.assertIsNotNone(last["body"].getbbox(), d)
            self.assertLessEqual(first["gear"].getbbox()[3] if first["gear"].getbbox() else 0, 46)
        for facing in ("front", "right"):
            for p, act in (("skeleton", "Summon_Rise"), ("necromancer", "Sword_Attack"), ("mage", "Cast_Spell")):
                a = self.s.procedural(self.pid, "character_kit", {"preset": p, "action": act, "facing": facing})
                self.assertFalse(a["animation"]["loop"]["enabled"])
                self.assertEqual(a["qa"]["deterministic"]["status"], "passed", (p, act, a["qa"]["deterministic"]["issues"]))

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
