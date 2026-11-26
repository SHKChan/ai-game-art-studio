"""Skill icons (技能图标), 32×32 square JRPG skill buttons: an element-coloured bevelled frame with an emblem.
One emblem per skill effect in Pixel Forge (lava burn, meteor, earth spike, fire pillar, whirlpool, gale, ice field,
holy judgment, dark vortex, life drain) plus common extras (revive, curse, heal, barrier, haste, slash, thunder,
poison). `element` overrides the frame colour (default: the skill's own element)."""
from __future__ import annotations

import math

from ._icon import OUTLINE, RAMPS, SIZES, Icon, _paint
from .raster import DocBuilder, Grid, bayer4

DESCRIPTION = "Square skill icon (32/48/64 px): lit bevelled element frame + shaded emblem for 18 skills (lava burn, meteor, holy judgment, …)."
ASSET_TYPE = "icon"
FULL_BLEED = True
GROUP = "Skill icons"
SKILLS = {  # skill → default element
    "lava_burn": "fire", "meteor": "fire", "fire_pillar": "fire", "earth_spike": "earth", "whirlpool": "water",
    "gale": "wind", "ice_field": "ice", "holy_judgment": "holy", "revive": "holy", "dark_vortex": "dark",
    "curse": "dark", "life_drain": "blood", "heal": "nature", "barrier": "arcane", "haste": "wind",
    "slash": "physical", "thunder": "lightning", "poison": "poison",
}
ELEMENTS = {  # border dark, border light, bg dark, bg mid, bg glow
    "fire": ["#5a140c", "#ff8a3a", "#2a0a08", "#6a1a10", "#b8401a"],
    "earth": ["#3a2410", "#d0a060", "#1e140c", "#4a3220", "#7a5634"],
    "water": ["#0c2458", "#5ab0ff", "#08122c", "#123a78", "#1e64b0"],
    "wind": ["#0e4436", "#7ae8c0", "#081e1a", "#14483c", "#22806a"],
    "ice": ["#14406a", "#b8f0ff", "#0a1a30", "#1a4a7a", "#3a86c0"],
    "holy": ["#6a4a0c", "#fff0a0", "#2a1e08", "#6a5014", "#b89430"],
    "dark": ["#2a0e44", "#c27aff", "#0e0618", "#2e1450", "#562488"],
    "blood": ["#4a0812", "#ff6a7a", "#1e0408", "#540c1a", "#8e1a2c"],
    "nature": ["#14441a", "#9ae86a", "#0a1e0c", "#18481c", "#2e7a2e"],
    "arcane": ["#1a2a6a", "#9ab8ff", "#0a1030", "#1e2e6a", "#3a54a8"],
    "physical": ["#3a3e4a", "#e4e8f0", "#14161c", "#30343e", "#545a6a"],
    "lightning": ["#5a4a08", "#fff27a", "#1e1a08", "#4a3e0c", "#8a7414"],
    "poison": ["#2a0e44", "#b8ff6a", "#100a18", "#2a1640", "#4a2a6a"],
}
PARAMS = {"skill": {"type": "string", "default": "lava_burn", "enum": list(SKILLS)},
          "element": {"type": "string", "default": "auto", "enum": ["auto"] + list(ELEMENTS)},
          "size": {"type": "int", "default": 48, "enum": SIZES}}


