"""Material & misc icons (素材与杂项图标), JRPG inventory style at 32 / 48 / 64 px with per-pixel lighting: ore, ingot,
gem, magic crystal, herb, mushroom, key, coin pouch. Each `color` is its own design (different gem cut, herb, mushroom,
key bow …), not only a recolour. `frame` adds a rarity slot."""
from __future__ import annotations

import math

from ._icon import FRAMES, RAMPS, SIZES, Icon, emit, ramp5, sparkle

DESCRIPTION = "JRPG material icon (32/48/64 px): ore, ingot, gem, crystal, herb, mushroom, key, coin pouch — each colour is its own design."
ASSET_TYPE = "item"


def FULL_BLEED(frame="none", **_):
    return frame != "none"


KINDS = ["ore", "ingot", "gem", "crystal", "herb", "mushroom", "key", "coin_pouch"]
COLORS = ["red", "blue", "green", "purple", "gold", "silver"]
PARAMS = {"kind": {"type": "string", "default": "gem", "enum": KINDS},
          "color": {"type": "string", "default": "red", "enum": COLORS},
          "frame": {"type": "string", "default": "none", "enum": FRAMES},
          "size": {"type": "int", "default": 48, "enum": SIZES}}
GEM = {"red": "ruby", "blue": "sapphire", "green": "emerald", "purple": "amethyst", "gold": "topaz", "silver": "diamond"}
METAL = {"red": "copper", "blue": "mithril", "green": "bronze", "purple": "dark", "gold": "gold", "silver": "silver"}
CLOTH = {"red": "red", "blue": "blue", "green": "green", "purple": "purple", "gold": "orange", "silver": "white"}


def _facets(ic: Icon, pts, centre, ramp):
    """Faceted gem: fan of triangles from the centre, tones by facet orientation to the top-left light."""
    G = ramp5(RAMPS[ramp])
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        mx, my = (a[0] + b[0]) / 2 - centre[0], (a[1] + b[1]) / 2 - centre[1]
        L = math.hypot(mx, my) or 1
        lit = -(mx + my) / (L * 1.414)
        tone = 4 if lit > 0.75 else 3 if lit > 0.25 else 2 if lit > -0.35 else 1
        ic.part(f"fac{i}", [G[tone]] * 4, flat=True)
        ic.poly([centre, a, b], f"fac{i}")


