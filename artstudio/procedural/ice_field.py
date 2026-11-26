"""Ice field (冰封大地): top-down ground skill. Frost races out over the area, freezing it into cracked ice with
crystal clusters; it glints while it holds (loop), then shatters. Tags: spread / hold (loop) / shatter."""
from __future__ import annotations

import math

from ._ground import Ground, contour
from .earth_spike import _spike
from .raster import DocBuilder, bayer4, hash01, vnoise

DESCRIPTION = "Top-down ice field for a grid: frost spreads, crystal clusters grow, glints while held (loop), shatters."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5},
          "color": {"type": "string", "default": "ice", "enum": ["ice", "crystal"]}}
# 0 outline 1 deep 2 mid 3 light 4 pale 5 white 6 frost
PALETTES = {
    "ice": ["#0c1a30", "#1f4f8f", "#3e8ed0", "#8fd2f4", "#d4f2ff", "#ffffff", "#a8cce4"],
    "crystal": ["#1a0c2a", "#5a2a8a", "#9a5ad0", "#d49af0", "#f4dcff", "#ffffff", "#c8b0dc"],
}
SPREAD = [0.25, 0.5, 0.78, 0.97, 1.0]
STAGES = [("spread", i) for i in range(5)] + [("hold", i) for i in range(4)] + [("shatter", i) for i in range(4)]
DUR = {"spread": 60, "hold": 120, "shatter": 90}


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=24)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, color: str = "ice", **_):
    gr = _ground(tiles)
    s, R, cx, cy = gr.s, gr.R, gr.cx, gr.cy
    OUT, D, M, L, P, W, FR = range(7)
    d = DocBuilder(f"ice-field-{color}-{tiles}t", gr.w, gr.h)
    d.palette(PALETTES[color])
    l_ice, l_cry, l_fx = d.layer("ice sheet"), d.layer("crystals"), d.layer("glints & shards")
    d.add_frames(len(STAGES) - 1, 80)
    clusters = []
    for k in range(1 + tiles):
        a = 2 * math.pi * (k / (1 + tiles) + 0.3 * hash01(k, 1))
        r = R * (0.62 if k else 0.1) * math.sqrt(hash01(k, 2))
        clusters.append((cx + math.cos(a) * r, cy + math.sin(a) * r, k))
    clusters.sort(key=lambda c: c[1])

    def edge_r(ang, rr):
        spikes = 0.12 * max(0, math.sin(ang * 9 + 1)) ** 3 + 0.1 * vnoise(ang * 4, 0, 3)
        return rr * (0.88 + spikes)

    for fi, (st, i) in enumerate(STAGES):
        ice, cry, fx = gr.grid(), gr.grid(), gr.grid()
        cover = SPREAD[i] if st == "spread" else 1.0
        broken = (i + 1) / 4 if st == "shatter" else 0

        def sheet(x, y):
            dist, ang = gr.polar(x, y)
            rr = edge_r(ang, R * cover)
            if dist > rr:
                return FR if dist < rr + 2 * s + 1 and bayer4(x, y) < 0.4 * (1 - broken) else None
            n = vnoise(x / (6 * s + .5), y / (6 * s + .5), 9)
            cell = abs(n - 0.5) < 0.035 + 0.05 * broken                  # crack lines
            if broken and hash01(int(x / 6), int(y / 6), 3) < broken * 0.9:
                return None if bayer4(x, y) < broken else FR
            if cell:
                return D if broken else M
            if dist > rr - 1.5:
                return P
            shade = (x - y) / (gr.w + gr.h) + 0.15 * vnoise(x / 9, y / 9, 1)
            return L if shade > -0.05 else (P if shade > -0.2 else L)
        ice.field(sheet)
        if st == "hold":                                                  # diagonal glint sweep
            band = -gr.w * 0.6 + (i / 3) * gr.w * 1.6
            for y in range(gr.h):
                for x in range(gr.w):
                    if ice.get(x, y) in (L, P) and abs((x + y - gr.head) - band - gr.w * 0.5) < 2.5 * s + 1:
                        ice.set(x, y, W)
        for bx, by, k in clusters:                                        # crystal clusters
            g = {"spread": max(0, SPREAD[i] * 1.2 - 0.25), "hold": 1, "shatter": 1 - broken}[st]
            if g <= 0.05 or (st == "spread" and math.hypot(bx - cx, by - cy) > R * cover):
                continue
            for j, (dx, h, w) in enumerate(((0, 20, 5.5), (-6, 13, 3.6), (6, 14, 3.8), (2, 8, 2.6))):
                _spike(cry, bx + dx * s, by + (j % 2) * 2 * s, w * s + .5, h * s * g, (dx * 0.4 + (hash01(k, j) - .5) * 3) * s, k * 5 + j, (OUT, M, L, P, W))
        contour(cry, OUT)
        if st == "spread" and i < 4:                                      # frost burst at the leading edge
            for k in range(24):
                a = 2 * math.pi * k / 24 + hash01(k, i)
                rr = edge_r(a, R * cover) + 2 * s
                fx.set(cx + math.cos(a) * rr, cy + math.sin(a) * rr, W if k % 3 == 0 else P)
        if st == "hold":
            for k in range(4 + 2 * tiles):
                if hash01(k, i, 5) < 0.4:
                    x, y = cx + (hash01(k, 6) - .5) * R * 1.6, cy + (hash01(k, 7) - .5) * R * 1.6
                    fx.set(x, y, W); fx.set(x + 1, y, P); fx.set(x - 1, y, P); fx.set(x, y + 1, P); fx.set(x, y - 1, P)
        if st == "shatter":                                               # shards fly up and fall
            for k in range(14 + 4 * tiles):
                a = 2 * math.pi * hash01(k, 8)
                rr = R * 0.9 * math.sqrt(hash01(k, 9)) + broken * 8 * s
                hgt = 22 * s * hash01(k, 10) * 4 * broken * (1 - broken) + 1
                x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr - hgt
                if broken < 1:
                    fx.polygon([(x, y - 2 * s - 1), (x + 1.5 * s + .5, y), (x, y + 1.5 * s), (x - 1.2 * s, y)], L)
                    fx.set(x, y - 1, W)
                elif k % 2 == 0:                                            # last frame: melting slivers on the ground
                    fx.set(x, y, P); fx.set(x + 1, y, L)
            contour(fx, OUT)
        d.paint(ice, l_ice, fi)
        d.paint(cry, l_cry, fi)
        d.paint(fx, l_fx, fi)
        d.duration(fi, DUR[st])
    d.tag("spread", 0, 4)
    d.tag("hold", 5, 8)
    d.tag("shatter", 9, 12)
    return d.calls
