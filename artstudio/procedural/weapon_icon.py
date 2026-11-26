"""Weapon icons (武器图标), JRPG inventory style, drawn at 32 / 48 / 64 px with per-pixel lighting.
Kinds: sword, katana, dagger, axe, spear, staff, bow, hammer. The `material` is also a *tier*: each step changes the
shape, not just the colour — bronze (plain) → iron (fuller, flared guard) → mithril (rune-lit, gem fittings) →
gold (ornate, winged) → dark (serrated, horned, glowing runes). `frame` adds a rarity slot."""
from __future__ import annotations

import math

from ._icon import FRAMES, RAMPS, SIZES, Icon, emit, ramp5, sparkle

DESCRIPTION = "JRPG weapon icon (32/48/64 px): 8 kinds × 5 tiers — each tier changes the shape (fuller, guards, runes, wings, serration)."
ASSET_TYPE = "item"


def FULL_BLEED(frame="none", **_):
    return frame != "none"     # a rarity slot fills the canvas


KINDS = ["sword", "katana", "dagger", "axe", "spear", "staff", "bow", "hammer"]
MATERIALS = ["bronze", "iron", "mithril", "gold", "dark"]
PARAMS = {"kind": {"type": "string", "default": "sword", "enum": KINDS},
          "material": {"type": "string", "default": "iron", "enum": MATERIALS},
          "frame": {"type": "string", "default": "none", "enum": FRAMES},
          "size": {"type": "int", "default": 48, "enum": SIZES}}
SET = {  # tier → (blade metal, fittings, grip, gem, wood, rune glow)
    "bronze": ("bronze", "bronze", "leather", "topaz", "wood", None),
    "iron": ("steel", "iron", "leather", "ruby", "wood", None),
    "mithril": ("mithril", "silver", "blue", "sapphire", "white", "#7ae8ff"),
    "gold": ("gold", "gold", "red", "emerald", "darkwood", "#fff6b4"),
    "dark": ("dark", "black", "black", "amethyst", "darkwood", "#e07aff"),
}
U = (0.7071, -0.7071)      # along the weapon (hilt → tip)
V = (0.7071, 0.7071)       # across (towards lower-right)


def P(o, s, t):
    """Point at s along / t across from origin o."""
    return (o[0] + U[0] * s + V[0] * t, o[1] + U[1] * s + V[1] * t)


def _blade(ic: Icon, start, length, width, part, tip=0.25, serrate=0.0, curve=0.0):
    """Blade from `start` along U. width(t) callable or number; curve bends towards V; serrate adds teeth on the V side."""
    pts = [P(start, length * i / 60, curve * math.sin(math.pi * i / 60) * (i / 60)) for i in range(61)]

    def wf(t):
        w = width(t) if callable(width) else width
        return w if t < 1 - tip else w * max(0.0, (1 - t) / tip)

    def px(x, y):
        best, bi = 1e9, 0
        for i in range(0, 61, 2):
            dd = (x - pts[i][0]) ** 2 + (y - pts[i][1]) ** 2
            if dd < best:
                best, bi = dd, i
        for i in (bi - 1, bi + 1):
            if 0 <= i <= 60:
                dd = (x - pts[i][0]) ** 2 + (y - pts[i][1]) ** 2
                if dd < best:
                    best, bi = dd, i
        t = bi / 60
        side = (x - pts[bi][0]) * V[0] + (y - pts[bi][1]) * V[1]
        w = wf(t) / 2
        if serrate and side > 0 and 0.1 < t < 0.85:
            w += serrate * max(0.0, 1 - ((t * 6) % 1) * 1.6)
        if math.sqrt(best) <= w + 0.15 and (0 < bi < 60 or math.sqrt(best) < 0.6):
            return part
        return None
    ic.field(px)
    return pts


