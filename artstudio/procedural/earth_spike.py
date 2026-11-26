"""Earth spike (地刺): top-down ground skill. The ground rumbles and cracks, faceted rock spikes burst up on
every cell of the area with a dust ring, hold, then crumble into rubble. Plays once."""
from __future__ import annotations

import math

from ._ground import Ground, contour
from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Top-down earth spikes for a grid: ground cracks, rock spikes burst up on every cell, dust ring, crumble."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5},
          "color": {"type": "string", "default": "earth", "enum": ["earth", "crystal", "ice"]}}
# 0 outline 1 dark 2 mid 3 light 4 highlight 5 dust 6 dust light 7 crack
PALETTES = {
    "earth": ["#1c140e", "#4a3424", "#7a5838", "#a8845a", "#dcc08e", "#7e6e58", "#b0a084", "#2a1e16"],
    "crystal": ["#160c24", "#3e2468", "#6a40a8", "#a878e0", "#ecd4ff", "#6e6280", "#a89cba", "#24163a"],
    "ice": ["#0c1a30", "#1f4f8f", "#3e8ed0", "#8fd2f4", "#f0fcff", "#7a92a8", "#b8cad8", "#16263e"],
}
GROW = [0, 0.5, 1.12, 1.0, 1.0, 1.0, 0.7, 0.35, 0]
DUR = [90, 50, 50, 70, 120, 120, 80, 90, 140]


def _spikes(gr: Ground):
    out = []
    for ty in range(gr.tiles):
        for tx in range(gr.tiles):
            k = ty * 7 + tx
            bx = (tx + 0.5 + (hash01(k, 1) - .5) * 0.3) * 32
            by = gr.head + (ty + 0.62 + (hash01(k, 2) - .5) * 0.2) * 32
            out.append((bx, by, 8 + 2 * hash01(k, 3), 26 + 8 * hash01(k, 4), (hash01(k, 5) - .5) * 5, k))
            for j in range(2):                                        # small satellites
                a = 2 * math.pi * hash01(k, j, 6)
                out.append((bx + math.cos(a) * 10, by + math.sin(a) * 6, 3 + hash01(k, j, 7), 9 + 5 * hash01(k, j, 8),
                            (hash01(k, j, 9) - .5) * 4, k * 10 + j + 100))
    return sorted(out, key=lambda p: p[1])


