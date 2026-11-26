"""Holy judgment (圣光审判): top-down ground skill. A golden magic circle inscribes itself, a pillar of light falls
from the sky, a cross of light flashes across the cells and motes of light drift up. Plays once."""
from __future__ import annotations

import math

from ._ground import Ground
from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Top-down holy judgment for a grid: magic circle inscribes, pillar of light falls, cross flash, rising motes."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5},
          "color": {"type": "string", "default": "holy", "enum": ["holy", "sun", "moon"]}}
# 0 outline 1 deep 2 mid 3 bright 4 pale 5 white
PALETTES = {
    "holy": ["#3a2a0a", "#b07a14", "#e8b830", "#ffe070", "#fff6c4", "#ffffff"],
    "sun": ["#3a120a", "#c0441a", "#f08a2a", "#ffc65a", "#fff0c0", "#ffffff"],
    "moon": ["#141c34", "#4a5a90", "#8a9ad0", "#c4d0f4", "#eef2ff", "#ffffff"],
}
# (circle draw 0..1, beam width 0..1, cross 0..1, circle brightness 0..2, motes phase or None)
FRAMES = [(0.35, 0, 0, 1, None), (0.7, 0, 0, 1, None), (1, 0, 0, 1, None), (1, 0.25, 0, 1, None), (1, 1, 0, 2, None),
          (1, 0.8, 1, 2, None), (1, 0.5, 0.6, 2, 0.1), (1, 0.25, 0.25, 1, 0.3), (1, 0.1, 0, 1, 0.5), (0.8, 0, 0, 1, 0.7),
          (0.5, 0, 0, 0, 0.85)]
DUR = [70, 60, 70, 40, 50, 60, 70, 80, 90, 100, 120]


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=48)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, color: str = "holy", **_):
    gr = _ground(tiles)
    s, R, cx, cy = gr.s, gr.R, gr.cx, gr.cy
    OUT, D, M, B, P, W = range(6)
    d = DocBuilder(f"holy-judgment-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_circle, l_beam, l_fx = d.layer("magic circle"), d.layer("light pillar"), d.layer("cross & motes")
    d.add_frames(len(FRAMES) - 1, 80)

    def circle(g: Grid, draw, bright):
        col = [D, M, B][bright]
        hi = [M, B, W][bright]
        for rr, c in ((R * 0.96, hi), (R * 0.88, col), (R * 0.5, col)):
            n = int(2 * math.pi * rr * 1.2)
            for k in range(int(n * min(1, draw))):
                a = -math.pi / 2 + 2 * math.pi * k / n
                g.set(cx + math.cos(a) * rr, cy + math.sin(a) * rr, c)
        if draw >= 0.6:                                         # hexagram between the rings
            for tri in (0, 1):
                pts = [(cx + math.cos(-math.pi / 2 + tri * math.pi / 3 + j * 2 * math.pi / 3) * R * 0.88,
                        cy + math.sin(-math.pi / 2 + tri * math.pi / 3 + j * 2 * math.pi / 3) * R * 0.88) for j in range(3)]
                for j in range(3):
                    g.line(*pts[j], *pts[(j + 1) % 3], col)
        if draw >= 1:                                           # rune ticks on the outer band
            for k in range(24):
                a = 2 * math.pi * k / 24
                r0 = R * 0.9 + 1
                g.set(cx + math.cos(a) * r0, cy + math.sin(a) * r0, hi if k % 2 else col)
            g.ellipse(cx, cy, 2 * s + .5, 2 * s + .5, hi)

    for fi, (draw, beam, cross, bright, motes) in enumerate(FRAMES):
        ci, bm, fx = gr.grid(), gr.grid(), gr.grid()
        if bright == 2:
            ci.ellipse(cx, cy, R * 0.9, R * 0.9, lambda x, y: M if bayer4(x, y) < 0.3 else None)
        circle(ci, draw, bright)
        if beam:
            w = R * 0.45 * beam
            for y in range(0, int(cy) + 1):
                v = y / cy
                ww = w * (0.7 + 0.3 * v)
                for x in range(int(cx - ww) - 1, int(cx + ww) + 2):
                    q = abs(x + .5 - cx) / max(ww, .5)
                    if q <= 1:
                        bm.set(x, y, W if q < 0.45 else (P if q < 0.75 else (B if q < 0.92 else M)))
            bm.ellipse(cx, cy, w * 1.4, w * 1.1, lambda x, y: W if math.hypot((x - cx) / 1.4, (y - cy) / 1.1) < w * 0.8 else P)
        if cross:
            arm, th = R * (0.6 + 0.4 * cross), (2.5 * cross + 1) * s
            for (dx, dy) in ((1, 0), (0, 1)):
                for t in range(-int(arm), int(arm) + 1):
                    for u in range(-int(th), int(th) + 1):
                        x, y = cx + dx * t + dy * u, cy + dy * t + dx * u
                        fade = abs(t) / arm
                        if bayer4(x, y) > fade ** 2:
                            fx.set(x, y, W if abs(u) < th * 0.5 else B)
        if motes is not None:
            for k in range(10 + 4 * tiles):
                ph = motes + 0.25 * hash01(k, 1)
                if ph > 1:
                    continue
                x = cx + (hash01(k, 2) - .5) * R * 1.7 + math.sin(ph * 8 + k) * 2
                y = cy + (hash01(k, 3) - .5) * R * 1.2 - ph * 40 * s
                c = W if ph < .4 else (B if ph < .7 else M)
                fx.set(x, y, c)
                if ph < 0.5 and k % 3 == 0:
                    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        fx.set(x + ddx, y + ddy, B)
        d.paint(ci, l_circle, fi)
        d.paint(bm, l_beam, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, DUR[fi])
    d.tag("circle", 0, 2)
    d.tag("judgment", 3, len(FRAMES) - 1)
    return d.calls