def _frame(element: str, n: int = 32):
    """Bevelled square button: dark outline, 2-step lit/shadowed bevel, inner shadow line, radial element glow."""
    BD, BL, D, M, Gl = ELEMENTS[element]
    k = n / 32.0
    bev = max(2, int(round(2 * k)))
    mid = "#%02x%02x%02x" % tuple((int(BD[i:i + 2], 16) + int(BL[i:i + 2], 16)) // 2 for i in (1, 3, 5))
    g = [[None] * n for _ in range(n)]
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            ex, ey = min(x, n - 1 - x), min(y, n - 1 - y)
            e = min(ex, ey)
            if ex + ey < 1:
                continue
            lit = (x + y) < n - 1 if ex != ey else x < c
            if e == 0:
                g[y][x] = OUTLINE
            elif e <= bev:
                top_left = (y <= x and y < n - 1 - x) or (x < y and x < n - 1 - y)
                top_left = (ey <= ex and y < c) or (ex < ey and x < c)
                g[y][x] = (BL if e == 1 else mid) if top_left else (BD if e == 1 else mid)
            elif e == bev + 1:
                g[y][x] = OUTLINE if (ey <= ex and y < c) or (ex < ey and x < c) else BD
            else:
                q = math.hypot(x - c, y - c - 2 * k) / (n * 0.6)
                g[y][x] = Gl if q < 0.36 + 0.08 * bayer4(x, y) else (M if q < 0.66 + 0.1 * bayer4(x, y) else D)
    return g


def _flame(ic: Icon, x, y, h, w, outer="fire_o", inner="fire_i", lean=0.0):
    pts_l, pts_r = [], []
    for i in range(13):
        v = i / 12
        half = w * math.sin(math.pi * (0.15 + 0.85 * v)) ** 0.6 * (1 - v) ** 0.55 if v < 1 else 0
        cx = x + lean * v * v
        pts_l.append((cx - half, y - h * v)); pts_r.append((cx + half, y - h * v))
    ic.poly(pts_l + pts_r[::-1], outer)
    if inner and h > 5:
        _flame(ic, x + lean * 0.1, y - 0.5, h * 0.55, w * 0.55, inner, None, lean * 0.4)


def _fire_parts(ic, ramp="fire"):
    r = RAMPS[ramp]
    ic.part("fire_o", [r[0], r[1], r[2], r[2]])
    ic.part("fire_i", [r[2], r[3], r[3], r[3]], flat=True)


def _spiral(ic: Icon, cx, cy, R, arms, part, turns=1.4, width=2.4):
    for k in range(arms):
        prev = None
        for i in range(60):
            u = i / 59
            a = 2 * math.pi * (k / arms + u * turns)
            r = R * (1 - u) + 1
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r)
            if prev:
                w = width * (1 - u * 0.6)
                ic.bar(*prev, *p, w, w, part)
            prev = p


def _swirl(x, y, cx, cy, R, arms, twist, base, arm, eye, eye_r=2.4):
    dx, dy = x + .5 - cx, y + .5 - cy
    r = math.hypot(dx, dy)
    if r > R:
        return None
    if r < eye_r:
        return eye
    v = math.sin(arms * math.atan2(dy, dx) + twist * 4 * math.log(r / R + 0.05))
    return arm if v > 0.55 else base


