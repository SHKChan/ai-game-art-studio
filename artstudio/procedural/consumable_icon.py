"""Consumable icons (消耗品图标), JRPG inventory style at 32 / 48 / 64 px with per-pixel lighting: HP potion, MP ether,
antidote, elixir, phoenix feather, scroll, bomb, onigiri. `grade` (minor / normal / greater) changes the design —
e.g. Potion → Hi-Potion → X-Potion: small vial → round flask → ornate crowned bottle. `frame` adds a rarity slot."""
from __future__ import annotations

import math

from ._icon import FRAMES, RAMPS, SIZES, Icon, emit, ramp5, sparkle

DESCRIPTION = "JRPG consumable icon (32/48/64 px): 8 kinds × 3 grades (minor / normal / greater) with different bottles and details."
ASSET_TYPE = "item"


def FULL_BLEED(frame="none", **_):
    return frame != "none"


KINDS = ["hp_potion", "mp_potion", "antidote", "elixir", "phoenix_feather", "scroll", "bomb", "onigiri"]
GRADES = ["minor", "normal", "greater"]
PARAMS = {"kind": {"type": "string", "default": "hp_potion", "enum": KINDS},
          "grade": {"type": "string", "default": "normal", "enum": GRADES},
          "frame": {"type": "string", "default": "none", "enum": FRAMES},
          "size": {"type": "int", "default": 48, "enum": SIZES}}
LIQUID = {"hp_potion": "red", "mp_potion": "blue", "antidote": "green", "elixir": "pink"}


def _bottle(ic: Icon, shape: str, liquid: str, level: float, cork="wood", gold=False):
    """Glass bottle of a given shape, filled with liquid up to `level` (design y)."""
    shapes = {
        "vial": (lambda p, i: (i.poly([(12, 12), (20, 12), (20.5, 26), (16, 28.5), (11.5, 26)], p)), (13.5, 7, 18.5, 12)),
        "round": (lambda p, i: i.ellipse(16, 20, 9, 8.6, p), (13, 8, 18, 12)),
        "tall": (lambda p, i: i.poly([(10, 14), (13, 11), (19, 11), (22, 14), (22, 27), (10, 27)], p), (13, 6, 18, 10)),
        "flask": (lambda p, i: i.poly([(13.5, 11), (18.5, 11), (25, 25), (23, 28), (9, 28), (7, 25)], p), (13.5, 6, 18.5, 11)),
        "heart": (lambda p, i: (i.ellipse(12, 17, 5.4, 5.4, p), i.ellipse(20, 17, 5.4, 5.4, p), i.poly([(6.8, 19), (25.2, 19), (16, 29)], p)), (13.5, 7, 18.5, 12)),
        "diamond": (lambda p, i: i.poly([(16, 10), (25.5, 19), (16, 29.5), (6.5, 19)], p), (14, 6, 18, 10)),
    }
    body, (nx0, ny0, nx1, ny1) = shapes[shape]
    ic.part("glass", "glass")
    ic.part("liq", liquid, style="round")
    ic.color("air", "#d4e8f2")
    body("glass", ic)
    ic.rect(nx0, ny0, nx1, ny1, "glass")
    inner = Icon(ic.n)
    body("x", inner)
    k = ic.k
    m = max(1, int(round(1.2 * k)))
    for y in range(ic.n):
        for x in range(ic.n):
            if all(0 <= x + dx < ic.n and 0 <= y + dy < ic.n and inner.parts[y + dy][x + dx] for dx, dy in ((m, 0), (-m, 0), (0, m), (0, -m))):
                yd = (y + .5) / k - .5
                if yd > ny1:
                    ic.parts[y][x] = "liq" if yd >= level else "air"
    lip = ic.part("lip", "gold" if gold else "glass", style="metal" if gold else "glass")
    ic.rect(nx0 - 1, ny0, nx1 + 1, ny0 + 1, lip)
    ic.part("cork", cork, style="metal" if cork == "gold" else "wood")
    ic.rect(nx0 + 0.5, ny0 - 3, nx1 - 0.5, ny0 - 1, "cork")
    L5 = ramp5(RAMPS[liquid])
    return L5, (nx0, ny0, nx1, ny1)


