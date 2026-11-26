"""Frost nova: a white flash at the centre, then a ring of ice shards bursts outward along the ground plane,
leaving a frosted ring that cracks into drifting snow. Plays once."""
from __future__ import annotations

import math

from ._fx import ring, sparkle
from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame frost nova: centre flash, outward ring of ice shards, frost ring and drifting snow."
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64},
          "color": {"type": "string", "default": "ice", "enum": ["ice", "arcane", "toxic"]}}
PALETTES = {  # outline, deep, mid, light, pale, white
    "ice": ["#0d1b3a", "#1f4f8f", "#3e9ad8", "#8fd8ff", "#dff6ff", "#ffffff"],
    "arcane": ["#1a0a36", "#4a2a9a", "#7a5ae0", "#b8a0ff", "#ece4ff", "#ffffff"],
    "toxic": ["#0c2410", "#1f6a2a", "#4ab83a", "#a8ec6a", "#e8ffc8", "#ffffff"],
}
# (ring radius, shard length, flash radius, fade 0..1)
FRAMES = [(0, 0, 6, 0), (6, 5, 9, 0), (11, 8, 5, 0), (16, 9, 0, 0), (21, 8, 0, 0.1), (25, 6, 0, 0.35), (27, 3, 0, 0.65), (28, 0, 0, 0.9)]
DURATIONS = [50, 50, 60, 60, 70, 80, 90, 100]
SHARDS = 12


def build(size: int = 64, color: str = "ice", **_):
    s = size / 64.0
    d = DocBuilder(f"frost-nova-{color}", size, size)
    d.palette(PALETTES[color])
    l_ring, l_shards, l_fx = d.layer("frost ring"), d.layer("shards"), d.layer("flash & snow")
    d.add_frames(len(FRAMES) - 1, 60)
    cx, cy, squash = 32 * s, 38 * s, 0.45
    for fi, (R, L, fr, fade) in enumerate(FRAMES):
        rg, sh, fx = Grid(size, size), Grid(size, size), Grid(size, size)
        R, L = R * s, L * s
        if R:
            ring(rg, cx, cy, R, R * squash, 1.8 * s,
                 lambda x, y, t, a: None if fade and hash01(x, y, fi) < fade else (4 if t > 0.55 else (3 if t > 0.25 else 2)))
        if L:
            for k in range(SHARDS):
                a = 2 * math.pi * (k + 0.5 * hash01(k, 1)) / SHARDS
                ln = L * (0.7 + 0.5 * hash01(k, 2))
                bx, by = cx + math.cos(a) * R, cy + math.sin(a) * R * squash
                tip = (bx + math.cos(a) * ln * 0.6, by - ln + math.sin(a) * ln * 0.25)   # shards point up and outward
                w = 2.2 * s
                nx, ny = math.cos(a + math.pi / 2) * w, math.sin(a + math.pi / 2) * w * squash
                base = [(bx - nx, by - ny), (bx + nx, by + ny)]
                sh.polygon([base[0], tip, base[1]], 3)
                sh.polygon([base[0], tip, (bx, by)], 4)            # lit face
                sh.line(bx, by, tip[0], tip[1], 5)
            out = sh.copy()
            out.outline(0)
            for y in range(size):
                for x in range(size):
                    if out.px[y][x] == 0 and sh.px[y][x] is None:
                        sh.set(x, y, 1)
        if fr:
            r = fr * s
            for y in range(int(cy - r), int(cy + r) + 1):
                for x in range(int(cx - r), int(cx + r) + 1):
                    q = math.hypot(x + .5 - cx, (y + .5 - cy) * 1.4) / r
                    if q <= 1:
                        fx.set(x, y, 5 if q < 0.6 else 4)
            sparkle(fx, cx, cy - r - 2 * s, 2, 5, 4)
        if fi >= 3:
            for k in range(14):
                a = 2 * math.pi * hash01(k, 11)
                rr = R * (0.4 + 0.7 * hash01(k, 12))
                x = cx + math.cos(a) * rr
                y = cy + math.sin(a) * rr * squash - (fi - 3) * 2.2 * s * (0.5 + hash01(k, 13))
                if hash01(k, fi) < 0.75:
                    fx.set(x, y, 5 if fi < 6 else 4)
        d.paint(rg, l_ring, fi)
        d.paint(sh, l_shards, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, DURATIONS[fi])
    d.tag("nova", 0, len(FRAMES) - 1)
    return d.calls
