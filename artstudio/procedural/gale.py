"""Gale (暴风): a tornado funnel on the target cell(s), with striped wind bands spinning upward, a dust ring on the
ground and leaves/debris orbiting it. Seamless loop."""
from __future__ import annotations

import math

from ._ground import Ground
from .raster import DocBuilder, bayer4, hash01

DESCRIPTION = "Tornado on a grid cell: spinning striped funnel, ground dust ring and orbiting leaves (8-frame loop)."
ASSET_TYPE = "effect"
FULL_BLEED = True
LOOP = True
PARAMS = {"tiles": {"type": "int", "default": 1, "min": 1, "max": 3}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "wind", "enum": ["wind", "sand", "storm"]}}
# 0 outline 1 dark 2 mid 3 light 4 white 5 leaf 6 leaf light 7 dust
PALETTES = {
    "wind": ["#14302a", "#4a9a86", "#86d6be", "#c8f4e4", "#ffffff", "#3a8a2a", "#8ad04a", "#a8b89a"],
    "sand": ["#2c1c0e", "#8a6438", "#c09860", "#e6cc96", "#fff6e0", "#6a4a24", "#a87a3a", "#b4a080"],
    "storm": ["#0e1220", "#3a4668", "#6a7aa0", "#a8b8d8", "#f0f6ff", "#4a5a7a", "#f4e86a", "#7a8294"],
}


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=48 * t)


def pivot(tiles: int = 1, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 1, frames: int = 8, color: str = "wind", **_):
    tiles = int(tiles)
    gr = _ground(tiles)
    s, R, cx, cy = gr.s * 3, gr.R, gr.cx, gr.cy
    OUT, D, M, L, W, LF, LF2, DU = range(8)
    n = max(4, min(16, int(frames)))
    d = DocBuilder(f"gale-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_dust, l_back, l_funnel, l_front = d.layer("ground dust"), d.layer("debris (behind)"), d.layer("funnel"), d.layer("debris (front)")
    d.add_frames(n - 1, 70)
    top = 3
    H = cy - top
    for fi in range(n):
        t = fi / n
        du, bk, fu, fr = gr.grid(), gr.grid(), gr.grid(), gr.grid()
        for y in range(top, int(cy) + 2):                   # funnel: slices from the ground up
            v = max(0.0, (cy - y) / H)                      # 0 ground → 1 top
            r = R * (0.2 + 0.75 * v ** 1.3)
            ox = math.sin(v * 3.2 + t * 2 * math.pi) * 2.5 * s * v
            for x in range(int(cx + ox - r) - 1, int(cx + ox + r) + 2):
                u = (x + .5 - cx - ox) / max(r, .5)
                if abs(u) > 1:
                    continue
                ang = math.asin(max(-1, min(1, u)))
                band = math.sin(3 * (ang + 2 * math.pi * t) + v * 14)       # 3 bands → loop after 1/3 turn × 3
                edge = abs(u) > 0.86
                if edge:
                    c = M if band > 0 else D
                elif band > 0.55:
                    c = W if band > 0.85 and abs(u) < 0.6 else L
                elif band > -0.2:
                    c = M
                else:
                    c = None if bayer4(x, y) < 0.55 else D           # see-through gaps
                if c is not None and v > 0.82 and bayer4(x, y) < (v - 0.82) / 0.18:
                    c = None
                if c is not None:
                    fu.set(x, y, c)
        for k in range(14):                                    # ground dust ring
            a = 2 * math.pi * (k / 14 + t / 2)
            rr = R * (0.75 + 0.15 * hash01(k, 1))
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.55
            r = 1.6 * s + hash01(k, 2) * 1.5
            du.ellipse(x, y, r, r * 0.7, lambda xx, yy: L if yy < y - r * 0.2 else DU)
        for k in range(8 + 4 * tiles):                         # leaves orbit while rising
            ph = (t + hash01(k, 3)) % 1.0
            a = 2 * math.pi * (hash01(k, 4) + 2 * ph)
            v = ph
            rr = R * (0.3 + 0.8 * v ** 1.3)
            x, y = cx + math.cos(a) * rr, cy - v * H * 0.9 + math.sin(a) * rr * 0.3
            g = fr if math.sin(a) > 0 else bk
            g.set(x, y, LF2 if k % 2 else LF)
            g.set(x + (1 if math.cos(a) > 0 else -1), y, LF)
            g.set(x, y + 1, OUT)
        d.paint(du, l_dust, fi)
        d.paint(bk, l_back, fi)
        d.paint(fu, l_funnel, fi)
        d.paint(fr, l_front, fi)
        d.duration(fi, 70)
    d.tag("spin", 0, n - 1)
    return d.calls
