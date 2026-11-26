"""Shared helpers for top-down ground skills (tactics grid). Canvas convention for every ground effect:

    width  = tiles * 32
    height = tiles * 32 + head        (head = headroom for things that rise: flames, pillars, spikes)

The bottom `tiles*32` square is the ground area (it lines up with the grid cells); the effect's ground
centre is the centre of that square. Pivot for engines: bottom-centre of the canvas, offset up by
tiles*16 px — or simply align the bottom square with the target cells."""
from __future__ import annotations

import math
from functools import lru_cache

from .raster import Grid, bayer4, hash01, vnoise

TILE = 32


class Ground:
    def __init__(self, tiles: int, head: int = TILE):
        if tiles not in (1, 2, 3, 4, 5):
            raise ValueError("tiles must be 1..5")
        self.tiles, self.head = tiles, head
        self.w = tiles * TILE
        self.h = tiles * TILE + head
        self.cx = self.w / 2
        self.cy = head + self.w / 2
        self.R = self.w / 2 - 1.5          # radius that just fits the area
        self.s = tiles * TILE / 96.0       # scale vs. the 3-tile design size
        self._polar: dict = {}

    def pivot(self) -> list[int]:
        return [int(self.cx), int(self.cy)]

    def grid(self) -> Grid:
        return Grid(self.w, self.h)

    def blob_r(self, ang: float, R: float, seed: int, wob: float = 0.14, lobes: float = 3.0) -> float:
        """Wobbly radius at angle (seamless around the circle). Angle quantised to 1/720 turn and cached."""
        return R * _blob(int(round((ang / (2 * math.pi)) % 1.0 * 720)) % 720, seed, wob, lobes)

    def polar(self, x, y):
        key = (x, y)
        p = self._polar.get(key)
        if p is None:
            dx, dy = x + .5 - self.cx, y + .5 - self.cy
            p = self._polar[key] = (math.hypot(dx, dy), math.atan2(dy, dx))
        return p



@lru_cache(maxsize=None)
def _blob(q: int, seed: int, wob: float, lobes: float) -> float:
    u = q / 720.0
    n = vnoise(math.cos(2 * math.pi * u) * lobes + 9, math.sin(2 * math.pi * u) * lobes + 9, seed)
    return 1 - wob + 2 * wob * n


def loop_noise(x: float, y: float, t: float, seed: int, scale: float, drift: float = 2.0) -> float:
    """Value noise whose sample point travels a circle in time → seamless when t goes 0→1."""
    a = 2 * math.pi * t
    return vnoise(x / scale + drift * math.cos(a), y / scale + drift * math.sin(a), seed)


def fbm(x, y, seed, scale, octaves=2):
    v, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        v += amp * vnoise(x / scale * (2 ** o), y / scale * (2 ** o), seed + o * 31)
        tot += amp
        amp *= 0.5
    return v / tot


def contour(g: Grid, color: int, only_on=None) -> None:
    """Dark 1px contour around g's pixels (outside only)."""
    src = g.copy()
    src.outline(color)
    for y in range(g.h):
        for x in range(g.w):
            if src.px[y][x] == color and g.px[y][x] is None:
                if only_on is None or only_on.get(x, y) is not None:
                    g.set(x, y, color)


def flame(g: Grid, x: float, y: float, h: float, w: float, ramp: list[int], seed: int, t: float = 0.0) -> None:
    """Small upright flame tongue rooted at (x, y), teardrop-shaped and swaying.
    ramp = [outer/dark, mid, inner, core]: outer colour on the rim and the tip, core only low in the middle."""
    if h < 1:
        return
    for yy in range(int(y - h) - 1, int(y) + 2):
        v = (y - yy) / h                       # 0 base → 1 tip
        if not -0.15 <= v <= 1:
            continue
        vv = max(0.0, v)
        sway = math.sin(vv * 2.6 + t * 2 * math.pi + seed) * w * 0.45 * vv
        half = w * (math.sin(math.pi * min(1, (vv + 0.18) / 1.18)) ** 0.9) * (1 - 0.55 * vv)
        if v < 0:
            half = w * 0.7 * (1 + v / 0.15)
        for xx in range(int(x - half - 3), int(x + half + 4)):
            dd = abs(xx + .5 - x - sway)
            if dd <= half:
                q = dd / max(half, .5)
                heat = (1 - q) * (1 - vv) ** 0.7
                if q > 0.72 or vv > 0.82:
                    c = ramp[0]
                elif heat > 0.55 and len(ramp) > 3:
                    c = ramp[3]
                elif heat > 0.3:
                    c = ramp[2]
                else:
                    c = ramp[1]
                g.set(xx, yy, c)


def wisps(g: Grid, gr: Ground, t: float, n: int, colors: list[int], seed: int, spread: float = 0.8, rise: float = 26,
          size: float = 2.2, keep=None) -> None:
    """Rising smoke puffs, looping (t 0→1); colours fade along the rise (dark → light)."""
    for k in range(n):
        ph = (t + hash01(k, seed)) % 1.0
        a = 2 * math.pi * hash01(k, seed + 1)
        r = gr.R * spread * math.sqrt(hash01(k, seed + 2))
        x0, y0 = gr.cx + math.cos(a) * r, gr.cy + math.sin(a) * r
        x = x0 + math.sin(ph * 5 + k) * 2 * gr.s
        y = y0 - ph * rise * gr.s
        rad = size * gr.s * (0.6 + ph)
        if keep is not None and not keep(ph):
            continue
        ci = min(len(colors) - 1, int(ph * len(colors)))
        for yy in range(int(y - rad) - 1, int(y + rad) + 2):
            for xx in range(int(x - rad) - 1, int(x + rad) + 2):
                if math.hypot(xx + .5 - x, yy + .5 - y) <= rad and bayer4(xx, yy) > ph * 0.9 - 0.35:
                    g.set(xx, yy, colors[ci])
