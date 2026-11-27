"""v0.9 asset packs + search tags.

Pack art is third-party and not in the repo, so these tests build small *synthetic* packs (geometric test fixtures
in the packs' real folder layouts) in a temp dir. Tests marked `real` also run against the installed packs in
assets_local/packs when they are present, and skip otherwise."""
import http.client
import io
import json
import os
import threading
import unittest
import zipfile
from pathlib import Path

from helpers import ROOT, cleanup, studio, temp_workspace
from PIL import Image, ImageDraw

from artstudio import packs
from artstudio.tagging import BUILDER_TAGS, builder_tags, normalize_tag, normalize_tags
from artstudio.util import StudioError

REAL = Path(os.environ.get("ARTSTUDIO_REAL_PACKS", ROOT / "assets_local" / "packs"))


def _img(path):
    with Image.open(path) as im:
        return im.convert("RGBA")


def blob(w, h, boxes, color=(200, 60, 60, 255), soft=None):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for b in boxes:
        d.rectangle(b, fill=color)
    if soft:
        d.rectangle(soft, fill=(255, 220, 120, 90))
    return im


def strip(n, cell=100, dx=0):
    im = Image.new("RGBA", (n * cell, cell), (0, 0, 0, 0))
    for i in range(n):
        im.alpha_composite(blob(cell, cell, [(40 + dx, 40 + i, 59 + dx, 70)]), (i * cell, 0))
    return im


def make_fixture_packs(root: Path) -> Path:
    # Tiny RPG
    for folder, acts in {"Soldier": {"Idle": 6, "Attack01": 6, "Death": 4}, "Orc": {"Walk": 8}}.items():
        for sub in (folder, f"{folder} with shadows"):
            d = root / "tiny-rpg" / folder / sub
            d.mkdir(parents=True, exist_ok=True)
            for a, n in acts.items():
                strip(n).save(d / f"{folder}_{a}.png")
            strip(8).save(d / f"{folder}.png")       # combined overview sheet → must be skipped
    # Craftpix dungeon
    png = root / "craftpix-dungeon" / "PNG"
    png.mkdir(parents=True)
    tiles = Image.new("RGBA", (208, 368), (0, 0, 0, 0))
    ImageDraw.Draw(tiles).rectangle((0, 0, 47, 47), fill=(90, 90, 110, 255))
    tiles.save(png / "walls_floor.png")
    fire = Image.new("RGBA", (176, 288), (0, 0, 0, 0))
    for r in range(6):
        for x0, w in ((0, 32), (32, 48), (80, 48), (128, 48)):
            ImageDraw.Draw(fire).rectangle((x0 + 8, r * 48 + 20 - r, x0 + w - 9, r * 48 + 40), fill=(255, 140, 40, 255))
    fire.save(png / "fire_animation.png")
    tiled = root / "craftpix-dungeon" / "Tiled_files"
    tiled.mkdir()
    ts = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    ImageDraw.Draw(ts).rectangle((0, 0, 15, 15), fill=(40, 90, 200, 255))
    ImageDraw.Draw(ts).rectangle((16, 0, 31, 15), fill=(80, 160, 255, 255))
    ts.save(tiled / "water.png")
    chunk = ",".join(["1"] * 16 + ["0"] * 240)
    (tiled / "Dungeon1.tmx").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" orientation="orthogonal" renderorder="right-down" width="16" height="16" tilewidth="16" tileheight="16" infinite="1">
 <tileset firstgid="1" name="water" tilewidth="16" tileheight="16" tilecount="2" columns="2">
  <image source="water.png" width="32" height="16"/>
  <tile id="0"><animation><frame tileid="0" duration="150"/><frame tileid="1" duration="150"/></animation></tile>
 </tileset>
 <layer id="1" name="water" width="16" height="16"><data encoding="csv"><chunk x="-16" y="0" width="16" height="16">{chunk}</chunk></data></layer>
