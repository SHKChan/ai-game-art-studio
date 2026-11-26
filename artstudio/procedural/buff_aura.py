"""Power-up aura: a rotating rune ring at the feet, flame-like streaks rising and chevrons climbing upward."""
from __future__ import annotations

import math

from ._fx import ring
from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame looping buff aura: rotating ring at the feet, rising energy streaks and upward chevrons."
LOOP = True
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "gold", "enum": ["gold", "red", "purple"]}}
PALETTES = {  # outline, deep, mid, light, pale, white
    "gold": ["#2e1606", "#8a4a0c", "#e08a14", "#ffc83a", "#fff0a0", "#ffffff"],
    "red": ["#2e0608", "#8a1418", "#e0302a", "#ff7a4a", "#ffd0a8", "#ffffff"],
    "purple": ["#1a0830", "#4a1a8a", "#8a3ae0", "#c07aff", "#ecd0ff", "#ffffff"],
}


def build(size: int = 64, frames: int = 8, color: str = "gold", **_):
    s = size / 64.0
    n = max(2, int(frames))
    d = DocBuilder(f"buff-aura-{color}", size, size)
    d.palette(PALETTES[color])
    l_back, l_streaks, l_front, l_fx = d.layer("ring back"), d.layer("streaks"), d.layer("ring front"), d.layer("chevrons")
    d.add_frames(n - 1, 80)
    d.duration(0, 80)
    cx, gy, rx = 32 * s, 51 * s, 22 * s
    ry = rx * 0.32
    for f in range(n):
        rot = 2 * math.pi * f / n
        back, front, streaks, fx = Grid(size, size), Grid(size, size), Grid(size, size), Grid(size, size)

        def ring_col(x, y, t, a):
            seg = (a - rot) % (2 * math.pi / 6)            # six bright runes travelling round the ring
            bright = seg < 0.35
            c = 5 if bright and 0.25 < t < 0.75 else (4 if bright else (3 if 0.3 < t < 0.7 else 2))
            return c
        tmp = Grid(size, size)
        ring(tmp, cx, gy, rx, ry, 1.5 * s, ring_col)
        for y in range(size):
            for x in range(size):
                v = tmp.px[y][x]
                if v is not None:
                    (back if y + .5 < gy else front).set(x, y, v)
        for k in range(14):
            ang = 2 * math.pi * k / 14 + 0.4 * hash01(k, 1)
            bx = cx + math.cos(ang) * rx * 0.92
            by = gy + math.sin(ang) * ry * 0.92
            t = (f / n + hash01(k, 2)) % 1.0
            h = (10 + 14 * hash01(k, 3)) * s
            top = by - h * (0.3 + 0.7 * t)
            bot = by - h * max(0.0, t - 0.45)
            for y in range(int(top), int(bot) + 1):
                u = (bot - y) / max(1.0, bot - top)
                c = 5 if u > 0.85 else (4 if u > 0.5 else 3)
                streaks.set(bx, y, c)
                if hash01(k, 4) > 0.6 and u < 0.5:
                    streaks.set(bx + 1, y, 2)
        for k in range(3):
            t = (f / n + k / 3) % 1.0
            y0 = gy - 10 * s - t * 34 * s
            x0 = cx + (k - 1) * 13 * s
            if t > 0.9:
                continue
            c = 5 if t < 0.3 else (4 if t < 0.65 else 3)
            for i in range(int(4 * s) + 1):
                for w in range(2):
                    fx.set(x0 - i, y0 + i + w, c)
                    fx.set(x0 + i, y0 + i + w, c)
        d.paint(back, l_back, f)
        d.paint(streaks, l_streaks, f)
        d.paint(front, l_front, f)
        d.paint(fx, l_fx, f)
    d.tag("aura", 0, n - 1)
    return d.calls
