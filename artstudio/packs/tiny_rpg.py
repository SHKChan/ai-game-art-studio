"""Tiny RPG Character Asset Pack 01/02 (Zerie, free versions): Soldier, Orc, Demon_A, Blood Monster_A.

Layout after setup:  <root>/<Character>/<Character>[ with shadows]/<Character>_<Action>.png
Each action is a horizontal strip of 100×100 cells, side view facing right. All actions of one character share the
same cell coordinates, so the importer keeps the cells as they are (canvas 100×100, one pivot at the feet)."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

ID = "tiny-rpg"
DIRNAME = "tiny-rpg"
TITLE = "Tiny RPG Characters"
DESCRIPTION = "Soldier, Orc, Demon and Blood Monster — side-view 100×100 action strips (idle, walk, attacks, hurt, death)."
LICENSE_NOTE = "Zerie, Tiny RPG Character Asset Pack (free). Use in your games; do not redistribute the art."
REDISTRIBUTABLE = False
OPTIONS = {"shadows": {"type": "boolean", "default": True, "label": "Include drop shadows"}}

CELL = 100
FRAME_MS = 100

# folder name → character record + search tags
CHARACTERS = {
    "Soldier": {"name": "Soldier", "tags": ["character", "hero", "human", "humanoid", "soldier", "knight", "melee", "sword",
                                             "bow", "archer", "ranged", "armor", "helmet"],
                "description": "Helmeted soldier with sword and bow (Tiny RPG)."},
    "Orc": {"name": "Orc", "tags": ["monster", "enemy", "orc", "goblin", "greenskin", "humanoid", "melee", "axe", "dungeon"],
            "description": "Green orc with an axe (Tiny RPG)."},
    "Demon_A": {"name": "Demon A", "tags": ["monster", "enemy", "demon", "fiend", "horned", "melee", "blade", "dungeon", "hell"],
                "description": "Horned red demon with a curved blade (Tiny RPG)."},
    "Blood Monster_A": {"name": "Blood Monster A", "tags": ["monster", "enemy", "blood", "flesh", "beast", "creature", "melee",
                                                            "claw", "dungeon"],
                        "description": "Crimson blood beast with claws (Tiny RPG)."},
}
ACTION_TAGS = {"idle": ["idle", "loop"], "walk": ["walk", "move", "loop"], "hurt": ["hurt", "hit", "damage"],
               "death": ["death", "die", "ko"], "attack01": ["attack", "melee"], "attack02": ["attack", "melee"],
               "attack03": ["attack"]}
# per-character extras for actions that differ (the soldier's third attack is a bow shot)
SPECIAL = {("Soldier", "attack03"): ["bow", "ranged", "shoot"], ("Soldier", "attack01"): ["sword", "slash"],
           ("Soldier", "attack02"): ["sword", "slash"], ("Orc", "attack01"): ["axe", "slash"], ("Orc", "attack02"): ["axe", "slash"],
           ("Demon_A", "attack02"): ["claw", "slash"], ("Blood Monster_A", "attack02"): ["claw", "dash"]}
LOOPING = {"idle", "walk"}
_ACT = re.compile(r"^(?P<char>.+)_(?P<act>Idle|Walk|Hurt|Death|Attack\d\d)\.png$")


def _char_dir(root: Path, folder: str, shadows: bool) -> Path | None:
    base = root / folder
    for d in ([base / f"{folder} with shadows"] if shadows else []) + [base / folder]:
        if d.is_dir():
            return d
    return None


def available(root: Path) -> bool:
    return root.is_dir() and any(_char_dir(root, f, False) for f in CHARACTERS)


def char_slug(folder: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-")


def items(root: Path, options: dict) -> list[dict]:
    out = []
    for folder, info in CHARACTERS.items():
        d = _char_dir(root, folder, options.get("shadows", True))
        if not d:
            continue
        for f in sorted(d.glob("*.png")):
            m = _ACT.match(f.name)
            if not m or m["char"] != folder:
                continue              # skip the combined <Character>.png overview sheet
            act = m["act"].lower()
            with Image.open(f) as im:
                n = im.width // CELL
            group = "Characters" if "hero" in info["tags"] else "Monsters"
            tags = info["tags"] + ACTION_TAGS.get(act, []) + SPECIAL.get((folder, act), []) + \
                ["action:" + act, "side-view", "tiny-rpg", "pixel-art", "100px"] + (["shadow"] if "with shadows" in d.name else [])
            out.append({"id": f"{char_slug(folder)}/{act}", "name": f"{info['name']} · {m['act']}", "type": "animation",
                        "group": group, "tags": tags, "frames": n, "action": act, "direction": "right",
                        "character": {"key": char_slug(folder), "name": info["name"], "description": info["description"],
                                      "tags": info["tags"]},
                        "file": str(f.relative_to(root).as_posix())})
        arrow = root / folder / "Arrow(projectile)" / "Arrow01(100x100).png"
        if arrow.is_file():
            out.append({"id": f"{char_slug(folder)}/arrow", "name": f"{info['name']} · Arrow", "type": "effect", "group": "Effects",
                        "tags": ["projectile", "arrow", "bow", "ranged", "effect", "tiny-rpg", "side-view"], "frames": 1,
                        "file": str(arrow.relative_to(root).as_posix())})
    return out


def _feet(root: Path, item: dict) -> list[int]:
    """Pivot = bottom centre of the character in its first idle frame (no shadow), same for every action."""
    from ..processing.frames import alpha_bbox
    folder = next(f for f in CHARACTERS if char_slug(f) == item["character"]["key"])
    src = _char_dir(root, folder, False) / f"{folder}_Idle.png"
    if not src.is_file():
        return [CELL // 2, CELL - 1]
    with Image.open(src) as im:
        b = alpha_bbox(im.convert("RGBA").crop((0, 0, CELL, CELL)), 128)
    return [round((b[0] + b[2]) / 2), b[3]] if b else [CELL // 2, CELL - 1]


def load(item: dict, root: Path, options: dict) -> dict:
    path = root / item["file"]
    with Image.open(path) as im:
        sheet = im.convert("RGBA")
    if item["type"] == "effect":
        return {"frames": [(sheet, FRAME_MS)], "canvas": list(sheet.size), "pivot": [sheet.width // 2, sheet.height // 2],
                "loop": False, "source_file": path}
    n = sheet.width // CELL
    frames = [(sheet.crop((i * CELL, 0, (i + 1) * CELL, CELL)), FRAME_MS) for i in range(n)]
    act = item["action"]
    return {"frames": frames, "canvas": [CELL, CELL], "pivot": _feet(root, item), "loop": act in LOOPING,
            "hold_last": act == "death", "source_file": path, "anim_name": act, "direction": "right",
            "source_rects": [[i * CELL, 0, CELL, CELL] for i in range(n)]}
