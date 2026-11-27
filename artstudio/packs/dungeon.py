"""Craftpix "Free 2D Top-Down Pixel Dungeon Asset Pack": 16 px tilesets, animated props and a sample Tiled map.

Layout after setup:  <root>/PNG/*.png, <root>/Tiled_files/{Dungeon1.tmx,*.png}, <root>/license.txt
Tilesets are imported whole (exact pixels, tile grid recorded on the asset); animated props are cut from their sheets
at fixed cells; the sample map is rendered from the .tmx with its tile animations."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from functools import reduce
from pathlib import Path

from PIL import Image

ID = "craftpix-dungeon"
DIRNAME = "craftpix-dungeon"
TITLE = "Pixel Dungeon (top-down)"
DESCRIPTION = "16 px dungeon walls/floor/water tilesets, torches, doors, chests, lever, spike trap and a sample map."
LICENSE_NOTE = "Craftpix.net free licence: use in your games; do not redistribute or resell the art."
REDISTRIBUTABLE = False
OPTIONS: dict = {}
TILE = 16
BASE = ["dungeon", "top-down", "pixel-art", "craftpix", "16px"]

TILESETS = [
    ("walls_floor", "Dungeon walls & floor", ["tileset", "wall", "floor", "stone", "brick", "autotile"]),
    ("decorative_cracks_walls", "Wall cracks", ["tileset", "wall", "crack", "decoration", "damaged"]),
    ("decorative_cracks_floor", "Floor cracks", ["tileset", "floor", "crack", "decoration", "damaged"]),
    ("Water_coasts_animation", "Water & coasts", ["tileset", "water", "coast", "pool", "liquid", "animated-tiles"]),
    ("decorative_cracks_coasts_animation", "Coast cracks", ["tileset", "water", "coast", "crack", "decoration", "animated-tiles"]),
    ("water_detilazation_v2", "Water details", ["tileset", "water", "ripple", "decoration", "animated-tiles"]),
    ("Objects", "Dungeon props", ["tileset", "props", "prop", "crate", "barrel", "chest", "ladder", "stairs", "key", "gold",
                                  "treasure", "vase", "shield", "furniture"]),
    ("trap_animation", "Spike trap tiles", ["tileset", "trap", "spikes", "hazard", "animated-tiles"]),
]

# (id, name, sheet, x, y, w, h, frames, dx, dy, ms, loop, hold_last, ping_pong, tags)  — frames step by (dx, dy)
PROPS = [
    ("candle-flame", "Candle flame", "fire_animation", 0, 0, 32, 48, 6, 0, 48, 150, True, False, False, ["candle", "fire", "light"]),
    ("torch", "Torch", "fire_animation", 32, 0, 48, 48, 6, 0, 48, 150, True, False, False, ["torch", "fire", "light"]),
    ("brazier-large", "Large brazier", "fire_animation", 80, 0, 48, 48, 6, 0, 48, 150, True, False, False, ["brazier", "fire", "light", "campfire"]),
    ("brazier", "Brazier", "fire_animation", 128, 0, 48, 48, 6, 0, 48, 150, True, False, False, ["brazier", "fire", "light"]),
    ("candles-three", "Candles (three)", "fire_animation2", 0, 0, 32, 32, 6, 0, 32, 150, True, False, False, ["candle", "fire", "light"]),
    ("candles-two", "Candles (two)", "fire_animation2", 32, 0, 32, 32, 6, 0, 32, 150, True, False, False, ["candle", "fire", "light"]),
    ("candle", "Candle", "fire_animation2", 64, 0, 32, 32, 6, 0, 32, 150, True, False, False, ["candle", "fire", "light"]),
    ("iron-gate", "Iron gate (opening)", "doors_lever_chest_animation", 0, 0, 32, 32, 5, 32, 0, 120, False, True, False, ["door", "gate", "iron", "bars", "open"]),
    ("wooden-door", "Wooden door (opening)", "doors_lever_chest_animation", 0, 32, 32, 32, 5, 32, 0, 120, False, True, False, ["door", "wood", "open"]),
    ("iron-gate-dark", "Iron gate, dark (opening)", "doors_lever_chest_animation", 0, 64, 32, 32, 5, 32, 0, 120, False, True, False, ["door", "gate", "iron", "bars", "open", "dark"]),
    ("wooden-door-dark", "Wooden door, dark (opening)", "doors_lever_chest_animation", 0, 96, 32, 32, 5, 32, 0, 120, False, True, False, ["door", "wood", "open", "dark"]),
    ("chest-open", "Treasure chest (opening)", "doors_lever_chest_animation", 0, 128, 32, 32, 5, 32, 0, 120, False, True, False, ["chest", "treasure", "gold", "loot", "open", "container"]),
    ("chest-small", "Small chest", "doors_lever_chest_animation", 0, 160, 32, 16, 5, 32, 0, 120, False, True, False, ["chest", "loot", "container"]),
    ("lever", "Lever", "doors_lever_chest_animation", 0, 176, 16, 16, 5, 16, 0, 100, False, True, False, ["lever", "switch", "puzzle", "interactive"]),
    ("spike-trap", "Spike trap", "trap_animation", 96, 48, 16, 32, 5, 0, 80, 120, True, False, True, ["trap", "spikes", "hazard"]),
]


def available(root: Path) -> bool:
    return (root / "PNG" / "walls_floor.png").is_file()


def items(root: Path, options: dict) -> list[dict]:
    out = []
    for key, name, tags in TILESETS:
        f = root / "PNG" / f"{key}.png"
        if f.is_file():
            out.append({"id": f"tileset/{key.lower()}", "name": name, "type": "tileset", "group": "Scenery",
                        "tags": BASE + ["scenery", "environment"] + tags, "frames": 1, "file": f"PNG/{key}.png"})
    for p in PROPS:
        if (root / "PNG" / f"{p[2]}.png").is_file():
            out.append({"id": f"prop/{p[0]}", "name": p[1], "type": "environment", "group": "Scenery",
                        "tags": BASE + ["scenery", "prop", "animated"] + (["loop"] if p[11] else []) + p[14], "frames": p[7],
                        "file": f"PNG/{p[2]}.png"})
    if (root / "Tiled_files" / "Dungeon1.tmx").is_file():
        out.append({"id": "scene/dungeon1", "name": "Dungeon sample map", "type": "environment", "group": "Scenery",
                    "tags": BASE + ["scene", "scenery", "environment", "map", "level", "room", "water", "pool", "torch",
                                    "animated", "loop", "tiled"], "frames": None, "file": "Tiled_files/Dungeon1.tmx"})
    return out


def _sheet(root: Path, name: str) -> Image.Image:
    with Image.open(root / "PNG" / f"{name}.png") as im:
        return im.convert("RGBA")


def load(item: dict, root: Path, options: dict) -> dict:
    kind, key = item["id"].split("/", 1)
    if kind == "tileset":
        src = root / item["file"]
        with Image.open(src) as im:
            sheet = im.convert("RGBA")
        w, h = sheet.size
        return {"frames": [(sheet, 100)], "canvas": [w, h], "pivot": [0, 0], "loop": False, "source_file": src, "full_bleed": True,
                "extra": {"tileset": {"tile_width": TILE, "tile_height": TILE, "columns": w // TILE, "rows": h // TILE,
                                      "source": item["file"]}}}
    if kind == "prop":
        p = next(x for x in PROPS if x[0] == key)
        _, _, sheet_name, x, y, w, h, n, dx, dy, ms, loop, hold, ping, _ = p
        sheet = _sheet(root, sheet_name)
        rects = [[x + i * dx, y + i * dy, w, h] for i in range(n)]
        frames = [(sheet.crop((r[0], r[1], r[0] + w, r[1] + h)), ms) for r in rects]
        return {"frames": frames, "canvas": [w, h], "pivot": [w // 2, h - 1], "loop": loop, "hold_last": hold, "ping_pong": ping,
                "source_file": root / item["file"], "source_rects": rects}
    if kind == "scene":
        frames, ms = render_tmx(root / item["file"])
        w, h = frames[0].size
        return {"frames": [(f, ms) for f in frames], "canvas": [w, h], "pivot": [0, 0], "loop": True, "full_bleed": True,
                "source_file": root / item["file"]}
    raise ValueError(item["id"])


# ---------------------------------------------------------------- Tiled map renderer (orthogonal, CSV, infinite chunks)
FLIP_H, FLIP_V, FLIP_D = 0x80000000, 0x40000000, 0x20000000


def render_tmx(path: Path, max_frames: int = 48) -> tuple[list[Image.Image], int]:
    """Render every visible tile layer of a Tiled map, animating animated tiles. Returns (frames, frame_ms)."""
    root = ET.parse(path).getroot()
    tw, th = int(root.get("tilewidth")), int(root.get("tileheight"))
    sets = []
    for ts in root.findall("tileset"):
        img = ts.find("image")
        with Image.open(path.parent / img.get("source")) as im:
            sheet = im.convert("RGBA")
        anims = {int(t.get("id")): [(int(f.get("tileid")), int(f.get("duration"))) for f in t.find("animation")]
                 for t in ts.findall("tile") if t.find("animation") is not None}
        sets.append({"first": int(ts.get("firstgid")), "cols": int(ts.get("columns")), "sheet": sheet, "anims": anims, "cache": {}})
    sets.sort(key=lambda s: s["first"])
    layers = []
    for lay in root.findall("layer"):
        if lay.get("visible") == "0":
            continue
        cells = {}
        data = lay.find("data")
        for ch in (data.findall("chunk") or [data]):
            cx, cy, cw = int(ch.get("x", 0)), int(ch.get("y", 0)), int(ch.get("width", lay.get("width")))
            vals = [int(v) for v in ch.text.replace("\n", "").split(",") if v.strip()]
            for i, g in enumerate(vals):
                if g:
                    cells[(cx + i % cw, cy + i // cw)] = g
        layers.append((float(lay.get("opacity", 1)), cells))
    pts = [p for _, c in layers for p in c]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts) + 1, max(p[1] for p in pts) + 1
    durs = [d for s in sets for a in s["anims"].values() for _, d in a]
    totals = [sum(d for _, d in a) for s in sets for a in s["anims"].values()]
    step = reduce(math.gcd, durs) if durs else 100
    period = reduce(lambda a, b: a * b // math.gcd(a, b), totals, step) if totals else step
    n = max(1, min(max_frames, period // step))

    def tile(gid: int, t: int) -> Image.Image | None:
        flags, g = gid & 0xE0000000, gid & 0x1FFFFFFF
        s = next((s for s in reversed(sets) if g >= s["first"]), None)
        if s is None:
            return None
        lid = g - s["first"]
        if lid in s["anims"]:
            seq = s["anims"][lid]
            tt = t % sum(d for _, d in seq)
            for tid, d in seq:
                if tt < d:
                    lid = tid
                    break
                tt -= d
        key = (lid, flags)
        if key not in s["cache"]:
            c, r = lid % s["cols"], lid // s["cols"]
            im = s["sheet"].crop((c * tw, r * th, (c + 1) * tw, (r + 1) * th))
            if flags & FLIP_D:
                im = im.transpose(Image.Transpose.TRANSPOSE)
            if flags & FLIP_H:
                im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flags & FLIP_V:
                im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            s["cache"][key] = im
        return s["cache"][key]

    frames = []
    for k in range(n):
        canvas = Image.new("RGBA", ((x1 - x0) * tw, (y1 - y0) * th), (0, 0, 0, 0))
        for opacity, cells in layers:
            lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            for (x, y), g in cells.items():
                im = tile(g, k * step)
                if im is not None:
                    lay.alpha_composite(im, ((x - x0) * tw, (y - y0) * th))
            if opacity < 1:
                a = lay.getchannel("A").point(lambda v: round(v * opacity))
                lay.putalpha(a)
            canvas.alpha_composite(lay)
        frames.append(canvas)
    return frames, step
