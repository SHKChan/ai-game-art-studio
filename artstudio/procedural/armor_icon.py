"""Armour & accessory icons (防具与饰品图标), JRPG inventory style at 32 / 48 / 64 px with per-pixel lighting:
helmet, armor, shield, gauntlet, boots, cloak, ring, amulet. The `material` is a tier and changes the design —
bronze (simple / leather) → iron (plate, rivets) → mithril (fine trims, gem) → gold (ornate, wings, crown) →
dark (horns, spikes, glowing eyes). `frame` adds a rarity slot."""
from __future__ import annotations

import math

from ._icon import FRAMES, RAMPS, SIZES, Icon, emit, ramp5, sparkle

DESCRIPTION = "JRPG armour/accessory icon (32/48/64 px): 8 kinds × 5 tiers — each tier changes the design (rivets, gems, wings, horns)."
ASSET_TYPE = "item"


def FULL_BLEED(frame="none", **_):
    return frame != "none"


KINDS = ["helmet", "armor", "shield", "gauntlet", "boots", "cloak", "ring", "amulet"]
MATERIALS = ["bronze", "iron", "mithril", "gold", "dark"]
PARAMS = {"kind": {"type": "string", "default": "helmet", "enum": KINDS},
          "material": {"type": "string", "default": "iron", "enum": MATERIALS},
          "frame": {"type": "string", "default": "none", "enum": FRAMES},
          "size": {"type": "int", "default": 48, "enum": SIZES}}
SET = {  # tier → (metal, trim, cloth, gem, jewel metal, glow)
    "bronze": ("bronze", "leather", "green", "topaz", "bronze", None),
    "iron": ("steel", "iron", "red", "ruby", "silver", None),
    "mithril": ("mithril", "silver", "blue", "sapphire", "mithril", "#7ae8ff"),
    "gold": ("gold", "gold", "white", "emerald", "gold", "#fff6b4"),
    "dark": ("dark", "black", "purple", "amethyst", "dark", "#ff4a8a"),
}


