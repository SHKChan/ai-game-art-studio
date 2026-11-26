"""Dark vortex (暗黑漩涡 / 诅咒之地): top-down curse field. A rune ring turns on the ground, shadow tendrils curl
in towards a void at the centre and dark motes rise. Seamless loop."""
from __future__ import annotations

import math

from ._ground import Ground, contour
from .raster import DocBuilder, bayer4, hash01

DESCRIPTION = "Top-down dark curse field for a grid: turning rune ring, curling shadow tendrils, void core, rising motes (loop)."
ASSET_TYPE = "effect"
FULL_BLEED = True
LOOP = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "dark", "enum": ["dark", "blood", "void"]}}
# 0 black 1 deep 2 mid 3 bright 4 glow 5 pale
PALETTES = {
    "dark": ["#0a0612", "#2a1240", "#561e80", "#9a3ad0", "#d27aff", "#f4d8ff"],
    "blood": ["#0e0406", "#3e0a12", "#7a1222", "#c8283a", "#ff6a6a", "#ffd4d0"],
    "void": ["#04100e", "#0e2e2a", "#1a5a4e", "#2ea888", "#6af0c4", "#d8fff0"],
}
ARMS = 5


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=28)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, frames: int = 8, color: str = "dark", **_):
    gr = _ground(tiles)
    s, R, cx, cy = gr.s, gr.R, gr.cx, gr.cy
    K, D, M, B, G, P = range(6)
    n = max(4, min(16, int(frames)))
    d = DocBuilder(f"dark-vortex-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_floor, l_tend, l_fx = d.layer("curse floor"), d.layer("tendrils"), d.layer("motes")
    d.add_frames(n - 1, 90)
    for fi in range(n):
        t = fi / n
        fl, te, fx = gr.grid(), gr.grid(), gr.grid()
        rot = 2 * math.pi * t / ARMS

        def floor(x, y):
            dist, ang = gr.polar(x, y)
            q = dist / R
            if q > 1:
                return None
            if q > 0.9:
                tick = int(((ang - rot * 2) % (2 * math.pi)) / (2 * math.pi) * 36)
                return B if tick % 3 == 0 else (M if q < 0.96 else D)
            if q > 0.84:
                return D
            if q < 0.16:
                return K
            if q < 0.22:
                return G if bayer4(x, y) < 0.5 else B
            return D if bayer4(x, y) < 0.5 + 0.4 * (1 - q) else None
        fl.field(floor)
        for k in range(ARMS):                                     # tendrils spiral from rim to core
            a0 = 2 * math.pi * k / ARMS + rot
            pts = []
            for i in range(24):
                u = i / 23
                r = R * (0.84 - 0.62 * u)
                a = a0 + u * 2.4 + 0.25 * math.sin(u * 6 + t * 2 * math.pi * 1 + k)
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, (1 - u) * 3.2 * s + 0.6))
            for x, y, w in pts:
                te.ellipse(x, y, w, w, M)
            for x, y, w in pts[::2]:
                te.set(x - w * .4, y - w * .4, B)
        contour(te, K)
        for k in range(8 + 3 * tiles):                            # motes rise from the field
            ph = (t + hash01(k, 1)) % 1.0
            a = 2 * math.pi * hash01(k, 2)
            r = R * 0.85 * math.sqrt(hash01(k, 3))
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r - ph * 26 * s
            fx.set(x, y, G if ph < 0.5 else B)
            if ph < 0.3:
                fx.set(x, y + 1, M)
        fx.set(cx, cy - 1, P if fi % 2 == 0 else G)               # pulsing void glint
        d.paint(fl, l_floor, fi)
        d.paint(te, l_tend, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, 90)
    d.tag("curse", 0, n - 1)
    return d.calls
