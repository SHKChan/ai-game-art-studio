"""UI / menu icons (菜单功能图标) at 32 / 48 / 64 px with the shaded icon renderer: bag, equipment, skills, map, quest,
shop, settings, save, home, mail, battle, auto, speed, confirm, close, back, gold, gem, stamina and a pointing-hand
cursor. `style` = color, or mono (white, for putting on buttons)."""
from __future__ import annotations

import math

from ._icon import RAMPS, SIZES, Icon, emit, ramp5, sparkle

DESCRIPTION = "JRPG menu icon (32/48/64 px): bag, equipment, skills, map, quest, shop, settings, save, gold, gem, cursor … colour or white."
ASSET_TYPE = "icon"
GROUP = "UI"
KINDS = ["bag", "equipment", "skills", "map", "quest", "shop", "settings", "save", "home", "mail", "battle", "auto",
         "speed", "confirm", "close", "back", "gold", "gem", "stamina", "cursor"]
PARAMS = {"kind": {"type": "string", "default": "bag", "enum": KINDS},
          "style": {"type": "string", "default": "color", "enum": ["color", "mono"]},
          "size": {"type": "int", "default": 32, "enum": SIZES}}


def _arc(ic, cx, cy, r, a0, a1, w, part, steps=24):
    prev = None
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        p = (cx + r * math.cos(a), cy + r * math.sin(a))
        if prev:
            ic.bar(*prev, *p, w, w, part)
        prev = p
    return prev


