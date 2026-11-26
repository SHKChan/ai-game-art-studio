"""Sprite editor backend: pixel patches survive reprocessing / re-cutting; reference-from-description; sheet cutting.
The mock provider returns labelled test fixtures (knight sample frames arranged as a sheet) — not AI output."""
import sys
import unittest

from helpers import KNIGHT, ROOT, cleanup, studio, temp_workspace

from PIL import Image

from artstudio import actions as plans
from artstudio.animation import clear_patch, edit_frames, reprocess, save_frame_edits
from artstudio.processing.sheet import SheetRejected, detect_grid, grid_for, process_sheet
from artstudio.util import StudioError

FAKE = f"{sys.executable} {ROOT / 'tests' / 'fake_codex.py'}"


class SpriteEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.s.registry.get("codex").codex_bin = FAKE
        cls.pid = cls.s.ws.create_project("E")["id"]
        c = cls.s.create_character_from_reference(cls.pid, "Knight", KNIGHT / "idle" / "poster.png")
        cls.cid = c["id"]
        plans.save_plan(cls.s.ws, cls.pid, cls.cid, {"actions": [{"preset": "walk"}, {"preset": "attack"}, {"preset": "hit"}]})

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def frame(self, a, i):
        with Image.open(self.s.ws.asset_dir(self.pid, a["id"]) / a["animation"]["frames"][i]["file"]) as im:
            return im.convert("RGBA")

    def test_core_actions_from_mock_sheets(self):
        for aid, n in (("walk", 8), ("attack", 8), ("hit", 4)):
            a = self.s.generate_action(self.pid, self.cid, aid, "mock")
            self.assertTrue(a["provider"]["is_test_fixture"])
            self.assertEqual(len(a["animation"]["frames"]), n)
            self.assertEqual(a["action"]["sheet_qa"]["status"], "pass", a["action"]["sheet_qa"])
            # one scale per sheet, feet on the ground line
            canvas, pivot = a["animation"]["canvas"], a["animation"]["pivot"]
            for i in range(n):
                bb = self.frame(a, i).getchannel("A").getbbox()
                self.assertEqual(bb[3], pivot[1], f"{aid} frame {i} not on the ground line")
            h0 = self.frame(a, 0).getchannel("A").getbbox()
            self.assertLess(abs((h0[3] - h0[1]) - 64), 8)  # reference pose ~ target height (64 px)
            self.assertEqual(a["animation"]["anchor"]["kind"], "ground_torso" if aid == "walk" else "ground")

    def test_patch_survives_reprocess_and_recut(self):
        a = self.s.generate_action(self.pid, self.cid, "hit", "mock")
        im = self.frame(a, 1)
        bb = im.getchannel("A").getbbox()
        x, y = bb[0] + 3, bb[1] + 5
        im.putpixel((x, y), (255, 0, 255, 255))           # recolour one pixel
        ex, ey = bb[2] - 1, bb[3] - 1
        while im.getpixel((ex, ey))[3] == 0:
            ex -= 1
        im.putpixel((ex, ey), (0, 0, 0, 0))                 # erase one pixel
        a = save_frame_edits(self.s.ws, a, [{"index": 1, "image": im}])
        p = a["animation"]["frames"][1]["patch"]
        self.assertEqual(p["pixels"], 2)
        self.assertEqual(self.frame(a, 1).getpixel((x, y)), (255, 0, 255, 255))
        # reprocess with a bigger canvas: pivot moves, the patch follows it
        cw, ch = a["animation"]["canvas"]
        a = reprocess(self.s.ws, a, {"canvas": [cw + 20, ch + 10], "pivot": [a["animation"]["pivot"][0] + 10, a["animation"]["pivot"][1] + 10]})
        f = self.frame(a, 1)
        self.assertEqual(f.getpixel((x + 10, y + 10)), (255, 0, 255, 255))
        self.assertEqual(f.getpixel((ex + 10, ey + 10))[3], 0)
        self.assertFalse(a["animation"]["frames"][1]["patch"]["stale"])
        # re-cut at another size: patch kept but flagged stale
        a = self.s.recut_action(self.pid, a["id"], {"target_height": 48})
        self.assertTrue(a["animation"]["frames"][1]["patch"]["stale"])
        h = self.frame(a, 0).getchannel("A").getbbox()
        self.assertLess(abs((h[3] - h[1]) - 48), 6)
        # duplicate copies the patch; clearing restores the base
        a = edit_frames(self.s.ws, a, "duplicate", index=1)
        self.assertTrue(a["animation"]["frames"][2]["patch"])
        self.assertNotEqual(a["animation"]["frames"][2]["patch"]["paint"], a["animation"]["frames"][1]["patch"]["paint"])
        a = clear_patch(self.s.ws, a, 1)
        self.assertIsNone(a["animation"]["frames"][1]["patch"])
        with self.assertRaises(StudioError):
            save_frame_edits(self.s.ws, a, [{"index": 0, "image": Image.new("RGBA", (5, 5))}])

    def test_reference_from_description(self):
        c = self.s.create_character_from_description(self.pid, "Mage", "small mage with a blue hat and a wooden staff")
        self.assertFalse(c["masters"])
        r = self.s.generate_reference_candidates(self.pid, c["id"], "codex", 4)
        self.assertEqual(len(r["candidates"]), 4)
        self.assertIn("blue hat", r["prompt"])
        c = self.s.pick_reference(self.pid, c["id"], r["candidates"][2])
        self.assertTrue(c["masters"]["right"]["locked"])
        c = self.s.pick_reference(self.pid, c["id"], r["candidates"][0])  # picking again replaces, keeping history
        self.assertEqual(c["masters"]["right"]["candidate"], r["candidates"][0])
        with self.assertRaises(StudioError):
            self.s.create_character_from_description(self.pid, "Empty", "  ")


class SheetTests(unittest.TestCase):
    def sheet(self, n, cols, rows, k=16 / 3, skip=()):
        from artstudio.adapters import knight_frames
        fr, _, _ = knight_frames("run")
        cw, ch = fr[0].size
        sh = Image.new("RGBA", (round(cw * cols * k), round(ch * rows * k)), (255, 255, 255, 255))
        for i in range(n):
            if i in skip:
                continue
            f = fr[i % len(fr)]
            sh.alpha_composite(f.resize((round(f.width * k), round(f.height * k)), Image.Resampling.NEAREST),
                               (round(i % cols * cw * k), round(i // cols * ch * k)))
        return sh

    def test_detect_grid(self):
        im = Image.open(KNIGHT / "idle" / "poster.png").convert("RGBA")
        for k in (4, 6):
            self.assertEqual(detect_grid(im.resize((im.width * k, im.height * k), Image.Resampling.NEAREST))["block"], k)

    def test_cut_and_reject(self):
        frames, rec = process_sheet(self.sheet(8, 4, 2), 8, 4, 2, {"target_height": 64})
        self.assertEqual(len(frames), 8)
        self.assertEqual(rec["qa"]["status"], "pass")
        self.assertEqual(len({f.size for f in frames}), 1)
        for f in frames:
            self.assertEqual(set(f.getchannel("A").getextrema()) <= {0, 255}, True)
        with self.assertRaises(SheetRejected) as cm:
            process_sheet(self.sheet(8, 4, 2, skip=(5,)), 8, 4, 2)
        self.assertEqual(cm.exception.record["issues"][0]["code"], "empty_cell")
        self.assertEqual(grid_for(4), (2, 2))


if __name__ == "__main__":
    unittest.main()
