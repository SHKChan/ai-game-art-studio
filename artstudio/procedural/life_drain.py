"""Life drain (生命汲取): a curse sigil marks the target cell, ribbons of life essence are torn out and spiral up into
a pulsing orb above, which then darts away (towards the caster). Plays once."""
from __future__ import annotations

import math

from ._ground import Ground, contour
from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Life drain on a grid cell: curse sigil, essence ribbons spiral up into a pulsing orb that darts away."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 1, "min": 1, "max": 3},
          "color": {"type": "string", "default": "blood", "enum": ["blood", "soul", "mana"]}}
# 0 outline 1 deep 2 mid 3 bright 4 pale 5 white
PALETTES = {
    "blood": ["#1a0408", "#6a0c1a", "#b8182e", "#f04050", "#ff9aa0", "#fff0f0"],
    "soul": ["#04141a", "#0c4a5a", "#1a8ea0", "#3ad8e0", "#a8fcff", "#f4ffff"],
    "mana": ["#060c26", "#16307a", "#2a5ad0", "#5a9aff", "#b8d4ff", "#f4f8ff"],
}
STAGES = ["mark", "mark", "pull", "pull", "pull", "pull", "pull", "orb", "dart", "dart"]
DUR = [90, 80, 70, 70, 70, 70, 70, 90, 60, 80]


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=56 * t)


def pivot(tiles: int = 1, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 1, color: str = "blood", **_):
    tiles = int(tiles)
    gr = _ground(tiles)
    s, R, cx, cy = gr.s * 3, gr.R, gr.cx, gr.cy
    OUT, D, M, B, P, W = range(6)
    d = DocBuilder(f"life-drain-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_mark, l_rib, l_orb = d.layer("sigil"), d.layer("essence"), d.layer("orb")
    d.add_frames(len(STAGES) - 1, 80)
    ox, oy = cx, gr.head * 0.45 + 4                               # orb position

    def sigil(g: Grid, bright):
        r = R * 0.8
        for k in range(int(30 * s)):
            a = 2 * math.pi * k / int(30 * s)
            g.set(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, B if bright else M)
        for k in range(4):                                         # inward hooks
            a = k * math.pi / 2 + math.pi / 4
            g.line(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, cx + math.cos(a + .6) * r * .35, cy + math.sin(a + .6) * r * .28, D if not bright else M)
        g.ellipse(cx, cy, 2 * s, 1.6 * s, B if bright else D)

    def orb(g: Grid, r, x, y):
        for yy in range(int(y - r) - 1, int(y + r) + 2):
            for xx in range(int(x - r) - 1, int(x + r) + 2):
                dx, dy = xx + .5 - x, yy + .5 - y
                q = math.hypot(dx, dy) / r
                if q <= 1:
                    lit = -(dx + dy) / (r * 1.41)
                    g.set(xx, yy, W if q < 0.3 and lit > -0.1 else (P if lit > 0.3 else (B if lit > -0.3 else M)))
        contour(g, OUT)

    for fi, st in enumerate(STAGES):
        mk, rb, ob = gr.grid(), gr.grid(), gr.grid()
        if st in ("mark", "pull", "orb"):
            sigil(mk, fi % 2 == 1)
        if st == "mark" and fi == 1:
            mk.ellipse(cx, cy, R * 0.5, R * 0.4, lambda x, y: D if bayer4(x, y) < 0.4 else None)
        if st == "pull":
            t = (fi - 2) / 5
            for k in range(3 + tiles):                             # ribbons: helices from ground to orb
                a0 = 2 * math.pi * k / (3 + tiles)
                for i in range(40):
                    u = i / 39
                    ph = u - t * 0.6
                    if not (0.05 + 0.15 * (1 - t) * 0 <= (u + t) % 1.2 <= 1.0):
                        continue
                    yv = cy + (oy - cy) * u
                    rr = R * 0.7 * (1 - u) ** 0.8 + 1
                    a = a0 + u * 7 + t * 5
                    x = cx + (ox - cx) * u + math.cos(a) * rr
                    y = yv + math.sin(a) * rr * 0.3
                    front = math.sin(a) >= 0
                    c = B if front else M
                    rb.set(x, y, c)
                    rb.set(x + (1 if front else 0), y + 1, D if not front else M)
                    if front and (i + int(t * 10)) % 5 == 0:
                        rb.set(x, y - 1, P)
            for k in range(6):                                     # droplets snapped off the target
                ph = (t + hash01(k, 3)) % 1
                rb.set(cx + (hash01(k, 4) - .5) * R, cy - ph * (cy - oy) * 0.8, B if ph < .6 else M)
            orb(ob, (2 + 4.5 * t) * s + 1, ox, oy)
        if st == "orb":
            orb(ob, 7.5 * s + 1, ox, oy)
            for k in range(8):
                a = k * math.pi / 4
                ob.set(ox + math.cos(a) * 10 * s, oy + math.sin(a) * 10 * s, P)
        if st == "dart":
            q = fi - 7                                              # 1, 2
            y = oy - q * 16 * s
            orb(ob, (6 - 2 * q) * s + 1, ox, y)
            for i in range(int(10 * s * q)):
                ob.set(ox + (hash01(i, 1) - .5) * 3, y + 6 * s + i, B if i < 5 else M)
            sigil(mk, False) if q == 1 else None
        d.paint(mk, l_mark, fi)
        d.paint(rb, l_rib, fi)
        d.paint(ob, l_orb, fi)
        d.duration(fi, DUR[fi])
    d.tag("drain", 0, len(STAGES) - 1)
    return d.calls
