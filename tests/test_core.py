"""Workspace, schema, character master system, processing, QA and export tests (offline)."""
import json
import plistlib
import unittest
import zipfile
from pathlib import Path

from helpers import KNIGHT, SHOWCASE_GIF, cleanup, sprite, studio, temp_workspace

from PIL import Image

from artstudio.animation import create_animation_asset, edit_frames, load_frames, replace_frame, reprocess
from artstudio.export import export_assets, pack_shelf
from artstudio.processing.frames import (alpha_bbox, depixelate, detect_background, estimate_pixel_scale, normalize_group,
                                         remove_background, slice_auto, slice_grid)
from artstudio.processing.importers import extract_animation
from artstudio.qa import check_asset, check_frames
from artstudio.schema import validate
from artstudio.util import StudioError, safe_join
from artstudio.workspace import Conflict, Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temp_workspace()
        self.ws = Workspace(self.tmp)
        self.p = self.ws.create_project("Test", default_style="pixel")

    def tearDown(self):
        cleanup(self.tmp)

    def test_safe_join_rejects_traversal(self):
        for bad in ("../x", "/etc/passwd", "C:\\x", "a/../../b"):
            with self.assertRaises(StudioError):
                safe_join(self.tmp, bad)

    def test_asset_schema_validation(self):
        a = create_animation_asset(self.ws, self.p["id"], "s", [sprite()], mode="pixel")
        self.assertEqual(validate(a, "asset"), [])
        a["animation"]["frames"][0]["duration_ms"] = -5
        self.assertTrue(validate(a, "asset"))
        with self.assertRaises(StudioError):
            self.ws.save_asset(a)

    def test_master_lock_and_explicit_replace(self):
        c = self.ws.create_character(self.p["id"], "Hero", "four", "pixel")
        self.assertEqual(c["directions"], ["south", "east", "north", "west"])
        f = self.tmp / "m.png"
        sprite().save(f)
        c = self.ws.add_character_image(self.p["id"], c["id"], f, "candidate", "south")
        cand = c["candidates"][0]["id"]
        c = self.ws.review_candidate(self.p["id"], c["id"], cand, "approved")
        self.assertTrue(c["masters"]["south"]["locked"])
        c = self.ws.add_character_image(self.p["id"], c["id"], f, "candidate", "south")
        cand2 = c["candidates"][-1]["id"]
        with self.assertRaises(Conflict):
            self.ws.review_candidate(self.p["id"], c["id"], cand2, "approved")
        with self.assertRaises(StudioError):
            self.ws.replace_master(self.p["id"], c["id"], "south", cand2, "")
        c = self.ws.replace_master(self.p["id"], c["id"], "south", cand2, "new costume revision")
        self.assertEqual(c["masters"]["south"]["candidate"], cand2)
        self.assertIn("master_replaced", [h["event"] for h in c["history"]])
        self.assertEqual(self.ws.missing_directions(c), ["east", "north", "west"])

    def test_optional_mirroring(self):
        c = self.ws.create_character(self.p["id"], "Side", "side2", "pixel")
        self.assertFalse(c["mirroring"]["enabled"])
        c = self.ws.update_character(self.p["id"], c["id"], {"mirroring": {"enabled": True, "pairs": {"left": "right"}}})
        f = self.tmp / "m.png"
        sprite().save(f)
        c = self.ws.add_character_image(self.p["id"], c["id"], f, "candidate", "right")
        c = self.ws.review_candidate(self.p["id"], c["id"], c["candidates"][0]["id"], "approved")
        self.assertEqual(self.ws.missing_directions(c), [])

    def test_backup_restore_roundtrip(self):
        a = create_animation_asset(self.ws, self.p["id"], "s", [sprite(), sprite(y_shift=1)], mode="pixel")
        z = self.ws.backup(self.tmp / ".." / f"{self.tmp.name}.zip")
        target = self.tmp.parent / (self.tmp.name + "-restored")
        try:
            w2 = Workspace.restore(z, target)
            b = w2.get_asset(self.p["id"], a["id"])
            self.assertEqual(len(load_frames(w2, b)), 2)
        finally:
            cleanup(target)
            z.unlink()

    def test_frame_edit_ops_and_versions(self):
        a = create_animation_asset(self.ws, self.p["id"], "s", [sprite(), sprite(y_shift=2), sprite(y_shift=4)], mode="pixel",
                                   events=[{"frame": 2, "type": "hit"}])
        a = edit_frames(self.ws, a, "duplicate", index=0)
        self.assertEqual(len(a["animation"]["frames"]), 4)
        self.assertEqual(a["animation"]["events"][0]["frame"], 3)
        a = edit_frames(self.ws, a, "move", index=3, to=0)
        self.assertEqual(a["animation"]["events"][0]["frame"], 0)
        a = edit_frames(self.ws, a, "delete", index=1)
        a = edit_frames(self.ws, a, "duration", index=0, duration_ms=250)
        a = edit_frames(self.ws, a, "reject", index=1)
        self.assertEqual(len(load_frames(self.ws, a)), 2)
        a = edit_frames(self.ws, a, "loop", enabled=False)
        self.assertFalse(a["animation"]["loop"]["enabled"])
        n_before = len(a["animation"]["frames"])
        v = a["versions"][1]["version"]
        a = self.ws.restore_version(self.p["id"], a["id"], v)
        self.assertNotEqual(len(a["animation"]["frames"]), 0)
        with self.assertRaises(StudioError):
            edit_frames(self.ws, a, "duration", index=0, duration_ms=0)
        self.assertGreater(n_before, 0)

    def test_manual_replacement_keeps_group_scale(self):
        a = create_animation_asset(self.ws, self.p["id"], "s", [sprite(), sprite()], mode="pixel", params={"scale": 2})
        a = replace_frame(self.ws, a, 1, sprite(color=(40, 200, 40, 255)))
        fr = load_frames(self.ws, a)
        b0, b1 = alpha_bbox(fr[0][1]), alpha_bbox(fr[1][1])
        self.assertEqual(b0[3] - b0[1], b1[3] - b1[1])  # same scale as group
        self.assertEqual(a["animation"]["frames"][1]["origin"], "manual")