def build(kind: str = "hp_potion", grade: str = "normal", frame: str = "none", size: int = 48, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if grade not in GRADES:
        raise ValueError(f"grade must be one of {GRADES}")
    gi = GRADES.index(grade)
    ic = Icon(int(size))
    W = "#ffffff"
    if kind in LIQUID:
        shape = {"hp_potion": ["vial", "round", "heart"], "mp_potion": ["vial", "tall", "diamond"],
                 "antidote": ["vial", "flask", "flask"], "elixir": ["round", "diamond", "heart"]}[kind][gi]
        level = {"vial": 17, "round": 16.5, "tall": 15, "flask": 17, "heart": 15.5, "diamond": 16}[shape]
        L5, (nx0, ny0, nx1, ny1) = _bottle(ic, shape, LIQUID[kind], level, cork="gold" if gi == 2 or kind == "elixir" else "wood",
                                           gold=gi == 2 or kind == "elixir")
        ic.dot(11.5 if shape != "vial" else 13, level + 1.5, W); ic.dot(11.5 if shape != "vial" else 13, level + 2.5, "#e8f6ff")
        for x, y in ((18, level + 6), (20, level + 3), (16, level + 9)):
            ic.dot(x, y, L5[4])
        if gi >= 1 and kind != "elixir":                                  # string tie
            ic.part("tie", "gold" if gi == 2 else "parchment", style="soft")
            ic.rect(nx0 - 0.5, ny1 - 1.5, nx1 + 0.5, ny1 - 0.5, "tie")
            ic.poly([(nx1, ny1 - 1), (nx1 + 3.6, ny1 + 3.6), (nx1 + 2.2, ny1 + 4.4), (nx1 - 0.5, ny1)], "tie")
        if kind == "mp_potion" and gi == 1:
            ic.part("label", "parchment", style="soft")
            ic.rect(12, 19, 20, 23, "label")
            ic.dot(16, 21, L5[1])
        if kind == "antidote":
            ic.part("leaf", "herb", style="soft")
            ic.poly([(19, 4), (26, 3), (24, 8), (20, 8)], "leaf")
            if gi == 2:
                ic.poly([(13, 4), (7, 2), (8, 7), (12, 8)], "leaf")
        if gi == 2 or kind == "elixir":                                  # wings / crown
            ic.part("wing", "gold")
            if kind in ("hp_potion", "elixir") and gi >= 1:
                ic.poly([(13, ny0 + 1), (7, ny0 - 2.5), (5.5, ny0 + 1), (10, ny0 + 3)], "wing")
                ic.poly([(19, ny0 + 1), (25, ny0 - 2.5), (26.5, ny0 + 1), (22, ny0 + 3)], "wing")
            else:
                for x in (nx0 + 0.6, (nx0 + nx1) / 2, nx1 - 0.6):
                    ic.poly([(x - 1.2, ny0 - 3), (x, ny0 - 5.6), (x + 1.2, ny0 - 3)], "wing")
            sparkle(ic, 26, 12, "#fff6b4"); sparkle(ic, 6, 24, "#ffffff")
        if kind == "elixir":
            ic.part("liq2", "purple", style="round")
            for y in range(ic.n):
                for x in range(ic.n):
                    if ic.parts[y][x] == "liq" and (y + .5) / ic.k > level + 6:
                        ic.parts[y][x] = "liq2"
    elif kind == "phoenix_feather":
        n_f = gi + 1
        for fi_ in range(n_f):
            ang = [0, -0.35, 0.35][fi_] if n_f > 1 else 0
            if n_f == 2:
                ang = [-0.2, 0.25][fi_]
            ca, sa = math.cos(ang), math.sin(ang)
            def R(x, y):                                               # rotate around the quill base
                dx, dy = x - 7, y - 26
                return (7 + dx * ca - dy * sa, 26 + dx * sa + dy * ca)
            vane = ic.part(f"vane{fi_}", "fire", style="soft")
            vane2 = ic.part(f"vaneb{fi_}", "red", style="soft")
            pts = [(7 + 18 * u, 26 - 20 * u - 3 * math.sin(math.pi * u)) for u in [i / 30 for i in range(31)]]
            scale = 1.0 if fi_ == 0 else 0.82
            for i, (x, y) in enumerate(pts[3:], 3):
                u = i / 30
                w = 7.2 * scale * math.sin(math.pi * min(1, u * 1.08)) ** 0.7
                xx, yy = R(7 + (x - 7) * scale, 26 + (y - 26) * scale)
                ic.ellipse(xx, yy, w / 2 + .3, w / 2 + .3, vane2 if u < 0.45 else vane)
            ic.part(f"quill{fi_}", "parchment", style="soft")
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                a, b = R(7 + (x0 - 7) * scale, 26 + (y0 - 26) * scale), R(7 + (x1 - 7) * scale, 26 + (y1 - 26) * scale)
                ic.bar(*a, *b, 0.9, 0.9, f"quill{fi_}")
        F = ramp5(RAMPS["fire"])
        for x, y in ((26, 3), (28, 6), (24, 2)):
            ic.dot(x, y, F[4])
        sparkle(ic, 27, 9, "#fff2a0")
        if gi == 2:
            sparkle(ic, 6, 10, "#fff2a0")
    elif kind == "scroll":
        ic.part("paper", "parchment", style="soft")
        ic.rect(8, 8, 24, 23, "paper")
        ic.part("roll", "parchment", style="round")
        ic.ellipse(16, 7, 10, 2.4, "roll"); ic.ellipse(16, 24, 10, 2.4, "roll")
        knob = ic.part("knob", ["darkwood", "darkwood", "gold"][gi])
        for x in (5, 27):
            ic.ellipse(x, 7, 1.5, 1.6, knob); ic.ellipse(x, 24, 1.5, 1.6, knob)
        Pp = ramp5(RAMPS["parchment"])
        for y in (12, 14, 16, 18):
            for x in range(11, 21 if y != 18 else 17):
                if (x + y) % 5:
                    ic.dot(x, y, Pp[1])
        if gi >= 1:
            ic.part("seal", "red", style="round")
            ic.ellipse(21, 20, 3, 3, "seal")
            ic.part("ribbon", "red", style="soft")
            ic.poly([(19, 22), (21, 22), (19.5, 28), (17.5, 27)], "ribbon"); ic.poly([(21, 22), (23, 22), (24.5, 27), (22.5, 28)], "ribbon")
        if gi == 2:                                                    # gold-trimmed magic scroll
            ic.part("trim", "gold")
            ic.rect(8, 9, 8.6, 22, "trim"); ic.rect(23.4, 9, 24, 22, "trim")
            ic.color("rune", "#3a6ad8")
            for a in range(0, 360, 60):
                ic.set(13 + 2.4 * math.cos(math.radians(a)), 15 + 2.4 * math.sin(math.radians(a)), "rune")
            sparkle(ic, 27, 15, "#bfe8ff")
    elif kind == "bomb":
        r = [7.0, 9.4, 9.6][gi]
        cx, cy = (15, 20) if gi < 2 else (13, 21)
        ic.part("ball", "black", style="round")
        ic.ellipse(cx, cy, r, r, "ball")
        if gi == 2:                                                    # skull mark + second bomb
            ic.part("ball2", "black", style="round")
            ic.ellipse(24.5, 25, 4.6, 4.6, "ball2")
            ic.part("skull", "white", style="round")
            ic.ellipse(cx, cy, 3.2, 2.8, "skull"); ic.rect(cx - 1.6, cy + 1.6, cx + 1.6, cy + 3, "skull")
            ic.color("eye", "#0e0a14"); ic.set(cx - 1.4, cy - 0.2, "eye"); ic.set(cx + 1.2, cy - 0.2, "eye")
        cap = ic.part("cap", "iron")
        a = (cx + r * 0.6, cy - r * 0.8)
        ic.bar(a[0] - 1.2, a[1] + 1.2, a[0] + 1.8, a[1] - 1.8, 4.2, 4.2, cap)
        ic.color("fuse", "#c8a46a")
        fx, fy = a[0] + 2.2, a[1] - 2.2
        ic.line(fx, fy, fx + 2, fy - 3, "fuse"); ic.line(fx + 2, fy - 3, fx + 4, fy - 4, "fuse")
        F = ramp5(RAMPS["fire"])
        sparkle(ic, fx + 5, fy - 5, F[3], 2); ic.dot(fx + 5, fy - 5, "#ffffff")
        if gi == 0:
            ic.part("band", "leather", style="soft")
            ic.rect(cx - r + 1, cy - 0.6, cx + r - 1, cy + 0.6, "band")
    elif kind == "onigiri":
        ic.part("rice", "rice", style="round")
        ic.poly([(16, 4), (21, 8), (27, 19), (27, 25), (24, 28), (8, 28), (5, 25), (5, 19), (11, 8)], "rice")
        R5 = ramp5(RAMPS["rice"])
        for x, y in ((12, 11), (19, 10), (9, 17), (22, 15), (16, 14), (11, 22), (23, 22)):
            ic.dot(x, y, R5[1])
        if gi >= 1:
            ic.part("nori", "black", style="soft")
            ic.rect(11, 19, 21, 28, "nori")
        if gi == 2:
            ic.part("ume", "red", style="round")
            ic.ellipse(16, 14, 2.0, 1.8, "ume")
            for x, y in ((13, 22), (18, 24), (15, 26), (19, 21)):
                ic.dot(x, y, "#f2e8c8")
            ic.part("leaf", "herb", style="soft")
            ic.poly([(22, 28), (29, 27), (27, 30), (21, 30)], "leaf")
    return emit(f"{grade}-{kind}".replace("_", "-"), ic, frame)