def build(skill: str = "lava_burn", element: str = "auto", size: int = 48, **_):
    if skill not in SKILLS:
        raise ValueError(f"skill must be one of {list(SKILLS)}")
    el = SKILLS[skill] if element == "auto" else element
    ic = Icon(int(size))
    W = "#ffffff"
    if skill == "lava_burn":
        ic.part("lava", "fire")
        ic.ellipse(16, 23, 11, 4.4, "lava")
        ic.part("crust", "stone")
        for x, y in ((9, 23), (21, 24), (15, 25)):
            ic.ellipse(x, y, 1.8, 0.9, "crust")
        _fire_parts(ic)
        for x, h, w in ((10, 11, 3.4), (16, 17, 4.6), (22, 12, 3.6)):
            _flame(ic, x, 23, h, w, lean=1.2 if x > 16 else -1)
        ic.dot(13, 20, RAMPS["fire"][3]); ic.dot(20, 21, RAMPS["fire"][3])
    elif skill == "meteor":
        _fire_parts(ic)
        for k in range(5):                                         # trail toward the top-right
            t = k / 4
            ic.ellipse(14 + 11 * t, 18 - 11 * t, 5.6 - 3.6 * t, 5.6 - 3.6 * t, "fire_o" if t > 0.3 else "fire_i")
        ic.part("rock", "stone")
        ic.ellipse(11.5, 20.5, 5.2, 5.2, "rock")
        ic.dot(10, 19, RAMPS["stone"][0]); ic.dot(13, 22, RAMPS["stone"][0]); ic.dot(12, 18, RAMPS["fire"][2]); ic.dot(9, 22, RAMPS["fire"][2])
        ic.dot(8, 17, RAMPS["stone"][3])
    elif skill == "fire_pillar":
        _fire_parts(ic)
        ic.part("glow", "fire")
        ic.ellipse(16, 25, 9, 3, "glow")
        _flame(ic, 16, 26, 22, 6.4, lean=1.5)
        _flame(ic, 10, 26, 8, 2.6, lean=-1); _flame(ic, 22, 26, 9, 2.6, lean=1)
    elif skill == "earth_spike":
        ic.part("ground", "earth" if "earth" in RAMPS else "leather")
        ic.part("ground", "leather")
        ic.ellipse(16, 25, 12, 3.2, "ground")
        for i, (x, h, w) in enumerate(((10, 12, 4), (17, 20, 5.4), (23, 10, 3.4))):
            ic.part(f"sl{i}", [RAMPS["wood"][2], RAMPS["parchment"][1], RAMPS["parchment"][2], W], flat=True)
            ic.part(f"sr{i}", [RAMPS["wood"][1]] * 4, flat=True)
            ic.poly([(x - w, 25), (x + 0.5, 25 - h), (x, 26)], f"sl{i}")
            ic.poly([(x, 26), (x + 0.5, 25 - h), (x + w, 25)], f"sr{i}")
        for x, y in ((6, 20), (27, 19), (13, 9)):
            ic.dot(x, y, RAMPS["parchment"][1])
    elif skill == "whirlpool":
        ic.part("water", "blue")
        ic.part("foam", ["#5a8ac0", "#c8ecff", "#ffffff", W], flat=True)
        ic.part("eye", "black")
        ic.field(lambda x, y: _swirl(x, y, 16, 17, 11.5, 3, 2.4, "water", "foam", "eye"))
    elif skill == "gale":
        ic.part("funnel", ["#2a7a64", "#8ae8c8", "#d8fff2", W])
        ic.part("band", ["#ffffff"] * 4, flat=True)
        pts_l, pts_r = [], []
        for i in range(12):
            v = i / 11
            cx = 16 + math.sin(v * 3) * 2.2
            r = 2 + 10 * (1 - v) ** 1.3
            y = 5 + 21 * v
            pts_l.append((cx - r, y)); pts_r.append((cx + r, y))
        ic.poly(pts_l + pts_r[::-1], "funnel")
        for k, y in enumerate((8, 13, 18, 22)):
            v = (y - 5) / 21
            cx, r = 16 + math.sin(v * 3) * 2.2, 2 + 10 * (1 - v) ** 1.3
            ic.bar(cx - r * 0.8, y + 1.2, cx + r * 0.7, y - 0.8, 1.2, 1.2, "band")
        ic.part("leaf", "herb")
        ic.ellipse(26, 14, 1.8, 1.2, "leaf"); ic.ellipse(6, 20, 1.6, 1.1, "leaf"); ic.ellipse(24, 24, 1.3, 1.0, "leaf")
    elif skill == "ice_field":
        ic.part("ice", "glass")
        ic.poly([(3, 24), (10, 20), (22, 20), (29, 24), (22, 28), (10, 28)], "ice")
        for i, (x, h, w) in enumerate(((16, 18, 4.4), (10, 11, 3), (22, 12, 3.2))):
            ic.part(f"cl{i}", [RAMPS["mithril"][2]] * 4, flat=True)
            ic.part(f"cr{i}", [RAMPS["mithril"][1]] * 4, flat=True)
            ic.poly([(x - w, 24), (x - w, 24 - h + 3), (x, 24 - h), (x, 25)], f"cl{i}")
            ic.poly([(x, 25), (x, 24 - h), (x + w, 24 - h + 3), (x + w, 24)], f"cr{i}")
        ic.dot(15, 9, W); ic.dot(9, 16, W); ic.dot(21, 15, W)
    elif skill == "holy_judgment":
        ic.part("ray", ["#b8901c", "#ffe27a", "#fff6c8", W], flat=True)
        for k in range(8):
            a = k * math.pi / 4 + math.pi / 8
            ic.bar(16 + math.cos(a) * 6, 16 + math.sin(a) * 6, 16 + math.cos(a) * 12, 16 + math.sin(a) * 12, 2.2, 0.6, "ray")
        ic.part("cross", "gold")
        ic.rect(14, 4, 18, 28, "cross"); ic.rect(7, 11, 25, 15, "cross")
        ic.part("core", "white")
        ic.ellipse(16, 13, 2.2, 2.2, "core")
    elif skill == "revive":
        ic.part("halo", "gold")
        ic.ellipse(16, 8, 7, 2.8, "halo"); ic.ellipse(16, 8.2, 4.6, 1.3, None)
        ic.part("wing", "white")
        for side in (-1, 1):
            for j in range(4):
                ic.poly([(16 + side * 2, 14 + j * 2.5), (16 + side * (8 + 3 * (3 - j) * 0.6), 11 + j * 3.4), (16 + side * (11 - j * 1.6), 16 + j * 3.4), (16 + side * 2, 19 + j * 2)], "wing")
        ic.part("plus", "green")
        ic.rect(15, 15, 17, 25, "plus"); ic.rect(11, 19, 21, 21, "plus")
    elif skill == "dark_vortex":
        ic.part("swirl", "purple")
        ic.part("arm", ["#6a2aa8", "#c27aff", "#ecd0ff", W], flat=True)
        ic.part("void", "black")
        ic.field(lambda x, y: _swirl(x, y, 16, 16, 12, 4, 2.0, "swirl", "arm", "void", 3.6))
        ic.color("eye", "#ff4a8a")
        ic.rect(14, 16, 18, 16, "eye"); ic.dot(16, 15, "#ffd0e0")
    elif skill == "curse":
        ic.part("aura", "purple")
        _flame(ic, 16, 27, 22, 9, "aura", None)
        ic.part("skull", "white")
        ic.ellipse(16, 15, 7, 6.6, "skull")
        ic.rect(12, 19, 20, 23, "skull")
        ic.part("hole", "black")
        ic.ellipse(13, 15.5, 1.9, 2.2, "hole"); ic.ellipse(19, 15.5, 1.9, 2.2, "hole")
        ic.rect(16, 18, 16, 19, "hole")
        for x in (13, 15, 17, 19):
            ic.dot(x, 22, RAMPS["white"][0])
        ic.dot(13, 15, "#d070ff"); ic.dot(19, 15, "#d070ff")
    elif skill == "life_drain":
        ic.part("heart", "ruby")
        ic.ellipse(12, 12, 5, 5, "heart"); ic.ellipse(20, 12, 5, 5, "heart")
        ic.poly([(7, 13.5), (25, 13.5), (16, 24)], "heart")
        ic.part("drip", "red")
        for x, y0 in ((11, 21), (16, 25), (21, 21)):
            ic.ellipse(x, y0 + 3, 1.5, 1.8, "drip")
        ic.part("orb", "red")
        for x, y, r in ((16, 4.5, 1.8), (11, 6, 1.2), (21, 6.4, 1.3)):
            ic.ellipse(x, y, r, r, "orb")
        ic.dot(10, 10, RAMPS["ruby"][3]); ic.dot(11, 9, RAMPS["ruby"][3])
    elif skill == "heal":
        ic.part("plus", "green")
        ic.rect(13, 6, 19, 26, "plus"); ic.rect(6, 13, 26, 19, "plus")
        ic.part("inner", ["#9ae070", "#d8ffb8", "#ffffff", W], flat=True)
        ic.rect(15, 8, 16, 14, "inner"); ic.rect(8, 15, 14, 16, "inner")
        for x, y in ((7, 7), (25, 25), (26, 8)):
            ic.dot(x, y, "#e0ffc0"); ic.dot(x + 1, y, "#9ae070"); ic.dot(x - 1, y, "#9ae070"); ic.dot(x, y + 1, "#9ae070"); ic.dot(x, y - 1, "#9ae070")
    elif skill == "barrier":
        ic.part("hex", "mithril")
        pts = [(16 + math.cos(math.pi / 6 + k * math.pi / 3) * 12, 16 + math.sin(math.pi / 6 + k * math.pi / 3) * 12) for k in range(6)]
        ic.poly(pts, "hex")
        ic.part("hexin", ["#2a5ab8", "#5a9ae8", "#9ad0ff", W])
        ic.poly([(16 + (x - 16) * 0.72, 16 + (y - 16) * 0.72) for x, y in pts], "hexin")
        ic.part("shield", "white")
        ic.poly([(11, 10), (21, 10), (21, 17), (16, 23), (11, 17)], "shield")
    elif skill == "haste":
        ic.part("chev", ["#1a6a52", "#5ad8a8", "#b8ffe4", W])
        for i in range(3):
            x = 8 + i * 6
            ic.poly([(x, 7), (x + 5, 7), (x + 11, 16), (x + 5, 25), (x, 25), (x + 6, 16)], "chev")
    elif skill == "slash":
        ic.part("arc", ["#5a6a8a", "#c4d4f0", "#ffffff", W])
        prev = None
        for i in range(24):
            u = i / 23
            a = math.radians(200 + 130 * u)
            p = (16 + math.cos(a) * 12 + 2, 20 + math.sin(a) * 12)
            if prev:
                w = 0.6 + 5 * math.sin(math.pi * u)
                ic.bar(*prev, *p, w, w, "arc")
            prev = p
        ic.part("arc2", "white")
        ic.bar(8, 22, 24, 6, 1.2, 0.4, "arc2")
    elif skill == "thunder":
        ic.part("bolt", "topaz")
        ic.poly([(18, 3), (9, 17), (15, 17), (11, 29), (24, 12), (17, 12), (22, 3)], "bolt")
        ic.part("boltc", ["#fff6c0", "#fffbe0", "#ffffff", W], flat=True)
        ic.line(19, 5, 13, 15, "boltc")
    elif skill == "poison":
        ic.part("bubble", "green")
        ic.ellipse(16, 18, 9, 9, "bubble")
        ic.ellipse(24, 8, 3, 3, "bubble"); ic.ellipse(8, 9, 2, 2, "bubble")
        ic.part("skull", "white")
        ic.ellipse(16, 17, 4.6, 4.2, "skull"); ic.rect(14, 20, 18, 22, "skull")
        ic.part("hole", "black")
        ic.ellipse(14.2, 17, 1.3, 1.4, "hole"); ic.ellipse(17.8, 17, 1.3, 1.4, "hole")
        ic.dot(12, 13, "#e8ffc0"); ic.dot(23, 7, "#e8ffc0")
    art = ic.shade()
    n = ic.n
    shine = [[None] * n for _ in range(n)]
    for x, y, c in ic.extra:
        if 0 <= x < n and 0 <= y < n:
            shine[y][x] = c
    fr = _frame(el, n)
    cols = []
    for g in (fr, art, shine):
        for row in g:
            for c in row:
                if c is not None and c not in cols:
                    cols.append(c)
    idx = {c: i for i, c in enumerate(cols)}
    d = DocBuilder(f"skill-icon-{skill.replace('_', '-')}", n, n)
    d.palette(cols)
    for name, g in (("frame", fr), ("emblem", art), ("shine", shine)):
        _paint(d, d.layer(name), g, idx, n)
    return d.calls