def _spike(g: Grid, bx, by, bw, h, lean, k, cols):
    """Faceted rock spike: lit left face / shadowed right face, each with a vertical gradient (lighter towards the
    tip), dithered band edges, rock speckle and a ridge highlight."""
    OUT, D, M, L, H = cols
    tip = (bx + lean, by - h)
    front = (bx + bw * 0.15, by + bw * 0.4)
    left, right, mid = Grid(g.w, g.h), Grid(g.w, g.h), Grid(g.w, g.h)
    left.polygon([(bx - bw, by), tip, front], 1)
    right.polygon([front, tip, (bx + bw, by)], 1)
    mid.polygon([(bx - bw * 0.35, by + bw * 0.15), tip, front], 1)
    for y in range(int(tip[1]) - 1, int(by + bw) + 2):
        v = max(0.0, min(1.0, (by - y) / max(h, 1)))          # 0 base → 1 tip
        for x in range(int(bx - bw) - 2, int(bx + bw) + 3):
            if left.get(x, y):
                t = 0.45 + 0.5 * v + (bayer4(x, y) - 0.5) * 0.3
                c = H if t > 0.92 else (L if t > 0.55 else M)
            elif mid.get(x, y):
                t = 0.3 + 0.5 * v + (bayer4(x, y) - 0.5) * 0.3
                c = L if t > 0.62 else M
            elif right.get(x, y):
                t = 0.15 + 0.45 * v + (bayer4(x, y) - 0.5) * 0.3
                c = M if t > 0.5 else D
            else:
                continue
            if hash01(x, y, k) < 0.08:                         # rock speckle
                c = D if c != D else M
            g.set(x, y, c)
    g.line(front[0], front[1], tip[0], tip[1], H)
    if h > 12:                                                 # strata notches
        for f in (0.35, 0.6):
            y = by - h * (f + 0.1 * hash01(k, f * 10))
            w = bw * (1 - f) * 0.8
            g.line(bx - w + lean * f, y + 1, bx - w * 0.2 + lean * f, y - 1, D)


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=32)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, color: str = "earth", **_):
    gr = _ground(tiles)
    OUT, D, M, L, H, DU, DL, CR = range(8)
    d = DocBuilder(f"earth-spike-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_ground, l_sp, l_dust = d.layer("cracks & rubble"), d.layer("spikes"), d.layer("dust")
    d.add_frames(len(GROW) - 1, 80)
    spikes = _spikes(gr)
    for fi, grow in enumerate(GROW):
        gd, sp, du = gr.grid(), gr.grid(), gr.grid()
        for bx, by, bw, h, lean, k in spikes:                          # cracks around each base
            n = 3 if bw > 5 else 2
            for j in range(n):
                a = 2 * math.pi * (j + hash01(k, j, 20)) / n
                ln = bw * (1.3 if fi == 0 else 1.9)
                x, y = bx, by
                for i in range(3):
                    a += (hash01(k, j, i) - .5) * .9
                    nx, ny = x + math.cos(a) * ln / 3, y + math.sin(a) * ln / 3 * 0.7
                    gd.line(x, y, nx, ny, CR if fi < 8 else D)
                    x, y = nx, ny
            if fi >= 2:
                gd.ellipse(bx, by + 1, bw * 1.05, bw * 0.45, CR)       # pit
            if fi == 0:
                for j in range(3):
                    gd.set(bx + (hash01(k, j, 30) - .5) * bw * 2, by - 1 - hash01(k, j, 31) * 3, DU)
        for bx, by, bw, h, lean, k in spikes:
            g = grow * (0.85 + 0.3 * hash01(k, 40)) if fi in (1, 2) else grow
            if g > 0.05:
                _spike(sp, bx, by, bw * min(1, 0.6 + g * 0.5), h * g, lean * g, k, (OUT, D, M, L, H))
            if fi >= 6:                                                # falling chunks + rubble
                for j in range(4 if bw > 5 else 2):
                    q = (fi - 5) / 3
                    x = bx + (hash01(k, j, 50) - .5) * bw * 3 * (0.5 + q)
                    y = by - h * (0.6 - 0.5 * q) * hash01(k, j, 51) - 2
                    r = 1.0 + hash01(k, j, 52) * 1.3
                    (gd if fi == 8 else sp).ellipse(x, max(y, by - 30) if fi < 8 else by + (hash01(k, j, 53) - .3) * 4, r, r * .8, M)
        contour(sp, OUT)
        if fi in (2, 3, 4, 5, 6):                                      # dust ring billowing from the bases
            q = (fi - 2) / 4
            for bx, by, bw, h, lean, k in spikes:
                if bw < 5:
                    continue
                for j in range(7):
                    a = 2 * math.pi * j / 7 + hash01(k, j, 60)
                    rr = bw * (1.3 + 1.6 * q)
                    x, y = bx + math.cos(a) * rr, by + math.sin(a) * rr * 0.55 - q * 3
                    r = (2.6 - 1.6 * q) + hash01(k, j, 61)
                    du.ellipse(x, y, r, r * 0.8, lambda xx, yy: (DL if yy < y else DU) if bayer4(xx, yy) > q * 0.8 else None)
        d.paint(gd, l_ground, fi)
        d.paint(sp, l_sp, fi)
        d.paint(du, l_dust, fi)
        d.duration(fi, DUR[fi])
    d.tag("erupt", 0, 3)
    d.tag("hold", 4, 5)
    d.tag("crumble", 6, 8)
    return d.calls
