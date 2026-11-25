"""64x64 fantasy health potion: round flask, red liquid with sphere shading, cork, tie, glass highlights.
Optional bubbling loop (frames > 1)."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, ramp_pick

DESCRIPTION = "Round-bottom fantasy potion flask (health red by default) with layered glass, liquid, cork and highlights."
ASSET_TYPE = "item"
PARAMS = {"size": {"type": "int", "default": 64}, "frames": {"type": "int", "default": 1, "max": 12},
          "liquid": {"type": "string", "default": "red", "enum": ["red", "blue", "green", "purple"]}}

LIQUIDS = {
    "red": ["#4a0a24", "#8c1533", "#d42a3c", "#ff6655", "#ffb8a0"],
    "blue": ["#0d1a4a", "#1d3e8c", "#2f78d4", "#5fc0ff", "#c4f0ff"],
    "green": ["#0b3320", "#16663a", "#2ea84e", "#7ee070", "#d6ffb8"],
    "purple": ["#2a0d4a", "#561d8c", "#8d34d4", "#c477ff", "#ecc4ff"],
}


def build(size: int = 64, frames: int = 1, liquid: str = "red", **_):
    s = size / 64.0
    L = LIQUIDS[liquid]
    pal = ["#160d22", "#33405e", "#6f86ab", "#b9d6ea", "#ffffff"] + L + ["#4d2a18", "#87532d", "#c48a52", "#e8c45a", "#9c6a24"]
    O, GD, GM, GL, W = 0, 1, 2, 3, 4
    LQ = [5, 6, 7, 8]
    LGLOW = 9
    CD, CM, CL, TG, TD = 10, 11, 12, 13, 14
    d = DocBuilder("health-potion", size, size)
    d.palette(pal)
    l_outline = d.layer("outline")
    l_glass = d.layer("glass")
    l_liquid = d.layer("liquid")
    l_bubbles = d.layer("bubbles")
    l_cork = d.layer("cork")
    l_shine = d.layer("highlights")
    cx, cy, r = 32 * s, 41 * s, 17.5 * s
    neck = (26.5 * s, 13 * s, 37.5 * s, 25 * s)
    lx, ly = -0.6, -0.75  # light from top-left
    n = math.hypot(lx, ly); lx, ly = lx / n, ly / n

    def in_body(x, y):
        return (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r

    def in_neck(x, y):
        return neck[0] <= x + .5 <= neck[2] and neck[1] <= y + .5 <= neck[3]

    silhouette = Grid(size, size)
    silhouette.field(lambda x, y: 1 if in_body(x, y) or in_neck(x, y) else None)
    rim = Grid(size, size)
    rim.rect(round(24.5 * s), round(12 * s), round(38.5 * s), round(14.5 * s), GM)
    rim.rect(round(25 * s), round(12 * s), round(38 * s), round(12 * s), GL)
    for fi in range(frames):
        ph = 2 * math.pi * fi / max(1, frames)
        surf = 31.5 * s + (0.6 * math.sin(ph) if frames > 1 else 0)
        glass, liq, bub, shine = Grid(size, size), Grid(size, size), Grid(size, size), Grid(size, size)

        def shade(x, y):
            nx, ny = (x + .5 - cx) / r, (y + .5 - cy) / r
            return nx, ny, max(0.0, 1 - nx * nx - ny * ny) ** .5

        def glass_px(x, y):
            if not (in_body(x, y) or in_neck(x, y)):
                return None
            if in_body(x, y):
                nx, ny, nz = shade(x, y)
                edge = math.hypot(nx, ny)
                if edge > 0.88:
                    return GD
                return GM
            # neck: darker sides, light column
            if x + .5 < neck[0] + 1.5 or x + .5 > neck[2] - 1.5:
                return GD
            return GL if neck[0] + 2.5 < x + .5 < neck[0] + 4 else GM
        glass.field(glass_px)
        glass.merge(rim)

        def liq_px(x, y):
            if not in_body(x, y):
                return None
            wave = surf + 0.9 * math.sin((x / (6 * s)) + ph) if frames > 1 else surf + (0.5 if (x // 3) % 2 else 0)
            if y + .5 < wave:
                return None
            nx, ny, nz = shade(x, y)
            if math.hypot(nx, ny) > 0.86:
                return None  # leave glass rim visible
            lum = 0.55 * (-(nx * lx + ny * ly)) + 0.45 * nz
            lum = lum * 0.85 + 0.12
            if y + .5 < wave + 1.6:
                return LQ[3]  # bright meniscus line
            return ramp_pick(lum, LQ, x, y, 0.4)
        liq.field(liq_px)
        # inner glow pocket
        liq.ellipse(cx + 4 * s, cy + 3 * s, 5 * s, 4 * s, lambda x, y: LQ[3] if liq.get(x, y) is not None else None)
        liq.ellipse(cx + 5 * s, cy + 4 * s, 2.5 * s, 2 * s, lambda x, y: LGLOW if liq.get(x, y) is not None else None)
        # bubbles rise through the loop
        for bi, (bx, by0, br) in enumerate([(26, 50, 1.6), (36, 47, 1.1), (31, 54, 1.0), (39, 52, 1.4)]):
            t = ((fi / max(1, frames)) + bi * 0.27) % 1.0 if frames > 1 else 0.3 + bi * 0.15
            by = (by0 - t * 18) * s
            if by < surf + 2 * s:
                continue
            bub.ellipse(bx * s, by, br * s + .2, br * s + .2, LQ[3])
            bub.set(bx * s - br * s * .5, by - br * s * .5, W)
        # glass highlights: curved specular arc + spots
        for a in range(205, 252, 3):
            rr = r * 0.74
            shine.set(cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)), W)
            shine.set(cx + (rr - 1) * math.cos(math.radians(a)), cy + (rr - 1) * math.sin(math.radians(a)), GL)
        shine.ellipse(cx - 9 * s, cy - 2 * s, 1.2 * s, 1.6 * s, W)
        shine.set(cx + 12 * s, cy + 6 * s, GL); shine.set(cx + 11 * s, cy + 8 * s, GL)
        shine.rect(neck[0] + 2, neck[1] + 3, neck[0] + 2, neck[3] - 2, W)
        if fi == 0:
            d.paint(glass, l_glass, 0, frames - 1 if frames > 1 else None)
        d.paint(liq, l_liquid, fi, replace=fi > 0)
        d.paint(bub, l_bubbles, fi, replace=fi > 0)
        if fi == 0:
            d.paint(shine, l_shine, 0, frames - 1 if frames > 1 else None)
        if fi == 0 and frames > 1:
            d.add_frames(frames - 1, 120, copy_from=0)
    # cork + tie (static)
    cork = Grid(size, size)
    cork.polygon([(27.5 * s, 4 * s), (36.5 * s, 4 * s), (35.5 * s, 13 * s), (28.5 * s, 13 * s)], CM)
    cork.field(lambda x, y: (CL if x + .5 < 30.5 * s else (CD if x + .5 > 34 * s else None)) if cork.get(x, y) is not None else None)
    cork.rect(round(28 * s), round(4 * s), round(36 * s), round(4 * s), CL)
    for (x, y) in [(31, 7), (33, 10), (30, 11)]:
        cork.set(x * s, y * s, CD)
    tie = Grid(size, size)
    tie.rect(round(26 * s), round(18 * s), round(38 * s), round(19 * s), TG)
    tie.rect(round(26 * s), round(19 * s), round(38 * s), round(19 * s), TD)
    tie.polygon([(36 * s, 19 * s), (41 * s, 25 * s), (39 * s, 26 * s), (35 * s, 20 * s)], TG)
    tie.polygon([(37 * s, 19 * s), (39.5 * s, 27 * s), (38 * s, 28 * s), (36 * s, 20 * s)], TD)
    cork.merge(tie)
    last = frames - 1 if frames > 1 else None
    d.paint(cork, l_cork, 0, last)
    # outline around the union silhouette
    sil = Grid(size, size)
    sil.field(lambda x, y: 1 if in_body(x, y) or in_neck(x, y) else None)
    sil.merge(rim); sil.merge(cork)
    ol = sil.copy()
    ol.outline(O)
    out = Grid(size, size)
    out.field(lambda x, y: O if ol.get(x, y) == O and sil.get(x, y) is None else None)
    d.paint(out, l_outline, 0, last)
    if frames > 1:
        d.tag("bubble", 0, frames - 1)
    return d.calls