</map>""", encoding="utf-8")
    # PVFX
    pv = root / "pvfx-foundry"
    effects = []
    for cat, name, loop in (("fire", "fireball-impact", False), ("ambient", "candle-flame", True)):
        g = pv / "effects" / cat / name / "lit" / "grid"
        g.mkdir(parents=True)
        sheet = Image.new("RGBA", (96, 32), (0, 0, 0, 0))
        sheet.alpha_composite(blob(32, 32, [(10, 10, 20, 30)], soft=(4, 4, 28, 9)), (0, 0))
        sheet.alpha_composite(blob(32, 32, [(8, 8, 22, 30)]), (32, 0))   # third cell left blank (a pause)
        sheet.save(g / "sprite-sheet.png")
        frames = [{"frame": i, "duration": {"numerator_ms": 70 + 10 * i, "denominator": 1},
                   "sheet": {"image": "sprite-sheet.png", "x": 32 * i, "y": 0, "width": 32, "height": 32, "scale": 1}} for i in range(3)]
        (g / "manifest.json").write_text(json.dumps({"tier": "lit", "loop_mode": "loop" if loop else "none", "source_size": [32, 32],
                                                      "pivot": [16, 40], "frames": frames}), encoding="utf-8")
        art = {"lit": {"grid": {"manifest": f"effects/{cat}/{name}/lit/grid/manifest.json", "sheet": "x"}},
               "strict": {"grid": {"manifest": f"effects/{cat}/{name}/strict/grid/manifest.json", "sheet": "x"}}}
        effects.append({"id": f"{cat}/{name}", "name": name.replace("-", " ").title(), "category": cat, "frames": 3, "loop": loop,
                        "tags": ["impact", "flagship"] if cat == "fire" else ["ambient", "loop"], "artifacts": art,
                        "description": "synthetic", "variants": {"frost": {"artifacts": art}} if cat == "fire" else {}})
    (pv / "pack.json").write_text(json.dumps({"schema": "pvfx.asset-pack/1", "effects": effects}), encoding="utf-8")
    return root


class TagTests(unittest.TestCase):
    def test_normalize_english_only(self):
        self.assertEqual(normalize_tag("Top Down"), "top-down")
        self.assertEqual(normalize_tag("action:Walk"), "action:walk")
        self.assertIsNone(normalize_tag("火焰"))
        self.assertIsNone(normalize_tag("  "))
        self.assertEqual(normalize_tags(["Fire", "fire", "地牢", "lava_burn", None, "a b  c"]), ["fire", "lava_burn", "a-b-c"])

    def test_every_builder_is_tagged(self):
        from artstudio.procedural import BUILDERS
        for k in BUILDERS:
            self.assertIn(k, BUILDER_TAGS, k)
            self.assertEqual(BUILDER_TAGS[k], normalize_tags(BUILDER_TAGS[k]), k)
        self.assertIn("dungeon", builder_tags("chest"))
        self.assertIn("scene", builder_tags("hero_shrine"))
        self.assertTrue({"spell", "fire"} <= set(builder_tags("meteor")))
        sk = builder_tags("character_kit", {"preset": "skeleton", "action": "Sword_Walk"})
        self.assertTrue({"monster", "undead", "skeleton", "action:sword_walk"} <= set(sk))
        self.assertNotIn("monster", builder_tags("character_kit", {"preset": "knight"}))

    def test_saved_assets_keep_only_english_tags(self):
        tmp = temp_workspace()
        try:
            s = studio(tmp)
            pid = s.ws.create_project("T")["id"]
            a = s.procedural(pid, "chest")
            self.assertIn("dungeon", a["tags"])
            a["tags"] += ["宝箱", "Treasure Room"]
            a = s.ws.save_asset(a)
            self.assertIn("treasure-room", a["tags"])
            self.assertFalse(any(ord(c) > 127 for t in a["tags"] for c in t))
        finally:
            cleanup(tmp)

    def test_retag_existing_assets(self):
        tmp = temp_workspace()
        try:
            s = studio(tmp)
            pid = s.ws.create_project("T")["id"]
            a = s.procedural(pid, "hero_shrine")
            a["tags"] = ["procedural", "hero_shrine", "mine"]          # as saved before v0.9
            s.ws.save_asset(a)
            r = s.retag(pid)
            self.assertEqual(r["retagged"], [a["id"]])
            tags = s.ws.get_asset(pid, a["id"])["tags"]
            self.assertTrue({"dungeon", "scene", "mine"} <= set(tags))
            self.assertEqual(s.retag(pid)["retagged"], [])
        finally:
            cleanup(tmp)

    def test_blank_frames_allowed_but_not_all(self):
        from artstudio.processing.frames import normalize_group
        empty = Image.new("RGBA", (16, 16))
        out, rec = normalize_group([blob(16, 16, [(4, 4, 10, 12)]), empty], {"anchor": "source", "padding": 0})
        self.assertEqual(len(out), 2)
        with self.assertRaises(StudioError):
            normalize_group([empty, empty])


class PackFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.old = os.environ.get("ARTSTUDIO_PACKS_DIR")
        os.environ["ARTSTUDIO_PACKS_DIR"] = str(make_fixture_packs(cls.tmp / "packs"))
        cls.s = studio(cls.tmp / "ws")
        cls.pid = cls.s.ws.create_project("Packs")["id"]

    @classmethod
    def tearDownClass(cls):
        if cls.old is None:
            os.environ.pop("ARTSTUDIO_PACKS_DIR", None)
        else:
            os.environ["ARTSTUDIO_PACKS_DIR"] = cls.old
        cleanup(cls.tmp)

    def test_listing_and_tag_filter(self):
        info = {p["id"]: p for p in packs.list_packs()}
        self.assertTrue(all(info[k]["available"] for k in ("tiny-rpg", "craftpix-dungeon", "pvfx-foundry")))
        tiny = packs.items("tiny-rpg")
        self.assertEqual(sorted(i["id"] for i in tiny), ["orc/walk", "soldier/attack01", "soldier/death", "soldier/idle"])
        self.assertEqual([i["id"] for i in packs.items("tiny-rpg", tags=["monster"])], ["orc/walk"])
        self.assertEqual([i["id"] for i in packs.items("tiny-rpg", tags=["Hero", "action:death"])], ["soldier/death"])
        self.assertEqual(packs.items("tiny-rpg", tags=["dragon"]), [])
        dun = {i["id"]: i for i in packs.items("craftpix-dungeon")}
        self.assertIn("scene/dungeon1", dun)
        self.assertTrue(all("dungeon" in i["tags"] for i in dun.values()))
        fx = {i["id"]: i for i in packs.items("pvfx-foundry")}
        self.assertTrue({"spell", "magic", "skill", "fire"} <= set(fx["fire/fireball-impact"]["tags"]))
        self.assertNotIn("flagship", fx["fire/fireball-impact"]["tags"])
        self.assertIn("scenery", fx["ambient/candle-flame"]["tags"])
        self.assertEqual(len(packs.items("pvfx-foundry", {"variants": True})), 3)
        with self.assertRaises(StudioError):
            packs.items("pvfx-foundry", {"tier": "neon"})

    def test_import_tiny_rpg_characters(self):
        r = self.s.import_pack(self.pid, "tiny-rpg", tags=["soldier"])
        self.assertEqual(len(r["imported"]), 3)
        self.assertEqual(len(r["characters"]), 1)
        c = self.s.ws.get_character(self.pid, r["characters"][0])
        self.assertEqual((c["name"], c["direction_mode"], c["camera"]), ("Soldier", "side2", "side"))
        assets = {a["animation"]["name"]: a for a in self.s.ws.list_assets(self.pid, character_id=c["id"])}
        idle, death = assets["idle"], assets["death"]
        self.assertEqual(idle["animation"]["canvas"], [100, 100])
        self.assertEqual(idle["animation"]["pivot"], [50, 71])
        self.assertTrue(idle["animation"]["loop"]["enabled"])
        self.assertFalse(death["animation"]["loop"]["enabled"])
        self.assertTrue(death["animation"]["loop"]["hold_last"])
        self.assertEqual(len(idle["animation"]["frames"]), 6)
        self.assertEqual(idle["animation"]["direction"], "right")
        self.assertIn("action:idle", idle["tags"])
        self.assertNotEqual(idle["qa"]["deterministic"]["status"], "failed", idle["qa"]["deterministic"])
        again = self.s.import_pack(self.pid, "tiny-rpg", tags=["soldier"])
        self.assertEqual((len(again["imported"]), len(again["skipped"])), (0, 3))
        orc = self.s.import_pack(self.pid, "tiny-rpg", ["orc/walk"])
        self.assertEqual(len(orc["characters"]), 1)

    def test_import_dungeon_exact_pixels_and_scene(self):
        r = self.s.import_pack(self.pid, "craftpix-dungeon")
        got = {self.s.ws.get_asset(self.pid, a)["processing"]["import"]["pack_item"]: self.s.ws.get_asset(self.pid, a) for a in r["imported"]}
        ts = got["tileset/walls_floor"]
        self.assertEqual(ts["type"], "tileset")
        self.assertEqual(ts["tileset"]["columns"], 13)
        frame = _img(self.s.ws.asset_dir(self.pid, ts["id"]) / ts["animation"]["frames"][0]["file"])
        src = _img(Path(os.environ["ARTSTUDIO_PACKS_DIR"]) / "craftpix-dungeon" / "PNG" / "walls_floor.png")
        self.assertEqual(frame.size, src.size)
        self.assertEqual(frame.tobytes(), src.convert("RGBA").tobytes())
        torch = got["prop/torch"]
        self.assertEqual((torch["animation"]["canvas"], len(torch["animation"]["frames"])), ([48, 48], 6))
        scene = got["scene/dungeon1"]
        self.assertEqual(scene["type"], "environment")
        self.assertEqual(scene["animation"]["canvas"], [256, 16])
        fr = [_img(self.s.ws.asset_dir(self.pid, scene["id"]) / f["file"]) for f in scene["animation"]["frames"]]
        self.assertEqual(len(fr), 2)
        self.assertNotEqual(fr[0].tobytes(), fr[1].tobytes())          # animated water tile
        self.assertEqual(scene["animation"]["frames"][0]["duration_ms"], 150)

    def test_import_pvfx_keeps_soft_alpha_timing_and_pauses(self):
        r = self.s.import_pack(self.pid, "pvfx-foundry", ["fire/fireball-impact"])
        a = self.s.ws.get_asset(self.pid, r["imported"][0])
        self.assertEqual(a["type"], "effect")
        self.assertEqual([f["duration_ms"] for f in a["animation"]["frames"]], [70, 80, 90])
        im = _img(self.s.ws.asset_dir(self.pid, a["id"]) / a["animation"]["frames"][0]["file"])
        self.assertGreater(im.getchannel("A").histogram()[90], 0)       # glow kept (lit tier)
        last = _img(self.s.ws.asset_dir(self.pid, a["id"]) / a["animation"]["frames"][2]["file"])
        self.assertIsNone(last.getbbox())                                 # pause frame kept
        self.assertEqual(a["animation"]["pivot"], [16, 31])               # clamped into the cell
        self.assertNotEqual(a["qa"]["deterministic"]["status"], "failed", a["qa"]["deterministic"])
        self.assertIn("spell", a["tags"])

    def test_missing_pack_is_a_clear_error(self):
        old = os.environ["ARTSTUDIO_PACKS_DIR"]
        os.environ["ARTSTUDIO_PACKS_DIR"] = str(self.tmp / "nope")
        try:
            with self.assertRaises(StudioError) as cm:
                self.s.import_pack(self.pid, "tiny-rpg")
            self.assertIn("setup_asset_packs.py", str(cm.exception))
            self.assertFalse(any(p["available"] for p in packs.list_packs()))
        finally:
            os.environ["ARTSTUDIO_PACKS_DIR"] = old

    def test_http_api(self):
        from artstudio.server.app import TOKEN, make_server
        srv = make_server(self.s, "127.0.0.1", 0)
        port = srv.server_address[1]
        srv.RequestHandlerClass.allowed_hosts = {f"127.0.0.1:{port}"}
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            def req(method, path, body=None):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                c.request(method, path, json.dumps(body) if body is not None else None,
                          {"Host": f"127.0.0.1:{port}", "Cookie": f"artstudio={TOKEN}", "Content-Type": "application/json"})
                r = c.getresponse()
                out = r.status, r.read()
                c.close()
                return out
            st, body = req("GET", "/api/packs/tiny-rpg/items?tags=monster")
            self.assertEqual(st, 200, body)
            self.assertEqual([i["id"] for i in json.loads(body)["items"]], ["orc/walk"])
            st, body = req("GET", "/api/packs/pvfx-foundry/thumb?item=fire/fireball-impact")
            self.assertEqual((st, Image.open(io.BytesIO(body)).format), (200, "PNG"))
            st, body = req("GET", "/api/forge/builders")
            self.assertIn("dungeon", json.loads(body)["builders"]["chest"]["tags"])
            st, body = req("POST", f"/api/projects/{self.pid}/packs/import", {"pack": "pvfx-foundry", "items": ["ambient/candle-flame"]})
            self.assertEqual(st, 200, body)
            job = json.loads(body)
            for _ in range(200):
                j = json.loads(req("GET", f"/api/jobs/{job['id']}")[1])
                if j["status"] in ("succeeded", "failed"):
                    break
                threading.Event().wait(0.05)
            self.assertEqual(j["status"], "succeeded", j)
            self.assertEqual(len(j["result"]["imported"]), 1)
        finally:
            srv.shutdown()


class ProjectDeleteTests(unittest.TestCase):
    def test_delete_moves_project_to_trash(self):
        tmp = temp_workspace()
        try:
            s = studio(tmp)
            pid = s.ws.create_project("Old Stuff")["id"]
            s.procedural(pid, "potion")
            with self.assertRaises(StudioError):
                s.ws.trash_project(pid, "old stuff")                      # must match exactly
            r = s.ws.trash_project(pid, "Old Stuff")
            self.assertNotIn(pid, [p["id"] for p in s.ws.list_projects()])
            trash = Path(r["trash"])
            self.assertTrue((trash / "project.json").is_file())
            self.assertEqual(trash.parent, tmp / "_trash")
            self.assertEqual(len(list((trash / "assets").glob("*/asset.json"))), 1)   # recoverable
            with self.assertRaises(StudioError):
                s.ws.get_project(pid)
        finally:
            cleanup(tmp)

    def test_delete_via_http_needs_confirmation(self):
        tmp = temp_workspace()
        s = studio(tmp)
        from artstudio.server.app import TOKEN, make_server
        srv = make_server(s, "127.0.0.1", 0)
        port = srv.server_address[1]
        srv.RequestHandlerClass.allowed_hosts = {f"127.0.0.1:{port}"}
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            def req(method, path, body=None):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                c.request(method, path, json.dumps(body) if body is not None else None,
                          {"Host": f"127.0.0.1:{port}", "Cookie": f"artstudio={TOKEN}", "Content-Type": "application/json"})
                r = c.getresponse()
                out = r.status, r.read()
                c.close()
                return out
            pid = s.ws.create_project("Bye")["id"]
            st, _ = req("DELETE", f"/api/projects/{pid}", {})
            self.assertGreaterEqual(st, 400)
            self.assertIn(pid, [p["id"] for p in s.ws.list_projects()])
            st, body = req("DELETE", f"/api/projects/{pid}", {"confirm": "Bye"})
            self.assertEqual(st, 200, body)
            self.assertEqual(s.ws.list_projects(), [])
        finally:
            srv.shutdown()
            cleanup(tmp)


class SetupScriptTests(unittest.TestCase):
    def test_detects_and_extracts_zip_layouts(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("setup_asset_packs", ROOT / "scripts" / "setup_asset_packs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = temp_workspace()
        try:
            src = make_fixture_packs(tmp / "src")
            z1 = tmp / "tiny.zip"
            with zipfile.ZipFile(z1, "w") as z:
                for f in (src / "tiny-rpg").rglob("*.png"):
                    z.write(f, "Tiny RPG Pack 01/Characters(100x100 split)/" + f.relative_to(src / "tiny-rpg").as_posix())
                z.writestr("__MACOSX/._junk.png", b"x")
                z.writestr("Tiny RPG Pack 01/Aseprite file/Soldier.aseprite", b"x")
            z2 = tmp / "fx.zip"
            with zipfile.ZipFile(z2, "w") as z:
                for f in (src / "pvfx-foundry").rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(src / "pvfx-foundry").as_posix())
                z.writestr("effects/fire/fireball-impact/lit/packed/sprite-sheet.png", b"x")   # packed sheets are skipped
            dest = tmp / "packs"
            self.assertEqual(mod.install(z1, dest)[0], "tiny-rpg")
            self.assertEqual(mod.install(z2, dest)[0], "pvfx-foundry")
            self.assertTrue((dest / "tiny-rpg" / "Soldier" / "Soldier" / "Soldier_Idle.png").is_file())
            self.assertTrue((dest / "tiny-rpg" / "_aseprite" / "Soldier.aseprite").is_file())
            self.assertFalse(any("__MACOSX" in str(p) for p in dest.rglob("*")))
            self.assertFalse((dest / "pvfx-foundry" / "effects" / "fire" / "fireball-impact" / "lit" / "packed").exists())
            bad = tmp / "bad.zip"
            with zipfile.ZipFile(bad, "w") as z:
                z.writestr("readme.txt", "hi")
            with self.assertRaises(SystemExit):
                mod.install(bad, dest)
        finally:
            cleanup(tmp)


@unittest.skipUnless((REAL / "tiny-rpg").is_dir() or (REAL / "pvfx-foundry").is_dir(), "real asset packs not installed")
class RealPackTests(unittest.TestCase):
    """Runs on the owner's computer once scripts/setup_asset_packs.py has installed the real packs."""

    def setUp(self):
        self.old = os.environ.get("ARTSTUDIO_PACKS_DIR")
        os.environ["ARTSTUDIO_PACKS_DIR"] = str(REAL)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("ARTSTUDIO_PACKS_DIR", None)
        else:
            os.environ["ARTSTUDIO_PACKS_DIR"] = self.old

    def test_real_items_load(self):
        for p in packs.list_packs():
            if not p["available"]:
                continue
            lst = packs.items(p["id"])
            self.assertGreater(len(lst), 0, p["id"])
            for it in lst[:: max(1, len(lst) // 12)]:
                d = packs.load(it)
                self.assertTrue(d["frames"], it["id"])
                self.assertEqual({im.size for im, _ in d["frames"]}, {tuple(d["canvas"])}, it["id"])
        if (REAL / "tiny-rpg").is_dir():
            names = {i["character"]["name"] for i in packs.items("tiny-rpg") if i.get("character")}
            self.assertTrue({"Soldier", "Orc", "Demon A", "Blood Monster A"} <= names)


if __name__ == "__main__":
    unittest.main()
