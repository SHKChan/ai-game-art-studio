"""Poison cloud: a lumpy toxic cloud that churns in place (seamless loop), with bubbles rising and popping on top
and drips falling underneath."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, hash01, ramp_pick, vnoise

DESCRIPTION = "8-frame looping poison cloud: churning toxic cloud, popping bubbles and falling drips."
LOOP = True
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "green", "enum": ["green", "purple", "orange"]}}
PALETTES = {  # outline, darkest, dark, mid, light, highlight
    "green": ["#0e1f0a", "#24461a", "#3f7a22", "#6cb82e", "#a8e84a", "#e4ff9a"],
    "purple": ["#1a0a24", "#3a1650", "#62268a", "#9a44c8", "#cc80f0", "#f2d4ff"],
    "orange": ["#2a1004", "#5a260a", "#9a4410", "#d8701a", "#f4a84a", "#ffe0a0"],
}
LOBES = [(-13, 2, 10), (-3, -4, 12), (9, -2, 11), (16, 4, 8), (-19, 6, 6), (2, 6, 11)]


def build(size: int = 64, frames: int = 8, color: str = "green", **_):
    s = size / 64.0
    n = max(2, int(frames))
    d = DocBuilder(f"poison-cloud-{color}", size, size)
    d.palette(PALETTES[color])
    l_drip, l_cloud, l_bub = d.layer("drips"), d.layer("cloud"), d.layer("bubbles")
    d.add_frames(n - 1, 100)
    cx, cy = 32 * s, 30 * s
    for f in range(n):
        ph = 2 * math.pi * f / n
        cloud, bub, drip = Grid(size, size), Grid(size, size), Grid(size, size)

        def dens(x, y):
            v = -9.0
            for i, (ox, oy, r) in enumerate(LOBES):
                lx = cx + ox * s + math.sin(ph + i * 1.7) * 1.3 * s
                ly = cy + oy * s + math.cos(ph + i * 2.3) * 1.0 * s
                rr = r * s * (1 + 0.06 * math.sin(ph * 1 + i))
                v = max(v, 1 - math.hypot(x + .5 - lx, y + .5 - ly) / rr)
            w = 0.5 + 0.5 * math.cos(ph)  # loop-safe noise blend
            nz = vnoise(x / (6 * s), y / (6 * s), 3) * w + vnoise(x / (6 * s) + 7, y / (6 * s) + 3, 3) * (1 - w)
            return v + (nz - 0.5) * 0.35 if v > -0.3 else v

        def px(x, y):
            v = dens(x, y)
            if v <= 0:
                return None
            light = 0.55 * min(1, v * 1.8) + 0.45 * (1 - (y - (cy - 16 * s)) / (30 * s))   # lit from above
            return ramp_pick(light, [1, 2, 3, 4, 5], x, y, 0.4)
        cloud.field(px)
        o = cloud.copy()
        o.outline(0)
        for y in range(size):
            for x in range(size):
                if o.px[y][x] == 0 and cloud.px[y][x] is None:
                    cloud.set(x, y, 0)
        for k in range(5):
            t = (f / n + hash01(k, 1)) % 1.0
            bx = cx + (hash01(k, 2) - 0.5) * 34 * s
            by = cy - 8 * s - t * 14 * s
            r = (1.5 + 2.5 * hash01(k, 3)) * s * (0.6 + t)
            if t < 0.8:
                bub.ellipse(bx, by, r, r, lambda x, y: 4)
                bub.ellipse(bx, by, max(0.6, r - 1.2), max(0.6, r - 1.2), lambda x, y: 3)
                bub.set(bx - r * 0.4, by - r * 0.4, 5)
            elif t < 0.9:
                for a in range(6):
                    ang = a * math.pi / 3
                    bub.set(bx + math.cos(ang) * (r + 1.5), by + math.sin(ang) * (r + 1.5), 4)
        for k in range(4):
            t = (f / n + hash01(k, 21)) % 1.0
            dx = cx + (hash01(k, 22) - 0.5) * 30 * s
            top = cy + 10 * s
            y = top + t * 20 * s
            if t < 0.15:
                drip.set(dx, top, 3)
            else:
                drip.set(dx, y, 3)
                drip.set(dx, y - 1, 2)
                if t < 0.6:
                    drip.set(dx, y - 2, 1)
        d.paint(drip, l_drip, f)
        d.paint(cloud, l_cloud, f)
        d.paint(bub, l_bub, f)
    d.tag("cloud", 0, n - 1)
    return d.calls
