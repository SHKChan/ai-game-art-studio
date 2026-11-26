"""Fire pillar (火柱): top-down ground skill on one cell (or more). A rune circle flares, a roaring column of fire
erupts and churns (seamless loop), then collapses into embers. Tags: rise / burn (loop) / end."""
from __future__ import annotations

import math

from ._ground import Ground, loop_noise
from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Top-down fire pillar: rune circle flares, a churning column of fire erupts (loop), collapses to embers."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 1, "min": 1, "max": 3},
          "color": {"type": "string", "default": "fire", "enum": ["fire", "azure", "violet"]}}
# 0 outline 1 deep 2 mid 3 bright 4 pale 5 white 6 rune 7 scorch
PALETTES = {
    "fire": ["#1e0a08", "#a8200e", "#ee5a18", "#ffa82a", "#ffe58a", "#fffbe8", "#ff7a2a", "#2a1610"],
    "azure": ["#06102a", "#1440b0", "#1e8ae8", "#52d0ff", "#b8f2ff", "#f6feff", "#3ab0ff", "#101a2c"],
    "violet": ["#140620", "#5a14a0", "#9a34e0", "#d070ff", "#f2c6ff", "#fff4ff", "#b050ff", "#1c1028"],
}
STAGES = ["rune", "rune", "rise", "burn", "burn", "burn", "burn", "burn", "burn", "end", "end", "end"]
DUR = [80, 70, 60, 80, 80, 80, 80, 80, 80, 80, 100, 130]


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=64 * t)


def pivot(tiles: int = 1, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 1, color: str = "fire", **_):
    tiles = int(tiles)
    gr = _ground(tiles)
    s, R, cx, cy = gr.s * 3, gr.R, gr.cx, gr.cy       # s = 1 for one tile
    OUT, F0, F1, F2, F3, F4, RUNE, SC = range(8)
    d = DocBuilder(f"fire-pillar-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_ground, l_col, l_fx = d.layer("rune & scorch"), d.layer("pillar"), d.layer("sparks")
    d.add_frames(len(STAGES) - 1, 80)
    top = 4

    def rune(g: Grid, r, bright):
        for k in range(int(40 * s)):
            a = 2 * math.pi * k / int(40 * s)
            g.set(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, F3 if bright else RUNE)
            if k % 5 == 0:
                g.set(cx + math.cos(a) * (r - 2), cy + math.sin(a) * (r - 2) * 0.8, RUNE)
        for k in range(3):                                             # inner triangle
            a0, a1 = -math.pi / 2 + k * 2 * math.pi / 3, -math.pi / 2 + (k + 1) * 2 * math.pi / 3
            g.line(cx + math.cos(a0) * r * .7, cy + math.sin(a0) * r * .56, cx + math.cos(a1) * r * .7, cy + math.sin(a1) * r * .56, RUNE)

    def column(g: Grid, t, height, width):
        base = cy + 2
        for y in range(int(base - height), int(base) + 3):
            v = (base - y) / max(height, 1)                            # 0 ground → 1 top
            if v < -0.08:
                continue
            w = width * (0.75 + 0.35 * math.sin(min(1, max(0, v)) * math.pi * 0.9) + (0.35 if v < 0.12 else 0)) * (1 - 0.35 * max(0, v) ** 3)
            for x in range(int(cx - w - 4), int(cx + w + 5)):
                n = loop_noise(x * 1.0, y + 0.0, t, 3, 5 * s + 1, 1.5)
                n2 = loop_noise(x * 0.5, y * 0.35 + t * 0, t, 9, 4 * s + 1, 2.2)
                edge = w * (0.78 + 0.4 * n)
                dx = abs(x + .5 - cx - math.sin(v * 5 + t * 6.28) * 1.2 * s)
                if dx > edge or (v > 0.85 and n2 < (v - 0.85) * 5):
                    continue
                q = dx / max(edge, .5)
                heat = (1 - q) * 0.75 + n2 * 0.45 - max(0, v) * 0.25
                c = F4 if heat > .8 else F3 if heat > .6 else F2 if heat > .4 else F1 if heat > .22 else F0
                if q > 0.86:
                    c = F0
                g.set(x, y, c)

    for fi, st in enumerate(STAGES):
        gd, col, fx = gr.grid(), gr.grid(), gr.grid()
        rr = R * 0.82
        gd.ellipse(cx, cy, rr, rr * 0.8, lambda x, y: SC if bayer4(x, y) < (0.3 if st == "rune" else 0.7) else None)
        if st == "rune":
            rune(gd, rr, fi == 1)
            if fi == 1:
                for k in range(6):
                    fx.set(cx + (hash01(k, 1) - .5) * rr, cy - hash01(k, 2) * 6 * s, F2)
        elif st == "rise":
            rune(gd, rr, True)
            column(col, 0, (cy - top) * 0.55, R * 0.55)
        elif st == "burn":
            t = (fi - 3) / 6
            rune(gd, rr, False)
            column(col, t, cy - top, R * 0.66)
            for k in range(8 * tiles):                                    # sparks spiralling up around it
                ph = (t + hash01(k, 10)) % 1.0
                a = 2 * math.pi * (hash01(k, 11) + ph * 1.5)
                x = cx + math.cos(a) * R * (0.55 + 0.15 * hash01(k, 12))
                y = cy - ph * (cy - top) * 0.95
                if math.sin(a) > -0.2 or abs(x - cx) > R * 0.45:
                    fx.set(x, y, F3 if ph < .5 else F1)
        else:
            q = (fi - 9) / 3                                               # 0, .33, .66
            column(col, q * 0.5, (cy - top) * (0.45 - 0.35 * q), R * (0.58 - 0.25 * q))
            for k in range(10 * tiles):
                ph = q + 0.3 * hash01(k, 20)
                x = cx + (hash01(k, 21) - .5) * R * 1.3
                y = cy - (0.2 + hash01(k, 22) * 0.6) * (cy - top) * ph
                fx.set(x, y, F2 if hash01(k, fi) > 0.4 else F0)
        d.paint(gd, l_ground, fi)
        d.paint(col, l_col, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, DUR[fi])
    d.tag("rise", 0, 2)
    d.tag("burn", 3, 8)
    d.tag("end", 9, 11)
    return d.calls
