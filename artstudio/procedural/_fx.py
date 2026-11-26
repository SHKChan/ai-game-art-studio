"""Small shared helpers for skill-effect builders (pure computation on raster.Grid)."""
from __future__ import annotations

import math

from .raster import Grid, bayer4


def sparkle(g: Grid, x: float, y: float, arm: int, core: int, edge: int) -> None:
    """4-point star: bright core pixel, arms of `arm` px in the edge colour."""
    x, y = int(round(x)), int(round(y))
    for k in range(1, arm + 1):
        c = core if k == 1 and arm > 1 else edge
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            g.set(x + dx, y + dy, c)
    g.set(x, y, core)


def plus(g: Grid, x: float, y: float, r: int, fill: int, outline: int | None = None) -> None:
    """Plus sign (heal symbol) of half-length r; arms 1 px wide below r=3, 2 px wide from r=3."""
    x, y = int(round(x)), int(round(y))
    t = 1 if r >= 3 else 0
    pts = set()
    for k in range(-r, r + 1):
        for w in range(0, t + 1):
            pts.add((x + k, y + w))
            pts.add((x + w, y + k))
    if outline is not None:
        for px, py in pts:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (px + dx, py + dy) not in pts:
                    g.set(px + dx, py + dy, outline)
    for px, py in pts:
        g.set(px, py, fill)


def ring(g: Grid, cx, cy, rx, ry, width, color_fn) -> None:
    """Elliptical ring; color_fn(x, y, depth 0..1 across the band, angle) -> colour or None."""
    for y in range(int(cy - ry - width) - 1, int(cy + ry + width) + 2):
        for x in range(int(cx - rx - width) - 1, int(cx + rx + width) + 2):
            dx, dy = (x + .5 - cx) / max(rx, .5), (y + .5 - cy) / max(ry, .5)
            r = math.hypot(dx, dy)
            band = (r - 1.0) * min(rx, ry) / max(width, .5)  # -1..1 across the band
            if -1 <= band <= 1:
                c = color_fn(x, y, (band + 1) / 2, math.atan2(dy, dx))
                if c is not None:
                    g.set(x, y, c)


def dither_on(x, y, amount: float) -> bool:
    """True for roughly `amount` (0..1) of pixels in an ordered pattern — reads as transparency in pixel art."""
    return bayer4(x, y) < amount


def clamp_margin(v, lo, hi):
    return max(lo, min(hi, v))
