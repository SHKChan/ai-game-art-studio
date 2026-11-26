"""Shield barrier: a hexagon-patterned bubble grows from the centre, locks with a flash, shimmers (a highlight
band sweeps across the cells) and finally dissolves. Interior is dithered so the character shows through."""
from __future__ import annotations

import math

from ._fx import dither_on, sparkle
from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame shield barrier: hexagon bubble forms, flashes, shimmers and dissolves (see-through interior)."
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64},
          "color": {"type": "string", "default": "azure", "enum": ["azure", "gold", "green"]}}
PALETTES = {  # outline, deep, mid, light, pale, white
    "azure": ["#081a36", "#1a4f9a", "#3a9ae0", "#8adcff", "#dcf6ff", "#ffffff"],
    "gold": ["#2e1a06", "#8a5a10", "#e0a020", "#ffd860", "#fff4b8", "#ffffff"],
    "green": ["#0a2a16", "#167a40", "#30c060", "#8af0a0", "#d8ffe0", "#ffffff"],
}
# (radius, rim brightness 0..1, highlight sweep position or None, dissolve 0..1)
FRAMES = [(8, 1.0, None, 0), (17, 0.9, None, 0), (26, 1.0, None, 0), (26, 0.7, 0.0, 0), (26, 0.7, 0.35, 0),
          (26, 0.7, 0.7, 0), (26, 0.6, None, 0.4), (26, 0.4, None, 0.8)]
DURATIONS = [60, 60, 90, 90, 90, 90, 80, 80]


def hex_edge(x, y, cell):
    """Distance (in cell units) to the nearest edge of a pointy-top hex grid."""
    q = (math.sqrt(3) / 3 * x - y / 3) / cell
    r = (2 / 3 * y) / cell
    cx, cz = q, r
    cy = -cx - cz
    rx, ry, rz = round(cx), round(cy), round(cz)
    dx, dy, dz = abs(rx - cx), abs(ry - cy), abs(rz - cz)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    fx, fy, fz = cx - rx, cy - ry, cz - rz
    return 0.5 - max(abs(fx), abs(fy), abs(fz)) * 1.0


def build(size: int = 64, color: str = "azure", **_):
    s = size / 64.0
    d = DocBuilder(f"shield-{color}", size, size)
    d.palette(PALETTES[color])
    l_fill, l_rim, l_fx = d.layer("hex fill"), d.layer("rim"), d.layer("glints")
    d.add_frames(len(FRAMES) - 1, 80)
    cx, cy = 32 * s, 32 * s
    for fi, (rad, rim_b, sweep, dis) in enumerate(FRAMES):
        R = rad * s
        fill, rim, fx = Grid(size, size), Grid(size, size), Grid(size, size)
        for y in range(int(cy - R) - 2, int(cy + R) + 3):
            for x in range(int(cx - R) - 2, int(cx + R) + 3):
                dx, dy = x + .5 - cx, y + .5 - cy
                r = math.hypot(dx, dy)
                if r > R + 0.5:
                    continue
                if dis and hash01(x, y, 5) < dis:
                    continue
                u = r / max(R, 1)
                if r > R - 1.6 * s:  # rim
                    hi = dy < 0 and dx < 0
                    rim.set(x, y, 5 if hi and rim_b > 0.8 else (4 if hi or rim_b > 0.9 else 3))
                    continue
                if r > R - 2.6 * s:
                    rim.set(x, y, 2)
                    continue
                e = hex_edge(dx, dy, 6.5 * s)
                lit = sweep is not None and abs((dx + dy) / (2.8 * R) + 0.5 - sweep) < 0.12
                if e < 0.07:
                    if dither_on(x, y, 0.55 + 0.4 * u) or lit:
                        fill.set(x, y, 5 if lit else (4 if u > 0.7 else 3))
                elif lit and dither_on(x, y, 0.35):
                    fill.set(x, y, 4)
                elif dither_on(x, y, 0.10 * u * u):
                    fill.set(x, y, 3)
        # specular highlight crescent, top-left
        if R > 10 * s and not dis:
            for k in range(6):
                a = math.radians(205 + k * 9)
                fx.set(cx + math.cos(a) * (R - 4 * s), cy + math.sin(a) * (R - 4 * s), 5)
        if fi == 2:
            for k in range(6):
                a = 2 * math.pi * k / 6 + 0.3
                sparkle(fx, cx + math.cos(a) * R, cy + math.sin(a) * R, 2, 5, 4)
        if dis:
            for k in range(8):
                a = 2 * math.pi * hash01(k, fi)
                rr = R + (2 + 4 * dis) * s * hash01(k, 3)
                fx.set(cx + math.cos(a) * rr, cy + math.sin(a) * rr - dis * 4 * s, 4 if dis < 0.6 else 3)
        d.paint(fill, l_fill, fi)
        d.paint(rim, l_rim, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, DURATIONS[fi])
    d.tag("shield", 0, len(FRAMES) - 1)
    return d.calls
