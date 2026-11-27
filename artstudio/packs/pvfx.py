"""PVFX Foundry 1.2 (CC0): 253 pixel-art effects — spells, skills, hits, status auras, projectiles, ambient loops, UI.

Layout after setup:  <root>/pack.json, <root>/effects/<category>/<effect>/[variants/<v>/]<tier>/grid/{sprite-sheet.png,manifest.json}
The importer reads the grid manifests (exact cell rects, per-frame durations, pivot) and keeps soft alpha for the
``lit`` tier. pack.json tags are kept and extended with the studio's skill / spell vocabulary."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ID = "pvfx-foundry"
DIRNAME = "pvfx-foundry"
TITLE = "PVFX Foundry effects"
DESCRIPTION = "253 pixel effects: elemental spells, melee skills, hits, explosions, status auras, projectiles, ambient loops, UI feedback."
LICENSE_NOTE = "CC0 1.0 (sprite sheets, manifests and pack.json) — free to use, modify and redistribute."
REDISTRIBUTABLE = True
OPTIONS = {"tier": {"type": "string", "enum": ["lit", "strict"], "default": "lit", "label": "Style tier"},
           "variants": {"type": "boolean", "default": False, "label": "Include colour variants"}}

MAGIC = {"fire", "ice", "lightning", "holy", "shadow", "arcane", "nature", "water", "wind"}
# category → extra studio tags (skill / spell vocabulary shared with the Pixel Forge builders)
CATEGORY_TAGS = {
    "fire": ["fire"], "ice": ["ice", "frost"], "lightning": ["lightning", "electric", "thunder"], "holy": ["holy", "light"],
    "shadow": ["shadow", "dark"], "arcane": ["arcane"], "nature": ["nature", "earth"], "water": ["water"], "wind": ["wind", "air"],
    "melee": ["skill", "melee", "physical", "attack"], "impacts": ["hit", "impact"], "explosions": ["explosion", "aoe"],
    "projectiles": ["projectile"], "status": ["status"], "smoke": ["smoke"], "ambient": ["ambient", "scenery", "environment"],
    "scifi": ["scifi"], "ui": ["ui", "feedback"],
}
DROP = {"flagship"}
SYNONYMS = {"heal": ["support", "restore"], "buff": ["support"], "debuff": ["control"], "cast": ["skill", "spell"],
            "dark": ["shadow"], "poison": ["toxic"], "explosion": ["aoe"], "shockwave": ["aoe"], "beam": ["attack"],
            "slash": ["skill", "melee"], "projectile": ["attack"]}


def available(root: Path) -> bool:
    return (root / "pack.json").is_file() and (root / "effects").is_dir()


def _tags(e: dict) -> list[str]:
    cat = e["category"]
    tags = [t for t in e.get("tags", []) if t not in DROP] + [cat] + CATEGORY_TAGS.get(cat, [])
    if cat in MAGIC:
        tags += ["skill", "spell", "magic"]
    for t in list(tags):
        tags += SYNONYMS.get(t, [])
    tags += ["effect", "vfx", "pvfx", "pixel-art"] + (["loop"] if e.get("loop") else ["one-shot"])
    return tags


def items(root: Path, options: dict) -> list[dict]:
    pack = json.loads((root / "pack.json").read_text(encoding="utf-8"))
    tier = options.get("tier", "lit")
    out = []
    for e in pack["effects"]:
        cat = e["category"]
        group = "UI" if cat == "ui" else ("Scenery" if cat == "ambient" else ("Spells" if cat in MAGIC else "Effects"))
        typ = "ui" if cat == "ui" else "effect"
        tiers = [tier] + [t for t in ("lit", "strict") if t != tier]
        art = next((e["artifacts"][t]["grid"] for t in tiers if (root / e["artifacts"][t]["grid"]["manifest"]).is_file()), None)
        if art is None:
            continue
        base = {"type": typ, "group": group, "frames": e["frames"], "description": e.get("description", ""),
                "loop": bool(e.get("loop")), "size": e.get("size")}
        out.append({**base, "id": e["id"], "name": e["name"], "tags": _tags(e), "manifest": art["manifest"]})
        if options.get("variants"):
            for vname, v in (e.get("variants") or {}).items():
                va = next((v["artifacts"][t]["grid"] for t in tiers if (root / v["artifacts"][t]["grid"]["manifest"]).is_file()), None)
                if va:
                    out.append({**base, "id": f"{e['id']}@{vname}", "name": f"{e['name']} ({vname})",
                                "tags": _tags(e) + [vname, "colour-variant"], "manifest": va["manifest"]})
    return out


def load(item: dict, root: Path, options: dict) -> dict:
    mpath = root / item["manifest"]
    man = json.loads(mpath.read_text(encoding="utf-8"))
    sheet_path = mpath.parent / man["frames"][0]["sheet"]["image"]
    with Image.open(sheet_path) as im:
        sheet = im.convert("RGBA")
    w, h = man["source_size"]
    frames, rects = [], []
    for f in man["frames"]:
        s = f["sheet"]
        d = f["duration"]
        r = [s["x"], s["y"], s["width"], s["height"]]
        frames.append((sheet.crop((r[0], r[1], r[0] + r[2], r[1] + r[3])), max(1, round(d["numerator_ms"] / d.get("denominator", 1)))))
        rects.append(r)
    piv = list(man.get("pivot") or [w // 2, h - 1])
    clamped = [min(max(piv[0], 0), w - 1), min(max(piv[1], 0), h - 1)]   # a few effects pivot just outside their cell
    return {"frames": frames, "canvas": [w, h], "pivot": clamped,
            "loop": man.get("loop_mode", "none") != "none" or item.get("loop", False), "source_file": sheet_path,
            "source_rects": rects, "binary_alpha": man.get("tier") == "strict",
            "extra": {"vfx": {"pack": "pvfx-foundry", "effect": item["id"], "tier": man.get("tier"), "pivot": piv,
                              "description": item.get("description", "")}}}
