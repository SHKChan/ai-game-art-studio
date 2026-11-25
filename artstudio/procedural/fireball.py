"""8-frame seamless-loop fireball travelling right: white-hot core, banded flame, flickering tongues, embers."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, bayer4, hash01, vnoise

DESCRIPTION = "Looping 8-frame fireball projectile (faces right) with hot core, flame tongues and trailing embers."
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64}, "frames": {"type": "int", "default": 8}}

PALETTE = ["#2b0b12", "#6e1414", "#b8261a", "#ec5a16", "#ff9a2a", "#ffd65a", "#fff6c8", "#ffffff"]
RAMP = [1, 2, 3, 4, 5, 6, 7]


def heat(x, y, f, n, s):
    cx, cy, rh = 41 * s, 32 * s, 10.5 * s
    tail_len = 33 * s
    w = f / n
    def noise(px, py):
        v = 2.6 * s
        a = vnoise(px / (5 * s) + v * f / s * 0.25, py / (5 * s), 11)
        b = vnoise(px / (5 * s) + v * (f - n) / s * 0.25, py / (5 * s), 11)
        return (1 - w) * a + w * b
    dx, dy = x + .5 - cx, y + .5 - cy
    d = math.hypot(dx, dy)
    h_head = 1.0 - d / rh
    hv = h_head
    if dx < rh * 0.3:
        u = max(0.0, (cx - (x + .5)) / tail_len)
        if u <= 1:
            phase = 2 * math.pi * f / n
            wob = 2.2 * s * math.sin(u * 7.5 - phase) * u + 1.4 * s * math.sin(u * 13 - 2 * phase + 1.3) * u
            r = rh * (1 - u) ** 0.85
            h_tail = (1 - abs(dy - wob) / max(0.5, r)) * (1 - u) ** 0.5
            hv = max(hv, h_tail * 0.95)
    nz = noise(x, y)
    hv = hv + (nz - 0.5) * 0.6 * min(1.0, max(0.0, 1 - hv) + 0.15)
    return hv


def build(size: int = 64, frames: int = 8, **_):
    s = size / 64.0
    d = DocBuilder("fireball", size, size)
    d.palette(PALETTE)
    l_emb = d.layer("embers")
    l_flame = d.layer("flame")
    l_core = d.layer("core")
    d.add_frames(frames - 1, 80)
    for f in range(frames):
        flame, core, emb = Grid(size, size), Grid(size, size), Grid(size, size)

        def px(x, y):
            h = heat(x, y, f, frames, s)
            if h <= 0.0:
                return None
            t = min(0.999, h * 0.98)
            band = t * len(RAMP)
            i = int(band)
            if i + 1 < len(RAMP) and band - i > 0.6 and bayer4(x, y) < (band - i - 0.6) / 0.4:
                i += 1
            return RAMP[i]
        full = Grid(size, size)
        full.field(px)
        for y in range(size):
            for x in range(size):
                v = full.px[y][x]
                if v is None:
                    continue
                (core if v >= 6 else flame).set(x, y, v)
        # dark rim on the leading (front) edge for readability against bright backgrounds
        rim = full.copy()
        rim.outline(0)
        for y in range(size):
            for x in range(size):
                if rim.px[y][x] == 0 and full.px[y][x] is None and x > 38 * s:
                    flame.set(x, y, 0)
        # embers drift backwards, periodic over the loop
        for k in range(9):
            base_x = 30 * s - hash01(k, 1) * 26 * s
            base_y = 32 * s + (hash01(k, 2) - 0.5) * 20 * s
            speed = 10 * s + hash01(k, 3) * 10 * s
            t = (f / frames + hash01(k, 4)) % 1.0
            ex = base_x - t * speed
            ey = base_y + math.sin(t * 6.28 + k) * 2 * s - t * 4 * s
            if ex < 1 or full.get(ex, ey) is not None:
                continue
            c = 6 if t < 0.3 else (5 if t < 0.6 else (3 if t < 0.85 else 1))
            emb.set(ex, ey, c)
            if hash01(k, 5) > 0.6 and t < 0.5:
                emb.set(ex + 1, ey, 4)
        d.paint(emb, l_emb, f)
        d.paint(flame, l_flame, f)
        d.paint(core, l_core, f)
    d.tag("fly", 0, frames - 1)
    return d.calls