def build(kind: str = "helmet", material: str = "iron", frame: str = "none", size: int = 48, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if material not in SET:
        raise ValueError(f"material must be one of {MATERIALS}")
    tier = MATERIALS.index(material)
    metal, trim, cloth, gem, jewel, glow = SET[material]
    ic = Icon(int(size))
    m = ic.part("metal", metal, style="metal")
    t = ic.part("trim", trim, style="metal" if trim not in ("leather",) else "soft")
    c = ic.part("cloth", cloth, style="soft")
    g = ic.part("gem", gem)
    lea = ic.part("leather", "leather", style="soft")
    ic.color("void", "#0e0a14")
    if kind == "helmet":
        if tier == 0:                                               # leather-lined bronze cap with nasal bar
            ic.ellipse(16, 16, 10, 9.6, m)
            ic.rect(6, 16, 26, 20, m)
            ic.rect(5, 19, 27, 22, lea)
            ic.rect(15, 16, 17, 26, m)
            for x in (9, 23):
                ic.dot(x, 20.5, ramp5(RAMPS["leather"])[0])
        else:
            if tier == 3:                                           # crown band + plume
                ic.poly([(14, 2), (19, 1), (24, 3), (21, 5), (17, 6)], c)
            if tier == 1:
                ic.poly([(15, 3), (17, 3), (22, 1), (25, 4), (21, 6), (17, 7)], c)          # red plume
            ic.ellipse(16, 15, 9.4, 9.6, m)
            ic.rect(7, 15, 25, 26, m)
            ic.poly([(7, 24), (25, 24), (22, 28), (10, 28)], m)
            ic.rect(9, 14, 23, 16, "void")
            ic.rect(15, 16, 17, 23, "void")
            ic.rect(15, 5, 17, 13, t)
            if tier >= 2:
                ic.rect(7, 18, 8, 26, t); ic.rect(24, 18, 25, 26, t)
            if tier == 2:                                           # wings at the temples
                for sgn in (-1, 1):
                    x0 = 16 + sgn * 9
                    ic.poly([(x0, 12), (x0 + sgn * 6, 5), (x0 + sgn * 5, 10), (x0 + sgn * 6.5, 12), (x0 + sgn * 4, 14), (x0, 16)], t)
                ic.ellipse(16, 10, 1.6, 1.6, g)
            if tier == 3:
                for x in (10, 16, 22):
                    ic.poly([(x - 2, 9), (x, 4 if x == 16 else 6), (x + 2, 9)], t)
                ic.rect(8, 9, 24, 11, t)
                ic.ellipse(16, 10, 1.4, 1.4, g)
            if tier == 4:                                           # horns + glowing eyes
                for sgn in (-1, 1):
                    ic.poly([(16 + sgn * 6, 9), (16 + sgn * 12, 6), (16 + sgn * 14, 0.5), (16 + sgn * 11, 9), (16 + sgn * 8, 12)], t)
                ic.dot(12, 15, glow); ic.dot(20, 15, glow)
            if tier == 1:
                for y in (19, 21):
                    ic.dot(12, y, ramp5(RAMPS[metal])[0]); ic.dot(20, y, ramp5(RAMPS[metal])[0])
    elif kind == "armor":
        if tier == 0:                                               # leather jerkin with bronze studs
            ic.poly([(9, 6), (23, 6), (26, 12), (23, 27), (9, 27), (6, 12)], lea)
            ic.ellipse(16, 6.4, 4, 2.4, "void")
            ic.rect(15, 9, 17, 26, t)
            for x, y in ((11, 12), (21, 12), (11, 17), (21, 17), (11, 22), (21, 22)):
                ic.ellipse(x, y, 0.9, 0.9, m)
        else:
            ic.poly([(9, 7), (23, 7), (25, 13), (23, 22), (21, 27), (11, 27), (9, 22), (7, 13)], m)
            ic.ellipse(16, 6.6, 4.4, 2.6, "void")
            r = [0, 4.4, 4.6, 5.0, 4.6][tier]
            ic.ellipse(7.4, 10.6, r, r * 0.9, t); ic.ellipse(24.6, 10.6, r, r * 0.9, t)
            if tier == 4:
                for x0, sgn in ((7.4, -1), (24.6, 1)):
                    for dy in (-3, 1):
                        ic.poly([(x0 - 1.4, 9 + dy), (x0 + sgn * 6, 7 + dy), (x0 + 1.4, 11 + dy)], t)
            ic.rect(9, 21, 23, 23, lea)
            ic.part("buckle", "gold")
            ic.rect(15, 20, 17, 24, "buckle")
            ic.line(16, 10, 16, 19, t)
            if tier >= 2:
                ic.ellipse(16, 14, 1.8, 1.8, g)
            if tier == 3:                                           # sun emblem + collar
                for a in range(0, 360, 45):
                    ic.dot(16 + 3.6 * math.cos(math.radians(a)), 14 + 3.6 * math.sin(math.radians(a)), "#fff4b4")
                ic.poly([(11, 5), (21, 5), (19, 9), (13, 9)], c)
            if tier == 4:
                ic.dot(13, 12, glow); ic.dot(19, 12, glow)
            if tier == 1:
                for x, y in ((11, 9), (21, 9), (11, 19), (21, 19)):
                    ic.dot(x, y, ramp5(RAMPS[metal])[4])
            ic.line(11, 25, 21, 25, lea)
    elif kind == "shield":
        if tier == 0:                                               # round wooden buckler, bronze rim and boss
            ic.part("wood", "wood")
            ic.ellipse(16, 16, 12, 12, m)
            ic.ellipse(16, 16, 10, 10, "wood")
            ic.ellipse(16, 16, 3, 3, m)
            for a in range(0, 360, 60):
                ic.dot(16 + 7 * math.cos(math.radians(a)), 16 + 7 * math.sin(math.radians(a)), ramp5(RAMPS["wood"])[0])
        else:
            def heater(inset, top=4.0, bottom=29.0):
                return ([(5.5 + inset, top + inset), (26.5 - inset, top + inset), (26.5 - inset, 15)] +
                        [(16 + (10.5 - inset) * math.cos(a), 15 + (bottom - 15 - inset) * math.sin(a)) for a in [math.pi * k / 16 for k in range(17)]] +
                        [(5.5 + inset, 15)])
            if tier == 2:                                           # kite
                ic.poly([(16, 2), (27, 8), (24, 20), (16, 30), (8, 20), (5, 8)], t)
                ic.poly([(16, 4.5), (24.5, 9), (22, 19), (16, 27), (10, 19), (7.5, 9)], c)
                ic.ellipse(16, 13, 3, 3, t); ic.ellipse(16, 13, 1.8, 1.8, g)
            else:
                ic.poly(heater(0), t)
                ic.poly(heater(2.2), c if tier != 4 else m)
                if tier == 1:
                    ic.rect(15, 7, 17, 24, t); ic.rect(9, 12, 23, 14, t)
                if tier == 3:                                       # wings + gem
                    for sgn in (-1, 1):
                        ic.poly([(16 + sgn * 9, 6), (16 + sgn * 15.5, 2), (16 + sgn * 14, 7), (16 + sgn * 15.5, 9), (16 + sgn * 11, 12)], t)
                    ic.poly([(16, 7), (20, 13), (16, 21), (12, 13)], t)
                    ic.ellipse(16, 14, 2.2, 2.2, g)
                if tier == 4:                                       # eye emblem + spikes
                    for x in (5.5, 16, 26.5):
                        ic.poly([(x - 1.6, 4.4), (x, 0.5), (x + 1.6, 4.4)], t)
                    ic.ellipse(16, 15, 5, 3, "void")
                    ic.ellipse(16, 15, 2, 2, g)
                    ic.dot(16, 15, glow)
    elif kind == "gauntlet":
        cuff = [(10, 19), (22, 19), (23, 28), (9, 28)]
        main = lea if tier == 0 else m
        ic.poly(cuff, main)
        ic.rect(9, 25, 23, 26, t)
        ic.poly([(9, 11), (22, 11), (23, 19), (9, 20)], main)
        for i, (x, top) in enumerate(((10, 6), (13.4, 4), (16.8, 4.4), (20.2, 6.4))):
            f = ic.part(f"f{i}", "leather" if tier == 0 else metal, style="soft" if tier == 0 else "metal")
            ic.rect(x, top, x + 2.4, 12, f)
            if tier == 4:
                ic.poly([(x, top), (x + 1.2, top - 3.4), (x + 2.4, top)], f)
        thumb = ic.part("thumb", "leather" if tier == 0 else metal, style="soft" if tier == 0 else "metal")
        ic.bar(9.6, 17, 5.6, 11.2, 3.0, 2.6, thumb)
        if tier >= 1:
            ic.rect(9, 11, 23, 12, t)
        if tier >= 2:
            ic.ellipse(16, 15.6, 1.8, 1.8, g)
        if tier == 3:
            ic.poly([(23, 20), (29, 16), (28, 21), (29.5, 23), (23, 25)], t)
        if tier == 4:
            for y in (20.5, 23.5):
                ic.poly([(23, y - 1), (27, y), (23, y + 1)], t)
    elif kind == "boots":
        top = 4 if tier != 0 else 12
        main = lea if tier == 0 else m
        ic.poly([(9, top), (19, top), (19, 20), (25, 22), (27.5, 25), (27.5, 27), (9, 27)], main)
        ic.rect(9, 26, 27, 28, lea)
        if tier == 0:
            ic.rect(8, 12, 20, 14, c)                               # cloth wrap top
            for y in (17, 20):
                ic.line(10, y, 18, y - 1, t)
        else:
            ic.rect(8, 4, 20, 7, t)
            ic.rect(9, 12, 19, 13, lea); ic.rect(9, 17, 19, 18, lea)
            if tier >= 2:
                ic.ellipse(14, 9.6, 1.4, 1.4, g)
            if tier == 3:                                           # winged heel
                ic.poly([(9, 10), (2, 5), (4, 10), (1.5, 12), (5, 14), (9, 16)], t)
            if tier == 4:
                for y in (8, 14, 20):
                    ic.poly([(9, y - 1.2), (4.6, y), (9, y + 1.2)], t)
                ic.poly([(26, 24), (30.5, 25.5), (27.5, 27)], t)
    elif kind == "cloak":
        hem_wave = [(28 - k * 1.5, 27 + (1.5 if k % 4 in (1, 2) else 0)) for k in range(17)]
        if tier == 4:                                              # tattered
            hem_wave = [(28 - k * 1.5, 27 + (3.0 if k % 3 == 1 else -1.0)) for k in range(17)]
        ic.poly([(11, 5), (21, 5), (24, 12), (28, 27)] + hem_wave + [(4, 27), (8, 12)], c)
        if tier == 0:                                               # hood
            ic.ellipse(16, 6.6, 6.4, 4.6, c)
            ic.ellipse(16, 7.4, 3.6, 2.6, "void")
        lin = ic.part("lining", "gold" if tier == 3 else ("white" if tier == 2 else trim), style="soft" if tier in (0, 2) else "metal")
        if tier >= 1:
            ic.poly([(11, 5), (21, 5), (19, 9), (13, 9)], lin)
        if tier == 3:                                               # fur collar + embroidered hem
            for x in range(9, 24, 2):
                ic.ellipse(x, 6.4, 1.6, 1.6, ic.part("fur", "white", style="round"))
            for k in range(2, 15, 2):
                x, y = hem_wave[k]
                ic.dot(x, y - 1.6, "#ffe07a")
        if tier == 2:
            for k in range(1, 16, 3):
                x, y = hem_wave[k]
                ic.dot(x, y - 1.2, "#bfe8ff")
        ic.part("fold", [ramp5(RAMPS[cloth])[0]] * 4, flat=True)
        for x0, x1 in ((14, 11), (18, 21), (16, 16)):
            ic.line(x0, 11, x1, 24, "fold")
        if tier >= 1:
            ic.part("clasp", jewel, style="metal")
            ic.ellipse(16, 8.4, 2.6, 2.6, "clasp")
            ic.ellipse(16, 8.4, 1.3, 1.3, g)
    elif kind == "ring":
        band = ic.part("band", jewel, style="metal")
        ic.ellipse(16, 20, 9, 7.6, band)
        ic.ellipse(16, 20.6, 6.2, 4.8, None)
        if tier == 0:
            for a in range(200, 341, 35):
                ic.dot(16 + 7.6 * math.cos(math.radians(a)), 20 + 6.2 * math.sin(math.radians(a)), ramp5(RAMPS[jewel])[0])
        elif tier == 1:
            ic.ellipse(16, 12.6, 2.4, 2.0, g)
        elif tier == 2:
            ic.poly([(12, 13), (20, 13), (19, 9), (13, 9)], band)
            ic.poly([(12.2, 8), (19.8, 8), (21.4, 4.6), (16, 2.4), (10.6, 4.6)], g)
        elif tier == 3:
            ic.poly([(10, 13), (22, 13), (23, 7), (20, 10), (16, 5), (12, 10), (9, 7)], band)
            ic.ellipse(16, 9.4, 3, 3, g)
            ic.ellipse(11, 11.6, 1.2, 1.2, ic.part("g2", "ruby")); ic.ellipse(21, 11.6, 1.2, 1.2, "g2")
            sparkle(ic, 25, 4, "#ffffff")
        else:                                                       # claw setting
            for sgn in (-1, 1):
                ic.poly([(16 + sgn * 2, 13), (16 + sgn * 5.6, 5), (16 + sgn * 3.2, 7.4), (16 + sgn * 4, 11)], band)
            ic.ellipse(16, 9.4, 3.0, 3.0, g)
            ic.dot(16, 9, glow)
    elif kind == "amulet":
        chain = ic.part("chain", jewel, style="metal") if tier > 0 else ic.part("chain", "leather", style="soft")
        for k in range(10):
            u = k / 9
            for side in (-1, 1):
                x, y = 16 + side * (9.5 * (1 - u) ** 1.1), 3 + 10 * u
                ic.ellipse(x, y, 1.0, 1.0, chain)
        fr = ic.part("frame", jewel, style="metal")
        if tier == 0:                                               # fang + beads
            ic.part("fang", "bone", style="round")
            ic.poly([(13.6, 15), (18.4, 15), (16.6, 28), (15.4, 28)], "fang")
            for x in (11, 21):
                ic.ellipse(x, 13.4, 1.4, 1.4, g)
        elif tier == 1:
            ic.ellipse(16, 20, 6, 6, fr)
            ic.ellipse(16, 20, 3.2, 3.2, g)
        elif tier == 2:
            ic.ellipse(16, 15, 1.6, 1.6, fr)
            ic.poly([(16, 15.5), (23, 21), (16, 30), (9, 21)], fr)
            ic.poly([(16, 18.2), (20.4, 21.4), (16, 27), (11.6, 21.4)], g)
        elif tier == 3:                                             # sun disc
            for a in range(0, 360, 30):
                aa = math.radians(a)
                ic.poly([(16 + 4.6 * math.cos(aa - .2), 21 + 4.6 * math.sin(aa - .2)), (16 + 8.4 * math.cos(aa), 21 + 8.4 * math.sin(aa)),
                         (16 + 4.6 * math.cos(aa + .2), 21 + 4.6 * math.sin(aa + .2))], fr)
            ic.ellipse(16, 21, 5.2, 5.2, fr)
            ic.ellipse(16, 21, 2.8, 2.8, g)
        else:                                                       # eye
            ic.poly([(7, 21), (12, 16), (20, 16), (25, 21), (20, 26), (12, 26)], fr)
            ic.ellipse(16, 21, 4.6, 3.2, "void")
            ic.ellipse(16, 21, 2.2, 2.2, g)
            ic.dot(16, 21, glow)
    return emit(f"{material}-{kind}", ic, frame)