def build(kind: str = "gem", color: str = "red", frame: str = "none", size: int = 48, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if color not in COLORS:
        raise ValueError(f"color must be one of {COLORS}")
    ci = COLORS.index(color)
    ic = Icon(int(size))
    gem, metal, cloth = GEM[color], METAL[color], CLOTH[color]
    G, M = ramp5(RAMPS[gem]), ramp5(RAMPS[metal])
    if kind == "ore":
        ic.part("rock", "stone", style="round")
        shapes = [[(6, 18), (10, 9), (18, 6), (25, 10), (27, 19), (23, 27), (11, 28), (5, 24)],
                  [(4, 22), (8, 12), (14, 8), (20, 10), (24, 6), (28, 14), (27, 24), (18, 28), (8, 28)],
                  [(8, 26), (6, 16), (12, 8), (22, 5), (27, 12), (26, 22), (20, 28)]]
        shape = shapes[ci % 3] if ci < 3 else [(32 - x, y) for x, y in shapes[ci % 3]]       # 3 lumps, mirrored for 3–5
        ic.poly(shape, "rock")
        ic.part("vein", metal, style="metal" if metal != "dark" else "gem")
        nuggets = [((13, 14, 2.6), (20, 19, 3.0), (11, 22, 1.8), (21, 11, 1.6)),
                   ((16, 15, 3.4), (10, 21, 2.2), (23, 18, 2.0)),
                   ((14, 12, 2.0), (19, 16, 2.4), (13, 21, 2.6), (22, 23, 1.6), (17, 8, 1.4))][ci % 3]
        for cx, cy, r in nuggets:
            ic.ellipse(cx if ci < 3 else 32 - cx, cy, r, r * 0.85, "vein")
        if color in ("purple", "blue"):
            sparkle(ic, 25, 6, G[4])
    elif kind == "ingot":
        def bar(y0, name, w=1.0):
            ic.part(name + "t", [M[2], M[3], M[3], M[4]], flat=True)
            ic.part(name + "f", metal, style="metal")
            ic.part(name + "s", [M[0], M[1], M[1], M[1]], flat=True)
            x0, x1 = 16 - 11 * w, 16 + 11 * w
            ic.poly([(x0 + 4, y0), (x1 - 4, y0), (x1, y0 + 5), (x0, y0 + 5)], name + "t")
            ic.poly([(x0, y0 + 5), (x1, y0 + 5), (x1 - 2, y0 + 13), (x0 + 2, y0 + 13)], name + "f")
            ic.poly([(x1, y0 + 5), (x1 + 2, y0 + 2), (x1 + 1, y0 + 9), (x1 - 2, y0 + 13)], name + "s")
        v = ci
        if v == 0:
            bar(12, "a")
        elif v == 1:
            bar(15, "a"); bar(7, "b", 0.8)
        elif v == 3:
            bar(16, "a", 0.62); bar(8, "b", 0.62)
        elif v == 4:                                                 # pyramid of three
            bar(17, "a", 0.55)
            bar(9, "b", 0.55)
            ic.part("nug", metal, style="round")
            ic.ellipse(6, 26, 3, 2.4, "nug"); ic.ellipse(26.5, 26, 2.6, 2.2, "nug")
        elif v == 5:
            bar(14, "a", 0.8)
            ic.part("nug", metal, style="round")
            ic.ellipse(8, 9, 3.2, 2.6, "nug")
        else:
            bar(12, "a")
            ic.color("stamp", M[1])
            for x, y in ((14, 20), (15, 19), (16, 20), (17, 19), (18, 20), (15, 21), (16, 21), (17, 21)):
                ic.set(x, y, "stamp")
        sparkle(ic, 24, 8 if v not in (1, 3, 4) else 4, "#ffffff")
    elif kind == "gem":
        cuts = {
            "red": [(16 + 11 * math.cos(math.radians(a)), 16 + 9 * math.sin(math.radians(a))) for a in range(-90, 270, 45)],
            "blue": [(7, 9), (11, 5), (21, 5), (25, 9), (25, 21), (21, 26), (11, 26), (7, 21)],
            "green": [(9, 6), (23, 6), (26, 10), (26, 22), (23, 26), (9, 26), (6, 22), (6, 10)],
            "purple": [(16, 3), (22, 11), (24, 18), (21, 25), (16, 28), (11, 25), (8, 18), (10, 11)],
            "gold": [(16, 4), (28, 25), (4, 25)],
            "silver": [(16 + 11 * math.cos(math.radians(a)), 16 + 11 * math.sin(math.radians(a))) for a in range(-90, 270, 30)],
        }[color]
        ic.part("rim", gem)
        ic.poly(cuts, "rim")
        cx = sum(p[0] for p in cuts) / len(cuts)
        cy = sum(p[1] for p in cuts) / len(cuts)
        inner = [(cx + (x - cx) * 0.55, cy + (y - cy) * 0.55) for x, y in cuts]
        _facets(ic, cuts, (cx, cy), gem)
        if color == "green":                                           # step cut: inner table
            ic.part("table", [G[3]] * 4, flat=True)
            ic.poly(inner, "table")
        else:
            ic.part("table", [G[3]] * 4, flat=True)
            ic.poly([(cx + (x - cx) * 0.35, cy + (y - cy) * 0.35) for x, y in cuts], "table")
        tab = inner if color == "green" else [(cx + (x - cx) * 0.35, cy + (y - cy) * 0.35) for x, y in cuts]
        ic.color("edgeD", G[1]); ic.color("edgeL", G[4])
        for (x0, y0), (x1, y1) in zip(tab, cuts):                      # facet edges
            ic.line(x0, y0, x1, y1, "edgeL" if (x1 - cx) + (y1 - cy) < 0 else "edgeD", w=0.7)
        for (x0, y0), (x1, y1) in zip(tab, tab[1:] + tab[:1]):
            ic.line(x0, y0, x1, y1, "edgeL", w=0.6)
        sparkle(ic, cx - 4, cy - 4, "#ffffff"); sparkle(ic, 26, 5, "#ffffff")
    elif kind == "crystal":
        ic.part("base", "stone", style="round")
        ic.poly([(5, 25), (9, 21), (23, 21), (27, 25), (24, 28), (8, 28)], "base")
        layouts = [((16, 24, 4.4, 20, 0.5), (10.5, 25, 3.0, 12, -3), (21.5, 25, 3.2, 13, 3), (13, 26, 2, 6, -2)),
                   ((13, 24, 3.6, 18, -2), (19, 24, 3.6, 15, 2.6), (24, 26, 2.2, 7, 3), (8, 26, 2.2, 8, -3)),
                   ((16, 25, 5.2, 14, 0), (9, 26, 2.6, 9, -4), (23, 26, 2.6, 10, 4))]
        mir = ci >= 3
        for i, (bx, by, w, h, lean) in enumerate(layouts[ci % 3]):
            if mir:
                bx, lean = 32 - bx, -lean
            pl = ic.part(f"cl{i}", [G[3]] * 4, flat=True)
            pr = ic.part(f"cr{i}", [G[1]] * 4, flat=True)
            pm = ic.part(f"cm{i}", [G[2]] * 4, flat=True)
            tip = (bx + lean, by - h)
            ic.poly([(bx - w, by), (bx - w + lean * 0.8, by - h + 3), tip, (bx + lean * 0.1, by - h + 3.5), (bx, by + 1)], pl)
            ic.poly([(bx, by + 1), (bx + lean * 0.1, by - h + 3.5), tip, (bx + w + lean * 0.8, by - h + 3), (bx + w, by)], pr)
            ic.poly([(bx - w * 0.3, by), (bx - w * 0.3 + lean * 0.8, by - h + 3.2), tip, (bx + lean * 0.1, by - h + 3.5), (bx, by + 1)], pm)
        sparkle(ic, 15, 8, "#ffffff"); sparkle(ic, 25, 8, G[4]); ic.dot(6, 16, G[4]); ic.dot(27, 18, G[3])
    elif kind == "herb":
        ic.part("stem", "herb", style="soft")
        leaf_n = 0

        def leaf(x, y, a, L=4.0, W=2.4, ramp="herb"):
            nonlocal leaf_n
            p = ic.part(f"leaf{leaf_n}", ramp, style="soft"); leaf_n += 1
            dx, dy = math.sin(a), -math.cos(a)
            ic.poly([(x, y), (x + dx * L * 0.5 + dy * W, y + dy * L * 0.5 - dx * W), (x + dx * L * 1.3, y + dy * L * 1.3),
                     (x + dx * L * 0.5 - dy * W, y + dy * L * 0.5 + dx * W)], p)
        if color == "red":                                           # healing herb with red berries
            ic.line(16, 28, 16, 10, "stem"); ic.line(16, 22, 10, 14, "stem"); ic.line(16, 19, 22, 11, "stem")
            for x, y, a in ((16, 22, -0.9), (16, 19, 0.8), (16, 15, -0.5), (16, 24, 0.9), (16, 12, 0.2)):
                leaf(x, y, a)
            ic.part("berry", "ruby")
            for x, y in ((10, 13), (22, 10), (11.5, 11), (16, 8)):
                ic.ellipse(x, y, 1.6, 1.6, "berry")
        elif color == "blue":                                        # bellflowers
            ic.line(14, 28, 12, 8, "stem"); ic.line(14, 24, 22, 12, "stem")
            for x, y, a in ((13, 24, -0.8), (15, 22, 0.9), (13, 18, -1.0)):
                leaf(x, y, a, 5, 2.2)
            ic.part("bell", "blue", style="round")
            for x, y in ((12, 8), (22, 12), (18, 16)):
                ic.poly([(x - 1.6, y), (x + 1.6, y), (x + 2.6, y + 4), (x - 2.6, y + 4)], "bell")
        elif color == "green":                                       # four-leaf clover sprig
            ic.line(16, 28, 16, 15, "stem")
            for a in (0, 90, 180, 270):
                aa = math.radians(a + 45)
                p = ic.part(f"lobe{a}", "herb", style="round")
                ic.ellipse(16 + 4.4 * math.cos(aa), 11 + 4.4 * math.sin(aa), 3.8, 3.8, p)
            leaf(16, 24, 0.9, 4, 2)
        elif color == "purple":                                      # lavender spikes
            for x0, x1 in ((12, 9), (16, 16), (20, 23)):
                ic.line(16, 28, x1, 8, "stem")
                ic.part(f"lav{x1}", "purple", style="round")
                for k in range(5):
                    t = k / 5
                    ic.ellipse(16 + (x1 - 16) * (0.55 + 0.45 * t), 18 - 10 * t, 1.5, 1.4, f"lav{x1}")
            leaf(16, 25, -0.8, 5, 2); leaf(16, 25, 0.8, 5, 2)
        elif color == "gold":                                        # golden wheat
            for x1 in (11, 16, 21):
                ic.line(16, 28, x1, 12, "stem")
                ic.part(f"ear{x1}", "topaz", style="round")
                for k in range(4):
                    yy = 12 - k * 2
                    ic.ellipse(x1 - 1.2, yy, 1.1, 1.4, f"ear{x1}"); ic.ellipse(x1 + 1.2, yy - 1, 1.1, 1.4, f"ear{x1}")
        else:                                                        # silver fern
            ic.line(10, 28, 22, 5, "stem")
            for k in range(1, 9):
                x, y = 10 + 12 * k / 9, 28 - 23 * k / 9
                L = 5 * (1 - k / 11)
                leaf(x, y, -1.4, L, 1.2, "silver"); leaf(x, y, 0.5, L, 1.2, "silver")
        if color in ("red", "blue", "purple"):
            ic.part("tie", "parchment", style="soft")
            ic.rect(14, 24.5, 18, 25.5, "tie")
    elif kind == "mushroom":
        cap = {"red": "red", "blue": "blue", "green": "green", "purple": "purple", "gold": "orange", "silver": "white"}[color]
        ic.part("stalk", "rice", style="round")
        ic.part("cap", cap, style="round")
        if color == "red":                                           # toadstool
            ic.poly([(13, 17), (19, 17), (20, 27), (12, 27)], "stalk")
            ic.poly([(4, 18), (6, 11), (11, 6), (16, 5), (21, 6), (26, 11), (28, 18)], "cap")
            for x, y, r in ((11, 10, 1.6), (19, 9, 1.4), (23, 14, 1.2), (8, 15, 1.1), (15, 13, 1.3)):
                ic.ellipse(x, y, r, r, ic.part(f"spot{x}", "white", style="round"))
        elif color == "blue":                                        # tall glowing cap
            ic.poly([(14, 14), (18, 14), (18.6, 28), (13.4, 28)], "stalk")
            ic.ellipse(16, 11, 8, 6.6, "cap")
            for x, y in ((12, 9), (16, 7), (20, 10), (14, 13)):
                ic.dot(x, y, "#bff4ff")
            sparkle(ic, 26, 5, "#9af0ff"); sparkle(ic, 6, 18, "#9af0ff")
        elif color == "green":                                       # flat-cap cluster
            for i, (x, y, r) in enumerate(((11, 15, 6), (21, 19, 5), (15, 23, 4))):
                st = ic.part(f"st{i}", "rice", style="round")
                ic.rect(x - 1.2, y, x + 1.2, 28, st)
                cp = ic.part(f"cp{i}", "green", style="round")
                ic.ellipse(x, y, r, r * 0.45, cp)
        elif color == "purple":                                      # conical witch cap
            ic.poly([(14, 18), (18, 18), (19, 28), (13, 28)], "stalk")
            ic.poly([(5, 19), (16, 2), (27, 19), (20, 21), (12, 21)], "cap")
            ic.part("band", "black", style="soft")
            ic.poly([(8, 16), (24, 16), (25.5, 18.5), (6.5, 18.5)], "band")
        elif color == "gold":                                        # chanterelle bunch
            for i, (x, y, w) in enumerate(((10, 12, 5), (19, 10, 6), (24, 17, 4))):
                cp = ic.part(f"cp{i}", "orange", style="round")
                ic.poly([(x - w, y), (x + w, y), (x + 1.4, y + 12), (x - 1.4, y + 12)], cp)
        else:                                                        # puffball pair
            ic.ellipse(13, 18, 8, 7.4, "cap")
            ic.part("cap2", "white", style="round")
            ic.ellipse(23, 23, 4.4, 4.0, "cap2")
            for x, y in ((10, 15), (14, 13), (16, 18), (11, 20)):
                ic.dot(x, y, ramp5(RAMPS["white"])[1])
        ic.part("grass", "herb", style="soft")
        ic.poly([(4, 29), (8, 24), (9, 29)], "grass"); ic.poly([(24, 29), (27, 23), (29, 29)], "grass")
    elif kind == "key":
        mt = ic.part("bow", metal, style="metal")
        bows = {
            "red": lambda: (ic.ellipse(7, 8, 3.6, 3.6, mt), ic.ellipse(13, 8, 3.6, 3.6, mt), ic.poly([(3.6, 9.4), (16.4, 9.4), (10, 17)], mt)),
            "blue": lambda: ic.poly([(10, 2), (17, 9), (10, 16), (3, 9)], mt),
            "green": lambda: [ic.ellipse(10 + 3.4 * math.cos(math.radians(a)), 9 + 3.4 * math.sin(math.radians(a)), 2.8, 2.8, mt) for a in (0, 90, 180, 270)],
            "purple": lambda: (ic.ellipse(10, 9, 5, 5, mt), ic.poly([(6, 6), (1, 2), (4, 9)], mt), ic.poly([(14, 6), (19, 2), (16, 9)], mt)),
            "gold": lambda: (ic.ellipse(10, 10, 5.4, 5.4, mt), ic.poly([(5, 6), (6, 1), (8, 4), (10, 0.5), (12, 4), (14, 1), (15, 6)], mt)),
            "silver": lambda: ic.ellipse(10, 9, 5.6, 5.6, mt),
        }
        bows[color]()
        ic.ellipse(10, 9, 2.0, 2.0, None)
        ic.part("shaft", metal, style="metal")
        ic.bar(12.6, 13.6, 25.6, 26.6, 2.8, 2.8, "shaft")
        teeth = [(0.72, 4.6), (0.9, 3.4)] if ci % 2 == 0 else [(0.66, 3.0), (0.78, 4.6), (0.92, 3.0)]
        for t, ln in teeth:
            x, y = 12.6 + 13.4 * t, 13.6 + 13.4 * t
            ic.bar(x, y, x - ln * 0.707 + 0.5, y + ln * 0.707 + 0.5, 2.2, 2.2, "shaft")
        ic.part("jewel", gem)
        ic.ellipse(13.4, 14.4, 1.5, 1.5, "jewel")
    elif kind == "coin_pouch":
        ic.part("sack", cloth if color != "silver" else "leather", style="soft")
        ic.poly([(11, 9), (21, 9), (19, 12), (26, 18), (27, 24), (23, 28), (9, 28), (5, 24), (6, 18), (13, 12)], "sack")
        ic.poly([(10, 5), (22, 5), (20, 9), (12, 9)], "sack")
        ic.part("cord", "gold" if color in ("red", "purple") else "parchment", style="soft")
        ic.rect(11, 9, 21, 10, "cord")
        ic.poly([(19, 10), (21, 10), (23, 15), (21, 15)], "cord")
        coin = "silver" if color == "silver" else "gold"
        spills = {"red": ((25, 27), (28.5, 24.5)), "blue": ((24, 26), (28, 25), (26, 22)),
                  "green": ((24, 27), (28, 26), (26, 23), (4.5, 27)), "purple": ((27, 27),),
                  "gold": ((24, 26), (28, 25), (26, 22), (20, 28), (28, 29)), "silver": ((5, 27), (8, 28.5), (4, 24))}
        for i, (x, y) in enumerate(spills[color]):
            p = ic.part(f"coin{i}", coin, style="metal")
            ic.ellipse(x, y, 2.4, 2.0, p)
        if color == "blue":
            ic.part("g", "sapphire"); ic.ellipse(7, 26, 2, 2, "g")
        if color == "purple":
            ic.color("star", "#ffe07a")
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                ic.set(15 + dx, 20 + dy, "star")
        elif color == "green":
            ic.part("patch", "leather", style="soft"); ic.rect(9, 19, 13, 23, "patch")
        else:
            ic.part("mark", coin, style="metal")
            ic.ellipse(15, 20, 2.6, 2.6, "mark")
    return emit(f"{color}-{kind}".replace("_", "-"), ic, frame)