def _guard(ic: Icon, c, style, part, half=4.5):
    if style == "bar":
        ic.bar(*P(c, 0, -half), *P(c, 0, half), 2.4, 2.4, part)
    elif style == "flared":
        ic.bar(*P(c, 0, -half), *P(c, 0, half), 2.2, 2.2, part)
        for sgn in (-1, 1):
            ic.poly([P(c, -1.2, sgn * half), P(c, 2.0, sgn * (half + 1.6)), P(c, 1.4, sgn * (half - 0.6))], part)
    elif style == "orbs":
        ic.bar(*P(c, 0, -half), *P(c, 0, half), 2.2, 2.2, part)
        for sgn in (-1, 1):
            ic.ellipse(*P(c, 0.4, sgn * (half + 0.6)), 1.5, 1.5, part)
    elif style == "crescent":
        pts = [P(c, 1.8 * (abs(t) / half) ** 2 * 1.6, t) for t in [half * (i / 8 - 1) * 1.2 for i in range(17)]]
        for a, b in zip(pts, pts[1:]):
            ic.bar(*a, *b, 2.2, 2.2, part)
    elif style == "wings":
        ic.bar(*P(c, 0, -2.5), *P(c, 0, 2.5), 2.6, 2.6, part)
        for sgn in (-1, 1):
            ic.poly([P(c, -1.0, sgn * 1.6), P(c, 1.0, sgn * 7.4), P(c, 3.6, sgn * 6.4), P(c, 1.6, sgn * 4.6), P(c, 2.8, sgn * 3.8), P(c, 1.0, sgn * 2.4)], part)
    elif style == "horns":
        ic.bar(*P(c, 0, -3.5), *P(c, 0, 3.5), 2.4, 2.4, part)
        for sgn in (-1, 1):
            ic.poly([P(c, -1.0, sgn * 2.6), P(c, 1.2, sgn * 3.8), P(c, 5.2, sgn * 5.8), P(c, 0.8, sgn * 5.4), P(c, -1.2, sgn * 4.4)], part)


def _pommel(ic: Icon, c, style, fit, gem):
    if style == "round":
        ic.ellipse(c[0], c[1], 1.9, 1.9, fit)
    elif style == "gem":
        ic.ellipse(c[0], c[1], 2.2, 2.2, fit)
        ic.ellipse(c[0], c[1], 1.1, 1.1, gem)
    elif style == "big":
        ic.poly([P(c, 1.0, -2.4), P(c, -1.4, -2.0), P(c, -3.0, 0), P(c, -1.4, 2.0), P(c, 1.0, 2.4)], fit)
        ic.ellipse(*P(c, -0.8, 0), 1.3, 1.3, gem)
    elif style == "spike":
        ic.poly([P(c, 1.0, -1.8), P(c, -4.0, 0), P(c, 1.0, 1.8)], fit)
        ic.ellipse(c[0], c[1], 1.4, 1.4, gem)


def _grip(ic, a, b, w, part, wrap_col=None):
    ic.bar(*a, *b, w, w, part)
    if wrap_col:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        for k in range(1, int(L / 1.6)):
            t = k * 1.6 / L
            ic.dot(a[0] + (b[0] - a[0]) * t + 0.4, a[1] + (b[1] - a[1]) * t - 0.4, wrap_col)


