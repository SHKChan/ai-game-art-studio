"""Healing effect: a ground glow pulses, a shimmering light column rises and plus-shaped motes float up and fade."""
from __future__ import annotations

import math

from ._fx import dither_on, plus, ring, sparkle
from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame healing effect: pulsing ground glow, rising light column and floating plus-shaped motes."
LOOP = True
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64}, "frames": {"type": "int", "default": 8, "max": 16},
          "color": {"type": "string", "default": "green", "enum": ["green", "blue", "gold"]}}
PALETTES = {  # outline, deep, mid, light, pale, white
    "green": ["#0b2a1a", "#146b3a", "#2fbf5a", "#7ff07a", "#d4ffb0", "#ffffff"],
    "blue": ["#0b1a36", "#1a4f9a", "#2f8fe0", "#7fd0ff", "#d4f2ff", "#ffffff"],
    "gold": ["#2e1a06", "#8a5a10", "#e0a020", "#ffd860", "#fff4b8", "#ffffff"],
}


def build(size: int = 64, frames: int = 8, color: str = "green", **_):
    s = size / 64.0
    n = max(2, int(frames))
    d = DocBuilder(f"heal-{color}", size, size)
    d.palette(PALETTES[color])
    l_glow, l_col, l_motes = d.layer("ground glow"), d.layer("light column"), d.layer("motes")
    d.add_frames(n - 1, 90)
    d.duration(0, 90)
    cx, gy = 32 * s, 52 * s
    for f in range(n):
        ph = f / n
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * ph)
        glow, col, motes = Grid(size, size), Grid(size, size), Grid(size, size)
        rx = (17 + 3 * pulse) * s
        ring(glow, cx, gy, rx, rx * 0.3, 1.6 * s, lambda x, y, t, a: 4 if t > 0.5 else 2)
        inner = rx * 0.78
        for y in range(int(gy - inner * 0.3) - 1, int(gy + inner * 0.3) + 2):
            for x in range(int(cx - inner) - 1, int(cx + inner) + 2):
                q = ((x + .5 - cx) / inner) ** 2 + ((y + .5 - gy) / (inner * 0.3)) ** 2
                if q <= 1 and dither_on(x, y, (1 - q) * (0.35 + 0.3 * pulse)):
                    glow.set(x, y, 3 if q > 0.3 else 4)
        for y in range(int(8 * s), int(gy)):
            h = (gy - y) / (gy - 8 * s)                      # 0 at ground, 1 at top
            half = (9 - 4 * h) * s
            for x in range(int(cx - half) - 1, int(cx + half) + 2):
                u = abs(x + .5 - cx) / half
                if u > 1:
                    continue
                amt = (1 - u) * (1 - h) ** 0.7 * (0.45 + 0.25 * pulse)
                shimmer = hash01(x, y // 2 + f * 3, 7)
                if dither_on(x, y, amt) and shimmer > 0.25:
                    col.set(x, y, 5 if u < 0.25 and h < 0.5 else (4 if u < 0.6 else 3))
        for k in range(9):
            t = (ph + hash01(k, 1)) % 1.0
            x = cx + (hash01(k, 2) - 0.5) * 30 * s + math.sin(t * 6.3 + k) * 2.5 * s
            y = gy - 4 * s - t * 40 * s
            if t > 0.92:
                continue
            big = hash01(k, 3) > 0.5
            if t < 0.6:
                if big:
                    plus(motes, x, y, 3, 4 if t < 0.35 else 3, 0)
                    motes.set(x, y, 5)
                    motes.set(x, y - 1, 5)
                else:
                    sparkle(motes, x, y, 1, 5, 3)
            else:
                motes.set(x, y, 3 if t < 0.8 else 2)
        d.paint(glow, l_glow, f)
        d.paint(col, l_col, f)
        d.paint(motes, l_motes, f)
    d.tag("heal", 0, n - 1)
    return d.calls
