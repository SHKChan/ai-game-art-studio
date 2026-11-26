"""Meteor (陨石坠落): top-down ground skill. A warning ring marks the target, a flaming rock falls in from the
top-right, explodes in a fire dome with flying debris and leaves a smoking, glowing crater. Plays once."""
from __future__ import annotations

import math

from ._ground import Ground, flame, wisps
from .raster import DocBuilder, Grid, bayer4, hash01, vnoise

DESCRIPTION = "Top-down meteor strike for a grid: warning ring, flaming rock falls, fire-dome explosion, smoking crater."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5},
          "color": {"type": "string", "default": "fire", "enum": ["fire", "arcane", "frost"]}}
# 0 outline 1-3 rock | 4 deep 5 mid 6 bright 7 pale 8 white | 9-11 smoke | 12 warning | 13 char
PALETTES = {
    "fire": ["#1a0c0a", "#3a2420", "#5e3a2c", "#8a5a3e", "#b8281a", "#f0661c", "#ffb02a", "#ffe68a", "#fffaf0",
             "#3a3236", "#5c5258", "#857a80", "#ff3a2a", "#24140f"],
    "arcane": ["#120a1e", "#2a1e40", "#463462", "#6a5490", "#5a1aa8", "#9a3ae8", "#d07aff", "#f0c8ff", "#fff6ff",
               "#2e2a3a", "#4a4458", "#6e6880", "#e040ff", "#1a1226"],
    "frost": ["#0a1020", "#1e2e48", "#34507a", "#5c84b0", "#1a50a8", "#2a90e0", "#68d0ff", "#c4f0ff", "#ffffff",
              "#2c3440", "#46505e", "#6a7684", "#40c8ff", "#121a2a"],
}
# frame: (meteor progress or None, stage)
STAGES = ["warn", "fall", "fall", "fall", "flash", "boom", "ring", "crater", "crater", "crater", "cool", "cool"]
FALL = {1: 0.3, 2: 0.62, 3: 0.88}
DUR = [90, 70, 60, 50, 50, 60, 70, 90, 100, 110, 120, 160]


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=32 if t >= 2 else 20)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, color: str = "fire", **_):
    gr = _ground(tiles)
    s, R, cx, cy = gr.s, gr.R, gr.cx, gr.cy
    OUT, RK0, RK1, RK2, F0, F1, F2, F3, F4, SM0, SM1, SM2, WARN, CH = range(14)
    d = DocBuilder(f"meteor-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_ground, l_fx, l_rock, l_smoke = d.layer("crater & marks"), d.layer("fire"), d.layer("meteor & debris"), d.layer("smoke")
    d.add_frames(len(STAGES) - 1, 80)
    sx, sy = gr.w + 6 * s, -4 * s                     # entry point (top-right, just outside)
    crater_r = R * 0.42

    def crater(g: Grid, glow: float):
        """Scorch ring, raised rim and dark bowl with glowing cracks (glow 0..1)."""
        for y in range(gr.h):
            for x in range(gr.w):
                dist, ang = gr.polar(x, y)
                rr = gr.blob_r(ang, crater_r, 5, 0.12)
                if dist <= rr * 0.78:
                    n = vnoise(x / (3 * s + .5), y / (3 * s + .5), 7)
                    lit = (x + .5 - cx) + (y + .5 - cy) > 0           # inner wall facing the light (bottom-right)
                    g.set(x, y, RK0 if lit and dist > rr * 0.55 else (CH if n < 0.62 else RK0))
                elif dist <= rr:
                    up = -((x + .5 - cx) + (y + .5 - cy)) / (dist * 1.41 + 1e-6)
                    g.set(x, y, RK2 if up > 0.35 else (RK1 if up > -0.4 else RK0))
                elif dist <= gr.blob_r(ang, R * 0.92, 9, 0.16):
                    e = (dist - rr) / (R * 0.92 - rr)
                    if bayer4(x, y) > e * 1.1 - 0.15:
                        g.set(x, y, CH if hash01(x, y, 2) > 0.2 else OUT)
        if glow > 0:
            for k in range(6 + tiles):
                a = 2 * math.pi * (k + hash01(k, 3)) / (6 + tiles)
                x, y = cx, cy
                for i in range(int(crater_r * (0.5 + 0.5 * glow) / (2 * s + .1))):
                    a += (hash01(k, i, 4) - .5) * .8
                    nx, ny = x + math.cos(a) * 2 * s, y + math.sin(a) * 2 * s
                    g.line(x, y, nx, ny, F2 if glow > .6 and i < 3 else (F1 if glow > .3 else F0))
                    x, y = nx, ny

    def warn_ring(g: Grid, fi):
        r = R * (0.75 if fi == 0 else 0.9)
        for k in range(48):
            if k % 4 == 3:
                continue
            a = 2 * math.pi * (k + fi * 0.5) / 48
            g.set(cx + math.cos(a) * r, cy + math.sin(a) * r, WARN)
            if tiles > 1:
                g.set(cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1), F0)

    def shadow(g: Grid, p):
        r = R * (0.15 + 0.35 * p)
        g.ellipse(cx, cy, r, r * 0.85, lambda x, y: OUT if bayer4(x, y) < 0.35 + 0.5 * p else None)

    def rock(g: Grid, f: Grid, x, y, r):
        """Burning meteor + flame trail pointing back to the entry point."""
        ux, uy = sx - x, sy - y
        L = math.hypot(ux, uy) or 1
        ux, uy = ux / L, uy / L
        for k in range(16):                         # trail: overlapping blobs, cooler and thinner further back
            q = k / 15
            tx, ty = x + ux * q * 40 * s, y + uy * q * 40 * s
            rr = r * (1.25 - 0.95 * q) + 0.5
            col = F3 if q < 0.15 else (F2 if q < 0.4 else (F1 if q < 0.7 else F0))
            for yy in range(int(ty - rr) - 1, int(ty + rr) + 2):
                for xx in range(int(tx - rr) - 1, int(tx + rr) + 2):
                    if math.hypot(xx + .5 - tx, yy + .5 - ty) <= rr * (0.75 + 0.35 * vnoise(xx * .5, yy * .5, k)):
                        f.set(xx, yy, col)
        for yy in range(int(y - r) - 1, int(y + r) + 2):
            for xx in range(int(x - r) - 1, int(x + r) + 2):
                dx, dy = xx + .5 - x, yy + .5 - y
                dist = math.hypot(dx, dy)
                if dist <= r:
                    facing = -(dx * ux + dy * uy) / (dist + 1e-6)          # +1 = front (heated side)
                    pit = vnoise(xx / 2.0, yy / 2.0, 3) > 0.7
                    c = F2 if facing > 0.55 and dist > r * 0.5 else (RK2 if facing > 0 else RK1)
                    g.set(xx, yy, RK0 if pit else c)
        contour(g, OUT)

    for fi, st in enumerate(STAGES):
        gd, fx, rk, sm = gr.grid(), gr.grid(), gr.grid(), gr.grid()
        if st in ("warn", "fall"):
            warn_ring(gd, fi)
            p = FALL.get(fi, 0.05)
            shadow(gd, p)
            if st == "fall":
                x, y = sx + (cx - sx) * p, sy + (cy - sy) * p
                rock(rk, fx, x, y, (6.5 + 3.5 * p) * s + 1)
        elif st == "flash":
            r = R * 0.62
            fx.ellipse(cx, cy, r * 1.12, r * 1.12, lambda x, y: F2 if bayer4(x, y) < 0.5 else None)
            fx.ellipse(cx, cy, r, r, F3)
            fx.ellipse(cx, cy, r * 0.82, r * 0.82, lambda x, y: F4 if bayer4(x, y) < 0.6 else F3)
            fx.ellipse(cx, cy, r * 0.62, r * 0.62, F4)
            for k in range(8):
                a = k * math.pi / 4 + .2
                fx.line(cx + math.cos(a) * r, cy + math.sin(a) * r, cx + math.cos(a) * R * 1.05, cy + math.sin(a) * R * 1.05, F3)
        else:
            glow = {"boom": 1, "ring": 1, "crater": 0.8, "cool": 0.35}[st] * (0.7 if fi == 11 else 1) * (0.85 if fi == 9 else 1)
            crater(gd, glow if fi < 11 else 0.15)
            if st == "boom":
                r = R * 0.78
                def dome(x, y):
                    dx, dy = x + .5 - cx, y + .5 - cy
                    q = math.hypot(dx, dy * 1.1 + r * 0.15) / r
                    if q > 1 - 0.18 * vnoise(x * .3, y * .3, 4):
                        return None
                    v = (1 - q) + 0.3 * (vnoise(x * .25, y * .25, 8) - .5) - (dy / r) * 0.15
                    return F4 if v > .75 else F3 if v > .55 else F2 if v > .33 else F1 if v > .15 else F0
                fx.field(dome)
            if st == "ring":
                rr = R * 0.96
                for y in range(gr.h):
                    for x in range(gr.w):
                        dist, ang = gr.polar(x, y)
                        band = abs(dist - rr * (0.88 + 0.08 * vnoise(ang * 3, 1, 2)))
                        if band < 3 * s + 1 and vnoise(x * .35, y * .35, 6) > 0.3:
                            fx.set(x, y, F2 if band < 1.2 * s else (F1 if band < 2.2 * s else F0))
                for k in range(5 + 2 * tiles):
                    a = 2 * math.pi * hash01(k, 50)
                    rr2 = crater_r * 0.9 * math.sqrt(hash01(k, 51))
                    flame(fx, cx + math.cos(a) * rr2, cy + math.sin(a) * rr2, (6 + 8 * hash01(k, 52)) * s, 2.5 * s + .5, [F0, F1, F2, F3], k)
            if st in ("ring", "crater"):                     # debris arcs out and falls
                tt = {"boom": 0.25, "ring": 0.55, "crater": 0.8 + 0.12 * (fi - 7)}[st]
                for k in range(8 + 3 * tiles):
                    a = 2 * math.pi * hash01(k, 60)
                    dist = R * (0.3 + 0.75 * hash01(k, 61)) * tt
                    hgt = 18 * s * hash01(k, 62) * 4 * tt * (1 - tt)
                    x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist - hgt
                    if tt < 1:
                        r = (1.0 + 1.2 * hash01(k, 63)) * s + 0.4
                        rk.ellipse(x, y, r, r, RK1)
                        rk.set(x - r * .5, y - r * .5, F2 if st != "crater" else RK2)
                if st != "boom":
                    contour(rk, OUT)
            if st in ("crater", "cool"):
                ph = (fi - 7) / 5
                wisps(sm, gr, ph, 5 + 2 * tiles, [SM0, SM1, SM2], 70, spread=0.45, rise=40, size=3.2 if fi < 10 else 2.4)
                for k in range(6):
                    q = (ph + hash01(k, 80)) % 1
                    if q < 0.8 and fi < 11:
                        fx.set(cx + (hash01(k, 81) - .5) * crater_r * 1.4, cy - q * 30 * s, F2 if q < .4 else F0)
        d.paint(gd, l_ground, fi)
        d.paint(fx, l_fx, fi)
        d.paint(rk, l_rock, fi)
        d.paint(sm, l_smoke, fi)
        d.duration(fi, DUR[fi])
    d.tag("fall", 0, 3)
    d.tag("impact", 4, len(STAGES) - 1)
    return d.calls


def contour(g: Grid, c: int) -> None:
    from ._ground import contour as _c
    _c(g, c)
