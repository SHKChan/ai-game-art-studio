"""Dress the Craftpix base frame by frame: recoloured clothes, hair, headgear, armour pieces and a re-shaped weapon.
Every frame uses that frame's own body / head / sword layers, so the costume follows the animation.

Draw order (back → front), grouped into five editable layers:
    shadow | back: cape, back hair, far-side weapon | body | gear: armour/robe, head, front hair, headgear,
    back-view cape | front: near-side weapon (over the face), swing trail | flash: the pack's red hurt tint
A right-handed character facing right holds the weapon on the near side (pack layer sword_front, drawn over the
head); facing left the weapon is on the far side (sword_back, behind the body)."""
from __future__ import annotations

from PIL import Image

from . import doll, equip, skeleton
from .base import CELL, DIRS, layer_sheets

GROUPS = ["shadow", "back", "body", "gear", "front", "flash"]


def blank():
    return Image.new("RGBA", (CELL, CELL))


def render_pieces(pieces):
    im = blank()
    for pts, ramp, kw in pieces:
        equip.paint(im, pts, ramp, **dict(kw))
    return im


def stack(*layers):
    im = blank()
    for layer in layers:
        if layer is not None:
            im.alpha_composite(layer)
    return im


def flatten(groups: dict) -> Image.Image:
    return stack(*(groups.get(g) for g in GROUPS))


def _cells(L, r):
    c = 0
    while c * CELL < L["body"].width:
        box = (c * CELL, r * CELL, c * CELL + CELL, r * CELL + CELL)
        cell = {k: v.crop(box) for k, v in L.items()}
        if cell["body"].getbbox() is None and cell["head"].getbbox() is None:
            return
        yield c, cell
        c += 1


def _lying(body: Image.Image) -> bool:
    """Death frames: the body lies on the ground (much wider than tall) — no cape or long hair there, and a staff
    falls flat (drawn along the dropped sword instead of upright)."""
    bb = body.getbbox()
    return bool(bb) and (bb[3] - bb[1]) * 1.6 < (bb[2] - bb[0])


def compose_base(sex: str, act: str, dirs=None) -> dict:
    """The unmodified base character, with the near-side weapon over the head."""
    L = layer_sheets(sex, act)
    out = {}
    for r, dirn in enumerate(DIRS):
        if dirs and dirn not in dirs:
            continue
        out[dirn] = [{"shadow": cell.get("shadow"), "back": cell.get("sword_back"), "body": cell["body"],
                      "gear": cell["head"], "front": stack(cell.get("sword_front"), cell.get("swing")), "flash": cell.get("red")}
                     for _, cell in _cells(L, r)]
    return out


def compose(sex: str, act: str, outfit: dict | None, dirs=None) -> dict:
    """{direction: [ {group: image} per frame ]}. outfit None → the plain base."""
    if not outfit:
        return compose_base(sex, act, dirs)
    L = layer_sheets(sex, act)
    rank = doll.skin_rank(L["body"])
    out = {}
    for r, dirn in enumerate(DIRS):
        if dirs and dirn not in dirs:
            continue
        fr = []
        for c, cell in _cells(L, r):
            lying = _lying(cell["body"])
            o = dict(outfit)
            if lying and (o.get("hair") or ("short",))[0] in ("long", "ponytail"):
                o["hair"] = ("short", o["hair"][1])
            body = doll.recolor_body(cell["body"], rank, o, dirn)
            head = cell["head"]
            if o.get("skeleton"):
                body = skeleton.bone_body(body, cell["body"], dirn, cell["head"])
                head = skeleton.skull(head, dirn, o.get("magic", "necro"))
            elif o.get("eyes"):
                head = skeleton.glowing_eyes(head, o["eyes"])
            if o.get("face_shadow"):
                head = skeleton.shadow_face(head)
            if "hair" in o and not o["hair"]:
                hair_f, hair_b = blank(), blank()
            else:
                hair_f, hair_b = doll.hair_layers(cell["head"], o, dirn, True)
            hi, bi = equip.head_info(cell["head"]), equip.body_info(cell["body"])
            under, over, top = equip.body_pieces(bi, {k: v for k, v in o.items() if not (lying and k == "cape")}, dirn, c)
            hg = []
            heads = o.get("head")
            for hs in (heads if isinstance(heads, (list, tuple)) else [heads]):
                if hs:
                    hg += equip.headgear(hi, hs, dirn, o.get("head_ramp", "steel"), o.get("accent", "gold"))
            sf = cell["sword_front"] if cell.get("sword_front") is not None else blank()
            sb = cell["sword_back"] if cell.get("sword_back") is not None else blank()
            swing = cell.get("swing") if not o.get("stiff") else None    # no speed trail on slow undead swings
            w = o.get("weapon")
            if w == "none":
                sf, sb, swing = blank(), blank(), None
            elif w == "axe":
                sf, sb = doll.axe_from_sword(sf, sb, body)
            elif isinstance(w, (tuple, list)) and w[0] == "staff" and lying:
                sf, sb = doll.recolor_weapon(sf, {"weapon": w[1]}), doll.recolor_weapon(sb, {"weapon": w[1]})
                swing = None
            elif isinstance(w, (tuple, list)) and w[0] == "staff":
                sf, sb = equip.staff_from_sword(sf, sb, body, wood=w[1], orb=w[2], head=w[3])
                swing = None
            else:
                sf, sb = doll.recolor_weapon(sf, o), doll.recolor_weapon(sb, o)
            sh_front = sh_back = None
            if o.get("shield") and not lying:
                from .bow import hands
                off = hands(cell["body"], dirn)[0]                   # the left (off) hand
                sh = skeleton.shield(off, dirn, *o["shield"]) if isinstance(o["shield"], (list, tuple)) else \
                    skeleton.shield(off, dirn)
                if dirn in ("front", "side_left"):
                    sh_front = sh
                else:
                    sh_back = sh
            fr.append({"shadow": cell.get("shadow"),
                       "back": stack(render_pieces(under), hair_b, sb, sh_back),
                       "body": body,
                       "gear": stack(render_pieces(over), head, hair_f, render_pieces(hg),
                                     render_pieces(top)),
                       "front": stack(sh_front, sf, swing), "flash": cell.get("red")})
        out[dirn] = fr
    return out
