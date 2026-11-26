"""Lightning strike: warning glint, a jagged bolt cracks down from the sky, impact flash and shock ring,
then branches flicker out and sparks scatter. Plays once."""
from __future__ import annotations

import math

from ._fx import ring, sparkle
from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame lightning strike: bolt from the sky, impact flash, shock ring, branches and sparks."
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64},
          "color": {"type": "string", "default": "blue", "enum": ["blue", "purple", "yellow"]},
          "thickness": {"type": "int", "default": 1, "min": 1, "max": 3}}
PALETTES = {  # outline, deep, mid, light, pale, white
    "blue": ["#08102e", "#1a3a9a", "#3a7aff", "#8ac8ff", "#dcf2ff", "#ffffff"],
    "purple": ["#14062e", "#4a1a9a", "#8a4aff", "#c8a0ff", "#f0e0ff", "#ffffff"],
    "yellow": ["#2a1a04", "#8a6010", "#e0b020", "#ffe060", "#fff8c0", "#ffffff"],
}
# (bolt reach 0..1, bolt width, flash radius, ring radius, branches, sparks)
FRAMES = [(0.0, 0, 0, 0, False, 0), (0.45, 1, 0, 0, False, 0), (1.0, 2, 9, 0, False, 0), (1.0, 3, 13, 8, True, 0),
          (1.0, 2, 7, 14, True, 1), (1.0, 1, 0, 19, True, 2), (0.0, 0, 0, 23, False, 3), (0.0, 0, 0, 0, False, 4)]
DURATIONS = [120, 40, 50, 70, 70, 70, 80, 90]


def bolt_path(s, seed, x0, y0, x1, y1, steps):
    pts = [(x0, y0)]
    for i in range(1, steps):
        t = i / steps
        jit = (hash01(seed, i) - 0.5) * 12 * s * (1 - abs(0.5 - t))
        pts.append((x0 + (x1 - x0) * t + jit, y0 + (y1 - y0) * t))
    pts.append((x1, y1))
    return pts


def draw_poly(g, pts, width, core, mid, edge):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = max(1, int(math.hypot(bx - ax, by - ay) * 2))
        for i in range(L + 1):
            x, y = ax + (bx - ax) * i / L, ay + (by - ay) * i / L
            for dx in range(-width - 1, width + 2):
                d = abs(dx)
                c = core if d < max(1, width - 1) else (mid if d <= width else edge)
                if g.get(x + dx, y) in (core,) and c != core:
                    continue
                g.set(x + dx, y, c)


def build(size: int = 64, color: str = "blue", thickness: int = 1, **_):
    extra = max(1, min(3, int(thickness))) - 1
    s = size / 64.0
    d = DocBuilder(f"lightning-{color}", size, size)
    d.palette(PALETTES[color])
    l_bolt, l_flash, l_spark = d.layer("bolt"), d.layer("flash"), d.layer("sparks")
    d.add_frames(len(FRAMES) - 1, 60)
    gx, gy = 32 * s, 53 * s
    main = bolt_path(s, 3, 30 * s, 2 * s, gx, gy, 9)
    for fi, (reach, width, flash_r, ring_r, branches, sparks) in enumerate(FRAMES):
        bolt, flash, sp = Grid(size, size), Grid(size, size), Grid(size, size)
        if fi == 0:  # warning: glint on the ground + faint charge at the top
            sparkle(sp, gx, gy - 2 * s, 2, 5, 3)
            ring(sp, gx, gy, 6 * s, 2 * s, 0.8, lambda x, y, t, a: 3)
            sparkle(sp, 30 * s, 4 * s, 1, 4, 2)
        if reach > 0:
            k = max(2, int(len(main) * reach))
            pts = main[:k] if reach < 1 else main
            draw_poly(bolt, pts, width + extra, 5, 4, 0)
            if branches:
                for b, (i0, sgn) in enumerate(((3, -1), (5, 1), (7, -1))):
                    ax, ay = main[i0]
                    bp = bolt_path(s, 20 + b + fi, ax, ay, ax + sgn * 12 * s, ay + 10 * s, 4)
                    draw_poly(bolt, bp, (0 if width < 3 else 1) + extra // 2, 4, 3, 0)
        if flash_r:
            r = flash_r * s
            for y in range(int(gy - r), int(gy + r * 0.5) + 1):
                for x in range(int(gx - r), int(gx + r) + 1):
                    q = math.hypot(x + .5 - gx, (y + .5 - gy) * 1.6) / r
                    if q <= 1:
                        flash.set(x, y, 5 if q < 0.55 else (4 if q < 0.8 else 3))
        if ring_r:
            rr = ring_r * s
            ring(flash, gx, gy, rr, rr * 0.3, 1.2 * s, lambda x, y, t, a: (4 if t > 0.4 else 2) if rr < 21 * s else 2)
        if sparks:
            for k in range(10):
                ang = -math.pi * (0.1 + 0.8 * hash01(k, 9))
                dist = (5 + sparks * 5 + 4 * hash01(k, 8)) * s
                x, y = gx + math.cos(ang) * dist, gy + math.sin(ang) * dist * 0.8 + sparks * sparks * 0.6 * s
                if sparks < 4 or hash01(k, 7) > 0.5:
                    c = 5 if sparks <= 2 else (3 if sparks == 3 else 2)
                    sp.set(x, y, c)
                    if sparks <= 2:
                        sp.set(x - math.cos(ang), y - math.sin(ang), 3)
        d.paint(flash, l_flash, fi)
        d.paint(bolt, l_bolt, fi)
        d.paint(sp, l_spark, fi)
        d.duration(fi, DURATIONS[fi])
    d.tag("strike", 0, len(FRAMES) - 1)
    return d.calls