def build(kind: str = "bag", style: str = "color", size: int = 32, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    ic = Icon(int(size))
    W = "#ffffff"
    if kind == "bag":
        ic.part("bag", "leather", style="soft")
        ic.poly([(7, 13), (10, 9), (22, 9), (25, 13), (26, 27), (24, 29), (8, 29), (6, 27)], "bag")
        ic.part("flap", "wood", style="soft")
        ic.poly([(8, 10), (24, 10), (25, 18), (16, 21), (7, 18)], "flap")
        ic.part("strap", "darkwood", style="soft")
        ic.rect(12, 4, 20, 6, "strap"); ic.rect(11, 5, 12, 10, "strap"); ic.rect(20, 5, 21, 10, "strap")
        ic.part("buckle", "gold")
        ic.rect(14.5, 17, 17.5, 21, "buckle")
        ic.part("pocket", "leather", style="soft")
        ic.rect(10, 23, 22, 27, "pocket")
    elif kind == "equipment":
        ic.part("plate", "steel")
        ic.poly([(9, 7), (23, 7), (25, 13), (23, 22), (21, 27), (11, 27), (9, 22), (7, 13)], "plate")
        ic.color("void", "#0e0a14"); ic.ellipse(16, 6.6, 4.2, 2.4, "void")
        ic.part("pad", "bronze")
        ic.ellipse(7.4, 10.6, 4.2, 3.8, "pad"); ic.ellipse(24.6, 10.6, 4.2, 3.8, "pad")
        ic.part("belt", "leather", style="soft"); ic.rect(9, 21, 23, 23, "belt")
        ic.part("gem", "ruby"); ic.ellipse(16, 14, 1.8, 1.8, "gem")
    elif kind == "skills":
        ic.part("cover", "purple", style="soft")
        ic.poly([(3, 14), (16, 18), (29, 14), (29, 27), (16, 30), (3, 27)], "cover")
        ic.part("pageL", "parchment", style="soft"); ic.part("pageR", "parchment", style="soft")
        ic.poly([(5, 12), (15.5, 15.5), (15.5, 27), (5, 24)], "pageL")
        ic.poly([(16.5, 15.5), (27, 12), (27, 24), (16.5, 27)], "pageR")
        P = ramp5(RAMPS["parchment"])
        for y in (18, 20, 22):
            ic.line(7, y - 2, 13, y - 0.4, ic.color("ln", P[1])); ic.line(19, y - 0.4, 25, y - 2, "ln")
        ic.part("spark", "topaz", style="glow")
        ic.poly([(16, 1), (17.6, 6.4), (23, 8), (17.6, 9.6), (16, 15), (14.4, 9.6), (9, 8), (14.4, 6.4)], "spark")
        sparkle(ic, 24, 3, "#fff6c0"); sparkle(ic, 8, 4, "#fff6c0")
    elif kind == "map":
        ic.part("p1", "parchment", style="soft"); ic.part("p2", ["#6a4a24", "#a07a48", "#c8a46e", "#e8cc94"], style="soft")
        xs = [4, 11, 18, 25, 29]
        for i in range(4):
            ic.poly([(xs[i], 7 + (i % 2) * 2), (xs[i + 1], 7 + ((i + 1) % 2) * 2), (xs[i + 1], 25 + ((i + 1) % 2) * 2), (xs[i], 25 + (i % 2) * 2)],
                    "p1" if i % 2 == 0 else "p2")
        ic.color("path", "#7a3a1a")
        for x, y in ((7, 21), (9, 19), (11, 18), (13, 17), (15, 15), (17, 14)):
            ic.set(x, y, "path")
        ic.color("x", "#d02a2a")
        for d in range(-2, 3):
            ic.set(21 + d, 12 + d, "x"); ic.set(21 + d, 12 - d, "x")
        ic.part("tree", "herb", style="round"); ic.ellipse(8, 12, 2, 2, "tree"); ic.ellipse(25, 21, 2, 2, "tree")
    elif kind == "quest":
        ic.part("paper", "parchment", style="soft")
        ic.poly([(6, 5), (22, 5), (26, 9), (26, 29), (6, 29)], "paper")
        ic.part("fold", ["#6a4a24", "#a07a48", "#c8a46e", "#e8cc94"], flat=True)
        ic.poly([(22, 5), (26, 9), (22, 9)], "fold")
        P = ramp5(RAMPS["parchment"])
        for y in (13, 16, 19, 22, 25):
            ic.line(9, y, 17 if y != 25 else 14, y, ic.color("ln", P[1]))
        ic.part("badge", "gold", style="round")
        ic.ellipse(22, 22, 6.2, 6.2, "badge")
        ic.color("ex", "#7a1a0a")
        ic.rect(21.2, 17.5, 22.8, 23, "ex"); ic.rect(21.2, 24.5, 22.8, 26, "ex")
    elif kind == "shop":
        ic.part("wall", "wood")
        ic.rect(6, 14, 26, 28, "wall")
        ic.part("counter", "darkwood"); ic.rect(5, 22, 27, 25, "counter")
        for i in range(5):                                           # striped awning
            p = ic.part(f"aw{i}", "red" if i % 2 == 0 else "white", style="soft")
            x0 = 3 + i * 5.2
            ic.poly([(x0 + 2, 5), (x0 + 7.2, 5), (x0 + 5.2, 13), (x0, 13)], p)
            ic.ellipse(x0 + 2.6, 13.4, 2.6, 2.0, p)
        ic.part("coin", "gold"); ic.ellipse(16, 19.4, 2.2, 2.2, "coin")
    elif kind == "settings":
        ic.part("gear", "steel")
        teeth = 8
        pts = []
        for i in range(teeth * 4):
            a = 2 * math.pi * i / (teeth * 4)
            r = 12.4 if (i % 4) in (1, 2) else 9.4
            pts.append((16 + r * math.cos(a), 16 + r * math.sin(a)))
        ic.poly(pts, "gear")
        ic.ellipse(16, 16, 4.0, 4.0, None)
        ic.part("hub", "iron"); ic.ellipse(16, 16, 6.2, 6.2, "hub"); ic.ellipse(16, 16, 3.2, 3.2, None)
    elif kind == "save":
        ic.part("ped", "stone", style="round")
        ic.poly([(9, 27), (23, 27), (21, 23), (11, 23)], "ped")
        ic.part("cl", ["#2a64d8", "#5aaaff", "#9ad8ff", W], flat=True); ic.part("cr", ["#1a3a9a", "#2a64d8", "#2a64d8", W], flat=True)
        ic.poly([(16, 2), (22, 11), (16, 21), (16, 2)], "cr")
        ic.poly([(16, 2), (10, 11), (16, 21)], "cl")
        ic.part("cm", ["#5aaaff", "#9ad8ff", "#9ad8ff", W], flat=True)
        ic.poly([(16, 2), (13.4, 11), (16, 21)], "cm")
        sparkle(ic, 24, 4, "#cfefff"); sparkle(ic, 7, 16, "#cfefff")
    elif kind == "home":
        ic.part("roof", "red", style="soft")
        ic.poly([(16, 3), (29, 15), (25, 15), (16, 7), (7, 15), (3, 15)], "roof")
        ic.poly([(16, 4.4), (26, 14), (6, 14)], "roof")
        ic.part("wall", "parchment", style="soft"); ic.rect(8, 14, 24, 28, "wall")
        ic.part("door", "wood"); ic.rect(14, 19, 18, 28, "door")
        ic.part("win", "blue", style="round"); ic.rect(9.5, 17, 12.5, 20, "win"); ic.rect(19.5, 17, 22.5, 20, "win")
        ic.part("chim", "stone"); ic.rect(21, 5, 23, 9, "chim")
    elif kind == "mail":
        ic.part("env", "white", style="soft")
        ic.rect(4, 9, 28, 25, "env")
        ic.part("flap", ["#8a8aa0", "#c8cad8", "#e6e8f2", W], style="soft")
        ic.poly([(4, 9), (28, 9), (16, 19)], "flap")
        ic.part("seal", "red", style="round"); ic.ellipse(16, 18, 2.8, 2.8, "seal")
    elif kind == "battle":
        for i, sgn in enumerate((1, -1)):
            b = ic.part(f"blade{i}", "steel", style="blade")
            x0 = 16 - sgn * 10
            ic.bar(16 + sgn * 0.0 - sgn * 7, 22, 16 + sgn * 9, 4, 3.2, 1.0, b)
            g = ic.part(f"guard{i}", "gold")
            ic.bar(16 - sgn * 10.5, 18.5, 16 - sgn * 4.5, 24.5, 2.2, 2.2, g)
            h = ic.part(f"hilt{i}", "leather", style="soft")
            ic.bar(16 - sgn * 8.4, 23.4, 16 - sgn * 11.6, 27.6, 2.4, 2.4, h)
            ic.ellipse(16 - sgn * 12.4, 28.4, 1.4, 1.4, g)
    elif kind == "auto":
        ic.part("ring", "green", style="soft")
        e1 = _arc(ic, 16, 16, 10, 200, 340, 3.4, "ring")
        e2 = _arc(ic, 16, 16, 10, 20, 160, 3.4, "ring")
        ic.poly([(e1[0] - 2, e1[1] - 4.5), (e1[0] + 4.6, e1[1] + 0.6), (e1[0] - 3.2, e1[1] + 3.0)], "ring")
        ic.poly([(e2[0] + 2, e2[1] + 4.5), (e2[0] - 4.6, e2[1] - 0.6), (e2[0] + 3.2, e2[1] - 3.0)], "ring")
    elif kind == "speed":
        for i in range(2):
            p = ic.part(f"chev{i}", "orange", style="soft")
            x = 4 + i * 11
            ic.poly([(x, 6), (x + 6, 6), (x + 15, 16), (x + 6, 26), (x, 26), (x + 9, 16)], p)
    elif kind in ("confirm", "close", "back"):
        ic.part("disc", {"confirm": "green", "close": "red", "back": "blue"}[kind], style="round")
        ic.ellipse(16, 16, 13, 13, "disc")
        ic.part("mark", "white", style="soft")
        if kind == "confirm":
            ic.bar(9, 16.5, 14, 22, 3.6, 3.6, "mark"); ic.bar(13, 22, 23.5, 10, 3.6, 3.6, "mark")
        elif kind == "close":
            ic.bar(10, 10, 22, 22, 3.8, 3.8, "mark"); ic.bar(22, 10, 10, 22, 3.8, 3.8, "mark")
        else:
            e = _arc(ic, 15, 17, 6, -90, 90, 3.4, "mark")
            ic.bar(15, 11, 12, 11, 3.4, 3.4, "mark")
            ic.poly([(13, 5.5), (13, 16.5), (6.5, 11)], "mark")
            ic.bar(e[0], e[1], 10, e[1], 3.4, 3.4, "mark")
    elif kind == "gold":
        for i, (x, y) in enumerate(((10, 24), (10, 21), (10, 18), (21, 25), (21, 22))):
            p = ic.part(f"c{i}", "gold")
            ic.ellipse(x, y, 7, 2.8, p)
        ic.part("big", "gold")
        ic.ellipse(20, 13, 7.4, 7.4, "big")
        ic.part("mark", "gold", style="round"); ic.ellipse(20, 13, 4.2, 4.2, "mark")
        sparkle(ic, 26, 5, "#fff6c0")
    elif kind == "gem":
        G = ramp5(RAMPS["ruby" if False else "pink"])
        cuts = [(9, 7), (23, 7), (28, 13), (16, 28), (4, 13)]
        ic.part("g0", [G[3]] * 4, flat=True); ic.part("g1", [G[2]] * 4, flat=True); ic.part("g2", [G[1]] * 4, flat=True)
        ic.part("g3", [G[4]] * 4, flat=True)
        ic.poly(cuts, "g1")
        ic.poly([(4, 13), (28, 13), (23, 7), (9, 7)], "g0")
        ic.poly([(16, 13), (28, 13), (16, 28)], "g2")
        ic.poly([(11, 8.6), (21, 8.6), (19, 12), (13, 12)], "g3")
        sparkle(ic, 26, 4, "#ffffff")
    elif kind == "stamina":
        ic.part("bolt", "topaz", style="soft")
        ic.poly([(18, 2), (8, 17), (15, 17), (11, 30), (25, 12), (17.5, 12), (23, 2)], "bolt")
        ic.part("core", ["#fff6c0", "#fffbe0", W, W], flat=True)
        ic.line(19, 4, 12, 15, "core")
    elif kind == "cursor":
        ic.part("glove", "white", style="soft")
        ic.poly([(5, 12), (11, 10), (17, 11), (29, 11.5), (29.5, 14.5), (19, 15.5), (19.5, 18), (19, 21), (18, 24), (8, 24), (5, 21)], "glove")
        ic.part("cuff", ["#5a6a8a", "#9aa8c8", "#c8d4ec", W], style="soft")
        ic.rect(2, 12, 5, 24, "cuff")
        ic.part("fold", ["#8a8aa0", "#9a9ab0", "#9a9ab0", W], flat=True)
        for y in (18, 21):
            ic.line(12, y, 18, y, "fold")
        ic.line(11, 15, 17, 15, "fold")
    if style == "mono":
        wr = ramp5(["#6a7088", "#c4c8d8", "#eef0f8", "#ffffff"])
        dk = ramp5(["#1e2030", "#3a3e52", "#5a5f78", "#8a90a8"])
        for k_ in list(ic.spec):
            ic.spec[k_] = (dk if k_ == "disc" else wr, ic.spec[k_][1] if ic.spec[k_][1] != "flat" else "soft")
        for k_ in list(ic.fixed):
            ic.fixed[k_] = "#9aa0b8"
        ic.extra = [(x, y, "#ffffff") for x, y, _ in ic.extra]
    return emit(f"ui-icon-{kind}{'-mono' if style == 'mono' else ''}", ic)