def build(kind: str = "sword", material: str = "iron", frame: str = "none", size: int = 48, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if material not in SET:
        raise ValueError(f"material must be one of {MATERIALS}")
    tier = MATERIALS.index(material)
    metal, fit, grip, gem, wood, rune = SET[material]
    ic = Icon(int(size))
    B, F, G, W, GR = (ic.part("blade", metal, style="blade"), ic.part("fit", fit), ic.part("gem", gem),
                      ic.part("wood", wood), ic.part("grip", grip, style="soft"))
    M5 = ramp5(RAMPS[metal])
    wrap = ramp5(RAMPS[grip])[0]
    hilt = (12.6, 19.4)                      # guard centre for swords
    if kind in ("sword", "dagger"):
        L = 17.5 if kind == "sword" else 11.5
        widths = [lambda t: 3.8 + 1.5 * math.sin(math.pi * min(1, t * 1.3)),   # bronze: leaf blade
                  4.6, 4.2, lambda t: 5.6 - 1.2 * t, 4.4]
        if kind == "dagger":
            widths = [lambda t: 3.6 + 1.6 * math.sin(math.pi * min(1, t * 1.2)), 4.0, 3.6, lambda t: 4.6 - 1.4 * t, 3.6]
        hilt = (12.6, 19.4) if kind == "sword" else (15.2, 16.8)
        pts = _blade(ic, P(hilt, 0.8, 0), L, widths[tier], B, tip=0.22 if kind == "sword" else 0.35,
                     serrate=2.4 if tier == 4 else 0.0)
        if tier >= 1:                                                         # fuller groove
            ic.color("fuller", M5[1] if tier != 4 else "#2a0a3a")
            for i in range(6, 40 if kind == "sword" else 34):
                x, y = pts[i]
                ic.set(x, y, "fuller")
        if rune and tier in (2, 4):
            for i in range(10, 44, 8):
                ic.dot(pts[i][0] + 0.8, pts[i][1] + 0.8, rune)
        if tier == 3:
            for i in (14, 22, 30):
                ic.dot(pts[i][0], pts[i][1], "#fff6b4")
        _guard(ic, hilt, ["bar", "flared", "orbs", "wings", "horns"][tier], F, half=4.5 if kind == "sword" else 3.5)
        if tier >= 2:
            ic.ellipse(hilt[0], hilt[1], 1.5, 1.5, G)
        gl = 6.4 if kind == "sword" else 5.0
        _grip(ic, P(hilt, -1.2, 0), P(hilt, -gl, 0), 2.6, GR, wrap)
        _pommel(ic, P(hilt, -gl - 1.4, 0), ["round", "round", "gem", "big", "spike"][tier], F, G)
    elif kind == "katana":
        hilt = (12.2, 19.8)
        pts = _blade(ic, P(hilt, 1.4, 0), 20.5, [3.0, 3.2, 3.2, 3.6, 3.4][tier], B, tip=0.14, curve=-1.6,
                     serrate=0.9 if tier == 4 else 0)
        ic.color("hamon", "#f4f8ff" if tier != 4 else "#c070ff")
        for i in range(8, 52):
            x, y = pts[i]
            ic.set(x + 0.9, y + 0.9, "hamon") if ic.get(x + 0.9, y + 0.9) == B else None
        tsuba = [lambda: ic.ellipse(*hilt, 2.6, 2.6, F),
                 lambda: ic.poly([P(hilt, -1, -3.2), P(hilt, 1.2, -3.2), P(hilt, 1.2, 3.2), P(hilt, -1, 3.2)], F),
                 lambda: [ic.ellipse(*P(hilt, 0, t), 1.6, 1.6, F) for t in (-1.8, 1.8)] + [ic.ellipse(*P(hilt, s_, 0), 1.6, 1.6, F) for s_ in (-1.2, 1.2)],
                 lambda: ic.ellipse(*hilt, 3.4, 3.4, F),
                 lambda: _guard(ic, hilt, "horns", F)][tier]
        tsuba()
        if tier == 3:
            for a in range(0, 360, 45):
                ic.dot(hilt[0] + 2.6 * math.cos(math.radians(a)), hilt[1] + 2.6 * math.sin(math.radians(a)), "#fff4b4")
        ic.part("habaki", "gold" if tier != 4 else "dark")
        ic.bar(*P(hilt, 0.8, 0), *P(hilt, 2.4, 0), 3.2, 3.2, "habaki")
        ic.part("tsuka", "black" if tier != 2 else "blue", style="soft")
        ic.bar(*P(hilt, -1.4, 0), *P(hilt, -9.0, 0), 3.0, 3.0, "tsuka")
        for k in range(5):
            x, y = P(hilt, -2.6 - k * 1.45, 0)
            ic.dot(x, y, "#e6e8f2" if tier != 4 else "#9a4ad0")
        ic.ellipse(*P(hilt, -9.6, 0), 1.6, 1.6, F)
        if rune and tier == 2:
            ic.dot(*pts[30], rune)
    elif kind == "axe":
        top = (22.6, 9.4)
        ic.bar(5.6, 28.4, *P(top, 1.2, 0), 2.6, 2.4, W)
        hc = P(top, -3.4, 0)

        def H(s_, t):
            return P(hc, s_, -t)                                   # blade grows to the upper-left (−V)
        # (s along the haft, t away from it); the last points are the cutting edge
        heads = [
            [(-1.4, 0.6), (1.4, 0.6), (2.2, 4.6), (1.2, 6.4), (-1.6, 6.4), (-2.4, 4.4)],
            [(-1.6, 0.6), (1.6, 0.6), (2.0, 3.0), (4.0, 7.0), (2.6, 8.4), (-1.4, 8.4), (-4.4, 6.4), (-2.2, 4.4)],
            [(-1.6, 0.6), (1.6, 0.6), (2.4, 2.8), (5.6, 6.6), (4.2, 8.8), (0, 9.4), (-4.2, 8.8), (-5.6, 6.6), (-2.4, 2.8)],
            [(-1.8, 0.6), (1.8, 0.6), (2.6, 2.6), (6.6, 5.4), (6.0, 9.6), (2.6, 8.6), (0, 10.2), (-2.6, 8.6), (-6.0, 9.6), (-6.6, 5.4), (-2.6, 2.6)],
            [(-1.6, 0.6), (1.6, 0.6), (2.6, 2.8), (6.2, 4.4), (4.6, 6.4), (6.6, 8.6), (3.4, 8.4), (1.8, 10.4), (0, 8.4), (-1.8, 10.4), (-3.4, 8.4), (-6.6, 8.6), (-4.6, 6.4), (-6.2, 4.4), (-2.6, 2.8)],
        ][tier]
        heads = [(a_ * 1.3, b_ * 1.3) for a_, b_ in heads]
        ic.part("head", metal, style="metal")
        ic.poly([H(a_, b_) for a_, b_ in heads], "head")
        if tier >= 2:                                                       # back bit / spike
            back = [(-1.4, 0), (1.4, 0), (0, 3.6)] if tier < 4 else [(-1.6, 0), (1.6, 0), (2.4, 4.8), (0, 3.0), (-2.4, 4.8)]
            ic.poly([P(hc, a_, b_) for a_, b_ in back], "head")
        ic.color("edge", M5[4])
        far = max(b_ for _, b_ in heads)
        for k in range(-14, 15):
            s_ = k * 0.45
            for t10 in range(int(far * 10) + 6, 20, -2):
                if ic.get(*H(s_, t10 / 10)) == "head":
                    ic.set(*H(s_, t10 / 10 - 0.5), "edge")
                    break
        ic.bar(*P(hc, -2.2, 0), *P(hc, 2.2, 0), 3.4, 3.4, F)
        if tier >= 2:
            ic.ellipse(*H(0, 4.2), 1.2, 1.2, G)
        if tier >= 1:
            _grip(ic, (8.6, 25.4), (12.6, 21.4), 3.0, GR, wrap)
    elif kind == "spear":
        sock = (20.2, 11.8)
        ic.bar(3.4, 28.6, *sock, 2.4, 2.4, W)
        heads = [lambda t: 1.6 + 3.4 * math.sin(math.pi * min(1, t * 1.3)),
                 lambda t: 1.8 + 3.0 * math.sin(math.pi * min(1, t * 1.3)),
                 lambda t: 1.8 + 2.4 * math.sin(math.pi * min(1, t * 1.15)),
                 lambda t: 2.2, lambda t: 1.8 + 3.6 * math.sin(math.pi * min(1, t * 1.2))]
        hl = [9.0, 9.4, 11.0, 10.0, 10.0][tier]
        if tier == 3:                                                      # golden trident
            for off in (-3.0, 0, 3.0):
                _blade(ic, P(sock, 1.0 + (0 if off == 0 else 1.4), off), hl - (0 if off == 0 else 2.5), 2.2, B, tip=0.4)
            ic.bar(*P(sock, 1.6, -3.4), *P(sock, 1.6, 3.4), 2.2, 2.2, F)
        else:
            _blade(ic, P(sock, 0.6, 0), hl, heads[tier], B, tip=0.35, serrate=1.0 if tier == 4 else 0)
        if tier == 1:                                                      # wing lugs
            ic.bar(*P(sock, -0.6, -3.2), *P(sock, -0.6, 3.2), 1.6, 1.6, F)
        if tier == 4:
            ic.poly([P(sock, 0, -2), P(sock, 3.0, -6.0), P(sock, 2.4, -1.4)], "blade")    # halberd hook
        ic.bar(*P(sock, -1.4, 0), *P(sock, 1.0, 0), 3.2, 3.2, F)
        if tier >= 2:
            ic.ellipse(*P(sock, -0.2, 0), 1.2, 1.2, G)
        ic.part("tassel", ["red", "red", "blue", "red", "purple"][tier], style="soft")
        ic.poly([P(sock, -1.8, 1.2), P(sock, -1.2, 2.6), P(sock, -6.0, 4.0), P(sock, -6.4, 2.4)], "tassel")
        if rune and tier in (2, 4):
            ic.dot(*P(sock, 5.0, 0), rune)
    elif kind == "staff":
        top = (21.6, 10.4)
        if tier == 0:
            ic.bar(5.6, 28.4, *P(top, 3.0, 0), 3.0, 2.8, W)
            ic.ellipse(*P(top, 3.4, 0), 2.6, 2.6, W)
            ic.part("leaf", "herb", style="soft")
            ic.poly([P(top, 0.5, 1.2), P(top, 2.0, 5.0), P(top, -1.0, 4.0)], "leaf")
        else:
            ic.bar(5.6, 28.4, *top, 2.8, 2.4, W)
            orb = P(top, 4.2, 0)
            r = [0, 2.6, 3.6, 3.8, 3.8][tier]
            if tier == 1:                                                    # crook
                for a in range(0, 200, 15):
                    aa = math.radians(a + 135)
                    ic.ellipse(orb[0] + 3.2 * math.cos(aa), orb[1] + 3.2 * math.sin(aa), 1.3, 1.3, W)
            if tier in (2, 3):                                               # prongs / sun ring
                for k in range(3 if tier == 2 else 8):
                    a0 = math.radians((150 + k * 85) if tier == 2 else k * 45)
                    if tier == 2:
                        ic.bar(*top, orb[0] + math.cos(a0) * 5.0, orb[1] + math.sin(a0) * 5.0, 1.8, 1.2, F)
                    else:
                        ic.poly([(orb[0] + math.cos(a0 - .25) * 4.2, orb[1] + math.sin(a0 - .25) * 4.2), (orb[0] + math.cos(a0) * 7.2, orb[1] + math.sin(a0) * 7.2),
                                 (orb[0] + math.cos(a0 + .25) * 4.2, orb[1] + math.sin(a0 + .25) * 4.2)], F)
                if tier == 3:
                    ic.ellipse(*orb, 4.8, 4.8, F)
            if tier == 4:                                                    # horns cradling the orb
                for sgn in (-1, 1):
                    ic.poly([P(top, 0, sgn * 1.2), P(top, 3.0, sgn * 5.4), P(top, 9.0, sgn * 4.2), P(top, 4.2, sgn * 3.8), P(top, 1.0, sgn * 0.2)], F)
            ic.ellipse(*orb, r, r, G)
            ic.ellipse(*top, 1.8, 1.8, F)
            if tier >= 2:
                sparkle(ic, orb[0] + 4.6, orb[1] - 4.6, rune or "#ffffff")
            if tier == 4:
                ic.dot(orb[0] - 5, orb[1] + 1, rune); ic.dot(orb[0] + 1, orb[1] - 6, rune)
    elif kind == "bow":
        A, C, Bp = (6.0, 4.0), (25.4, 6.6), (28.0, 26.0)
        pts = [((1 - t) ** 2 * A[0] + 2 * (1 - t) * t * C[0] + t * t * Bp[0], (1 - t) ** 2 * A[1] + 2 * (1 - t) * t * C[1] + t * t * Bp[1])
               for t in [i / 40 for i in range(41)]]
        ic.color("string", "#e8e4d8" if tier != 4 else "#c070ff")
        ic.line(A[0] + 0.6, A[1] + 1.4, Bp[0] - 1.4, Bp[1] - 0.6, "string")
        limb = ic.part("limb", [wood, wood, "white", "gold", "dark"][tier], style="wood" if tier < 2 else "metal")
        for i in range(40):
            t = i / 40
            w = 1.8 + [1.2, 1.6, 1.8, 2.0, 2.0][tier] * math.sin(math.pi * t)
            ic.bar(*pts[i], *pts[i + 1], w, w, limb)
        if tier >= 1:
            ic.ellipse(*pts[0], 1.5, 1.5, F); ic.ellipse(*pts[-1], 1.5, 1.5, F)
        if tier == 3:                                                        # golden wing ornaments
            for i, sgn in ((9, 1), (31, 1)):
                x, y = pts[i]
                ic.poly([(x, y), (x + 4.6, y - 1.6 if i < 20 else y + 1.0), (x + 2.6, y + 2.2 if i < 20 else y + 3.8)], F)
        if tier == 4:                                                        # bone spikes
            for i in (6, 13, 27, 34):
                x, y = pts[i]
                ic.poly([(x - 0.8, y), (x + 3.6, y - 1.6), (x + 0.8, y + 1.0)], F)
        m = pts[20]
        _grip(ic, (m[0] - 1.8, m[1] - 1.8), (m[0] + 2.0, m[1] + 2.0), 3.8, GR, wrap)
        if tier >= 2:
            ic.ellipse(*pts[13], 1.3, 1.3, G); ic.ellipse(*pts[27], 1.3, 1.3, G)
    elif kind == "hammer":
        ic.bar(5.6, 28.2, 19.6, 14.2, 2.8, 2.8, W)
        hc = (21.0, 11.0)

        def H(s_, t):
            return P(hc, s_, t)
        ic.part("head", metal, style="metal")
        hs, ht = [(3.0, 5.0), (3.8, 7.4), (3.8, 7.2), (4.4, 8.0), (4.0, 6.6)][tier]
        ic.poly([H(-hs, -ht), H(hs, -ht), H(hs, ht), H(-hs, ht)], "head")
        if tier in (3,):                                                    # flared faces
            for sgn in (-1, 1):
                ic.poly([H(-hs - 1.2, sgn * ht), H(hs + 1.2, sgn * ht), H(hs, sgn * (ht - 1.6)), H(-hs, sgn * (ht - 1.6))], "head")
        if tier >= 1:
            ic.part("band", fit)
            for t in (-ht * 0.6, ht * 0.6):
                ic.bar(*H(-hs - 0.2, t), *H(hs + 0.2, t), 1.6, 1.6, "band")
        if tier == 2:
            ic.poly([H(-1.6, -ht), H(1.6, -ht), H(0, -ht - 4.6)], "head")        # back spike
        if tier == 4:
            for s_ in (-hs, 0, hs):
                for sgn in (-1, 1):
                    ic.poly([H(s_ - 1.0, sgn * ht), H(s_ + 1.0, sgn * ht), H(s_, sgn * (ht + 3.0))], "head")
            ic.poly([H(hs, -1.2), H(hs + 3.4, 0), H(hs, 1.2)], "head")
        if tier >= 2:
            ic.ellipse(*hc, 1.7, 1.7, G)
        ic.bar(*H(-hs - 1.6, 0), *H(-hs, 0), 3.4, 3.4, F)
        if tier >= 1:
            _grip(ic, (7.4, 26.4), (11.6, 22.2), 3.2, GR, wrap)
        if rune and tier == 4:
            ic.dot(*H(0, -3), rune); ic.dot(*H(0, 3), rune)
    return emit(f"{material}-{kind}", ic, frame)