class ProcessingTests(unittest.TestCase):
    def test_background_removal_pixel_binary(self):
        im = sprite(bg=(0, 255, 0, 255))
        self.assertEqual(detect_background(im)["kind"], "solid")
        out, info = remove_background(im, mode="pixel")
        a = out.getchannel("A")
        self.assertEqual(set(a.getdata()) - {0, 255}, set())
        self.assertEqual(out.getpixel((0, 0))[3], 0)
        self.assertEqual(out.getpixel((15, 20))[3], 255)

    def test_background_removal_hd_soft_edges(self):
        im = sprite(64, 96, bg=(255, 255, 255, 255)).resize((64, 96))
        im = Image.new("RGBA", (128, 192), (255, 255, 255, 255))
        im.alpha_composite(sprite(64, 96).resize((128, 192), Image.Resampling.LANCZOS))
        out, _ = remove_background(im, mode="hd", tolerance=20)
        vals = set(out.getchannel("A").getdata())
        self.assertTrue(any(0 < v < 255 for v in vals), "HD mode must preserve partial alpha")

    def test_checker_background(self):
        im = Image.new("RGBA", (40, 40))
        for y in range(40):
            for x in range(40):
                im.putpixel((x, y), (204, 204, 204, 255) if (x // 8 + y // 8) % 2 else (255, 255, 255, 255))
        im.alpha_composite(sprite(), (4, 0))
        self.assertEqual(detect_background(im)["kind"], "checker")
        out, _ = remove_background(im, mode="pixel")
        self.assertEqual(out.getpixel((0, 0))[3], 0)

    def test_slice_grid_and_auto_keeps_detached_weapon(self):
        sheet = Image.new("RGBA", (128, 48))
        for i in range(4):
            sheet.alpha_composite(sprite(weapon=True), (i * 32, 0))
        self.assertEqual(len(slice_grid(sheet, 4, 1)), 4)
        parts = slice_auto(sheet, merge_px=3)
        self.assertEqual(len(parts), 4)
        self.assertGreaterEqual(parts[0][1][2], 20)  # weapon included in the crop width

    def test_uniform_group_scale_and_no_crop(self):
        small, big = sprite(), Image.new("RGBA", (32, 48))
        big.alpha_composite(sprite(weapon=True))
        frames, rec = normalize_group([small, big], {"mode": "pixel", "scale": 2, "canvas": [40, 40], "pivot": [20, 38]})
        self.assertTrue(rec["canvas_expanded"])  # never crops: canvas grows
        for f in frames:
            bb = alpha_bbox(f)
            self.assertTrue(bb[0] > 0 and bb[1] > 0 and bb[2] < f.width and bb[3] < f.height)
        h = [alpha_bbox(f)[3] - alpha_bbox(f)[1] for f in frames]
        self.assertEqual(h[0], 2 * (alpha_bbox(small)[3] - alpha_bbox(small)[1]))

    def test_ground_anchor_preserves_airborne(self):
        fr = [sprite(), sprite(y_shift=-6)]  # second frame jumps up
        out, rec = normalize_group(fr, {"mode": "pixel", "anchor": "ground", "airborne": [1]})
        b0, b1 = alpha_bbox(out[0]), alpha_bbox(out[1])
        self.assertEqual(b1[3], b0[3] - 6)
        out2, _ = normalize_group(fr, {"mode": "pixel", "anchor": "ground"})
        self.assertEqual(alpha_bbox(out2[0])[3], alpha_bbox(out2[1])[3])

    def test_source_anchor_keeps_motion(self):
        fr = [sprite(), sprite(x_shift=3, y_shift=-2)]
        out, _ = normalize_group(fr, {"mode": "pixel"})
        b0, b1 = alpha_bbox(out[0]), alpha_bbox(out[1])
        self.assertEqual((b1[0] - b0[0], b1[1] - b0[1]), (3, -2))

    def test_hd_mode_keeps_partial_alpha(self):
        im = sprite(64, 96).resize((64, 96)).resize((48, 72), Image.Resampling.LANCZOS)
        out, _ = normalize_group([im], {"mode": "hd", "scale": 1.5})
        self.assertTrue(any(0 < v < 255 for v in out[0].getchannel("A").getdata()))

    def test_pixel_scale_detection(self):
        im = sprite().resize((32 * 6, 48 * 6), Image.Resampling.NEAREST)
        self.assertEqual(estimate_pixel_scale(im), 6)
        self.assertEqual(depixelate(im, 6).size, (32, 48))

    def test_gif_extraction_from_upstream_showcase(self):
        frames = extract_animation(SHOWCASE_GIF / "explosion.gif")
        self.assertGreaterEqual(len(frames), 5)
        self.assertTrue(all(d >= 10 for _, d in frames))


class QATests(unittest.TestCase):
    def codes(self, issues):
        return {i["code"] for i in issues}

    def test_detects_problems(self):
        empty = Image.new("RGBA", (32, 48))
        opaque = Image.new("RGBA", (32, 48), (10, 10, 10, 255))
        clipped = Image.new("RGBA", (32, 48))
        clipped.alpha_composite(sprite(), (-10, 0))
        good = sprite()
        c = self.codes(check_frames([good, good, empty, opaque, clipped], [100, 100, 0, 100, 100]))
        for code in ("duplicate_frame", "empty_frame", "no_transparency", "clipped_sprite", "invalid_duration"):
            self.assertIn(code, c)

    def test_inconsistent_canvas(self):
        self.assertIn("inconsistent_canvas", self.codes(check_frames([sprite(), sprite(40, 48)], [100, 100])))


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temp_workspace()
        self.ws = Workspace(self.tmp)
        self.p = self.ws.create_project("E")

    def tearDown(self):
        cleanup(self.tmp)

    def test_packer(self):
        pos, (W, H) = pack_shelf([(10, 20), (30, 5), (8, 8)] * 10, 256, 2)
        rects = [(x, y, x + w, y + h) for (x, y), (w, h) in zip(pos, [(10, 20), (30, 5), (8, 8)] * 10)]
        for i, a in enumerate(rects):
            self.assertTrue(a[2] <= W and a[3] <= H)
            for b in rects[i + 1:]:
                self.assertFalse(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3], "overlap")

    def test_full_export_formats(self):
        idle = Image.open(KNIGHT / "idle" / "atlas.png").convert("RGBA")
        frames = [(f, 120) for f, _ in slice_grid(idle, 4, 2)]
        a = create_animation_asset(self.ws, self.p["id"], "idle", frames, anim_name="idle", direction="east", mode="pixel",
                                   events=[{"frame": 2, "type": "blink"}])
        m = export_assets(self.ws, self.p["id"], [a["id"]], name="t")
        out = Path(m["path"])
        self.assertEqual(m["qa"]["status"], "passed", m["qa"])
        for rel in m["files"]:
            self.assertTrue((out / rel).is_file(), rel)
        tp = json.loads((out / "t_atlas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(tp["frames"]), 8)
        self.assertIn("idle_east", tp["animations"])
        pl = plistlib.loads((out / "cocos" / "t.plist").read_bytes())
        self.assertEqual(pl["metadata"]["format"], 2)
        self.assertEqual(len(pl["frames"]), 8)
        meta = json.loads((out / "t.anim.json").read_text(encoding="utf-8"))
        anim = meta["animations"][0]
        self.assertEqual(anim["events"][0]["time_ms"], 240)
        with Image.open(out / anim["atlas"]) as atl:
            for f in anim["frames"]:
                r = f["atlas"]
                crop = atl.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
                self.assertIsNotNone(crop.getbbox())
        with Image.open(out / anim["previews"]["gif"]) as g:
            self.assertEqual(g.n_frames, 8)
        with zipfile.ZipFile(out / "t.zip") as z:
            self.assertIn("cocos/t.plist", z.namelist())


if __name__ == "__main__":
    unittest.main()
