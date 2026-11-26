"""Whirlpool (漩涡): top-down water skill. A spiralling vortex churns on the area (seamless loop) with foam
crests, a dark eye and splashing droplets at the rim. Loops."""
from __future__ import annotations

import math

from ._ground import Ground
from .raster import DocBuilder, bayer4, hash01, vnoise

DESCRIPTION = "Top-down whirlpool for a grid: spiralling vortex with foam crests, dark eye and rim splashes (8-frame loop)."
ASSET_TYPE = "effect"
FULL_BLEED = True
LOOP = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "water", "enum": ["water", "abyss", "sand"]}}
# 0 eye 1 deep 2 mid 3 light 4 foam 5 white 6 rim-dark
PALETTES = {
    "water": ["#06142a", "#0f3a78", "#1c6ec0", "#3ea8e8", "#a8e4ff", "#ffffff", "#0a2448"],
    "abyss": ["#08040e", "#26124a", "#45288a", "#6a4cc0", "#b8a4f0", "#f4eeff", "#160a2a"],
    "sand": ["#2a1a0c", "#6e4a24", "#a07038", "#c89a58", "#e8cc94", "#fff4d8", "#4a3018"],
}
ARMS = 3


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=6)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, frames: int = 8, color: str = "water", **_):
    gr = _ground(tiles)
    s, R, cx, cy = gr.s, gr.R, gr.cx, gr.cy
    EYE, D, M, L, FO, W, RIM = range(7)
    n = max(4, min(16, int(frames)))
    d = DocBuilder(f"whirlpool-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_water, l_foam = d.layer("water"), d.layer("foam & spray")
    d.add_frames(n - 1, 90)
    for fi in range(n):
        t = fi / n
        wa, fo = gr.grid(), gr.grid()
        rot = 2 * math.pi * t / ARMS                       # one arm-period per loop → seamless

        def px(x, y):
            dist, ang = gr.polar(x, y)
            rr = gr.blob_r(ang - rot * 0.5 * 0, R, 4, 0.06)
            if dist > rr:
                return None
            q = dist / rr                                   # 0 centre → 1 rim
            if q > 0.94:
                return RIM if bayer4(x, y) > 0.3 else D
            spiral = math.sin(ARMS * (ang + rot) + 9.0 * math.log(q + 0.08))     # log spiral arms
            depth = q ** 0.7 + 0.12 * vnoise(x / 4, y / 4, 2)
            if q < 0.1:
                return EYE
            v = depth * 0.75 + spiral * 0.22
            if spiral > 0.86 and q > 0.18:
                return W if spiral > 0.95 and q > 0.35 else FO
            return D if v < 0.35 else (M if v < 0.62 else L)
        wa.field(px)
        for k in range(10 + 4 * tiles):                     # droplets thrown off the rim (orbit + hop)
            ph = (t + hash01(k, 1)) % 1.0
            a = 2 * math.pi * hash01(k, 2) + rot * ARMS * 0.5 * (1 + ph)
            r = R * (0.95 + 0.1 * ph)
            hop = math.sin(math.pi * ph) * 6 * s
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r - hop
            fo.set(x, y, W if ph < 0.5 else FO)
            if ph < 0.3:
                fo.set(x + 1, y, FO)
        for k in range(6 + 2 * tiles):                      # foam flecks circling inward
            ph = (t + hash01(k, 7)) % 1.0
            q = 0.85 - 0.6 * ph
            a = 2 * math.pi * hash01(k, 8) + ph * 4 + rot * 2
            fo.set(cx + math.cos(a) * R * q, cy + math.sin(a) * R * q, FO)
        d.paint(wa, l_water, fi)
        d.paint(fo, l_foam, fi)
        d.duration(fi, 90)
    d.tag("swirl", 0, n - 1)
    return d.calls
