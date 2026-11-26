"""Lava burn (熔岩灼地): top-down ground skill for a tactics grid. Glowing cracks split the ground, magma bursts
out and floods the area, then the pool burns (seamless loop: flowing lava, crust plates, bubbles, flame
tongues, smoke) and finally cools into scorched rock. Tags: cast / burn (loop) / fade."""
from __future__ import annotations

import math

from ._ground import Ground, contour, flame, loop_noise, wisps
from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Top-down lava burn for a grid: cracks glow, magma floods the tiles, burns in a loop, then cools (tags cast/burn/fade)."
ASSET_TYPE = "effect"
FULL_BLEED = True
PARAMS = {"tiles": {"type": "int", "default": 3, "min": 1, "max": 5},
          "color": {"type": "string", "default": "lava", "enum": ["lava", "soulfire", "acid"]},
          "phase": {"type": "string", "default": "all", "enum": ["all", "cast", "burn", "fade"]}}

# 0 char-dark 1 char 2 crust 3 crust-light | 4 deep 5 red 6 orange 7 yellow 8 pale 9 white | 10-12 smoke
PALETTES = {
    "lava": ["#140a0a", "#2a1712", "#45261c", "#6a3a26", "#7a160e", "#c22e16", "#f06a1c", "#ffaa2a", "#ffe07a", "#fff8de",
             "#2e2629", "#4a4044", "#6e6468"],
    "soulfire": ["#080a16", "#141a2e", "#202a48", "#34406a", "#122a7a", "#1c58c8", "#26a0f0", "#5ad8ff", "#b0f4ff", "#f4feff",
                 "#22263a", "#3a4058", "#5c6480"],
    "acid": ["#0a120a", "#16241a", "#223a24", "#36562e", "#1a5a12", "#2e9a1c", "#5ad02a", "#a8f040", "#e0ff90", "#f8ffe0",
             "#262e24", "#3e4a3a", "#5e6c58"],
}
CAST, BURN, FADE = 6, 6, 4


def _cracks(gr: Ground, seed: int):
    """Branching crack polylines radiating from the centre: list of (points, depth)."""
    out = []

    def grow(x, y, ang, length, depth, k):
        pts = [(x, y)]
        steps = max(2, int(length / (3 * gr.s)))
        for i in range(steps):
            ang += (hash01(k, i, seed) - 0.5) * 0.9
            x += math.cos(ang) * 3 * gr.s
            y += math.sin(ang) * 3 * gr.s
            pts.append((x, y))
            if depth < 2 and hash01(k, i, seed + 7) < 0.18:
                grow(x, y, ang + (0.8 if hash01(k, i, 3) < .5 else -0.8), length * 0.45, depth + 1, k * 13 + i)
        out.append((pts, depth))
    n = 5 + gr.tiles
    for k in range(n):
        grow(gr.cx, gr.cy, 2 * math.pi * (k + 0.4 * hash01(k, seed)) / n, gr.R * (0.75 + 0.25 * hash01(k, 2)), 0, k)
    return out


def _draw_cracks(g: Grid, cracks, reach: float, cols, gr: Ground):
    """Draw cracks up to `reach` (0..1 of their length). cols = (glow, core)."""
    for pts, depth in cracks:
        n = max(1, int(len(pts) * min(1.0, reach * (1.25 - 0.25 * depth))))
        for i in range(n - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            g.line(x0, y0, x1, y1, cols[1] if depth == 0 and i < n * 0.7 else cols[0])
            if depth == 0 and i < n * 0.5 and gr.tiles >= 2:
                g.line(x0 + 1, y0, x1 + 1, y1, cols[0])


def _ground(tiles) -> Ground:
    t = int(tiles)
    return Ground(t, head=32 if t >= 2 else 16)


def pivot(tiles: int = 3, **_):
    """Engine pivot: centre of the ground cells (see _ground.py)."""
    return _ground(tiles).pivot()


def build(tiles: int = 3, color: str = "lava", phase: str = "all", **_):
    gr = _ground(tiles)
    pal = PALETTES[color]
    CH0, CH1, CR0, CR1, L0, L1, L2, L3, L4, L5, SM0, SM1, SM2 = range(13)
    d = DocBuilder(f"lava-burn-{color}-{tiles}t", gr.w, gr.h)
    d.palette(pal)
    l_scorch, l_lava, l_fx, l_smoke = d.layer("scorch"), d.layer("lava"), d.layer("flames & bubbles"), d.layer("smoke")
    seed = {"lava": 11, "soulfire": 23, "acid": 37}[color]
    cracks = _cracks(gr, seed)
    s = gr.s

    # frame plan: (kind, local t)
    plan = [("cast", i / CAST) for i in range(CAST)] + [("burn", i / BURN) for i in range(BURN)] + [("fade", (i + 1) / FADE) for i in range(FADE)]
    if phase != "all":
        plan = [p for p in plan if p[0] == phase]
    durations = {"cast": [70, 70, 60, 60, 80, 90], "burn": [110] * BURN, "fade": [110, 120, 130, 160]}
    d.add_frames(len(plan) - 1, 100)

    def pool_px(x, y, R, t, heat=1.0):
        """Lava pool colour at (x, y) for pool radius R (wobbly) — None outside."""
        dist, ang = gr.polar(x, y)
        rr = gr.blob_r(ang, R, seed)
        if dist > rr:
            return None
        edge = (rr - dist) / max(rr, 1)                        # 0 at rim → 1 at centre
        flow = loop_noise(x, y, t, seed, 7 * s, 1.6)
        crust = loop_noise(x + 40, y, t, seed + 5, 6 * s, 0.9)
        v = 0.05 + 0.55 * flow + 0.35 * min(1, edge * 2.0)
        v *= heat
        if crust > 0.67 and edge > 0.12:                       # floating crust plate with a lit top edge
            return CR1 if loop_noise(x + 40, y - 1, t, seed + 5, 6 * s, 0.9) <= 0.67 else CR0
        if crust > 0.63 and edge > 0.1:
            return L3 if heat > .5 else CR0                   # glowing seam around plates
        if edge < 0.035:
            return CR0
        if edge < 0.08:
            return L0 if heat > .4 else CR0
        k = v + (bayer4(x, y) - 0.5) * 0.12
        ramp = [L0, L1, L1, L2, L3] if heat > .6 else [CR0, L0, L1, L2, L2]
        return ramp[min(4, max(0, int(k * 5)))]

    def scorch(g: Grid, R, amount=1.0):
        """Charred ground under / around the pool (dithered edge)."""
        for y in range(gr.h):
            for x in range(gr.w):
                dist, ang = gr.polar(x, y)
                rr = gr.blob_r(ang, R, seed + 3, 0.18)
                if dist <= rr:
                    e = (rr - dist) / max(rr, 1)
                    if e < 0.12 and bayer4(x, y) > e / 0.12 * amount:
                        continue
                    g.set(x, y, CH1 if hash01(x, y, 4) > 0.15 else CH0)

    fi = 0
    for kind, t in plan:
        sc, lv, fx, sm = gr.grid(), gr.grid(), gr.grid(), gr.grid()
        R = gr.R
        if kind == "cast":
            i = int(round(t * CAST))
            reach = [0.25, 0.55, 0.9, 1, 1, 1][i]
            pool = [0, 0, 0.3, 0.6, 0.85, 0.97][i] * R
            scorch(sc, R * (0.35 + 0.6 * reach))
            _draw_cracks(sc, cracks, reach, (L1, L3 if i < 2 else L5), gr)
            if pool:
                lv.field(lambda x, y: pool_px(x, y, pool, t * 0.5))
            if i == 0:
                for k in range(6):                                  # glints at the crack origin
                    a = k * math.pi / 3
                    fx.set(gr.cx + math.cos(a) * 2 * s, gr.cy + math.sin(a) * 2 * s, L4)
                fx.set(gr.cx, gr.cy, L5)
            if i in (2, 3, 4):                                      # eruption: blobs flung upward and out
                for k in range(10 + 4 * gr.tiles):
                    a = 2 * math.pi * hash01(k, seed, 1)
                    rr = pool * (0.3 + 0.7 * hash01(k, 2))
                    up = (i - 1) * (6 + 10 * hash01(k, 3)) * s
                    x = gr.cx + math.cos(a) * rr * (1 + (i - 2) * 0.25)
                    y = gr.cy + math.sin(a) * rr - up + (i - 2) ** 2 * 3 * s
                    r = (1.6 - 0.4 * (i - 2)) * s + 0.4
                    fx.ellipse(x, y, r, r, L2)
                    fx.set(x, y, L4)
                    fx.set(x, y + r, L0)
            if i >= 3:
                for k in range(4 + 2 * gr.tiles):
                    a = 2 * math.pi * hash01(k, 9)
                    rr = pool * 0.7 * math.sqrt(hash01(k, 10))
                    flame(fx, gr.cx + math.cos(a) * rr, gr.cy + math.sin(a) * rr, (8 + 10 * hash01(k, 11)) * s * (1.3 if i == 3 else 1),
                          (2.4 + hash01(k, 12)) * s + .5, [L1, L2, L3, L4], k, t)
        elif kind == "burn":
            scorch(sc, R)
            lv.field(lambda x, y: pool_px(x, y, R * 0.97, 0.5 + t))
            for k in range(5 + 3 * gr.tiles):                       # bubbles: swell → pop ring, staggered
                ph = (t + hash01(k, seed, 20)) % 1.0
                a = 2 * math.pi * hash01(k, 21)
                rr = R * 0.8 * math.sqrt(hash01(k, 22))
                x, y = gr.cx + math.cos(a) * rr, gr.cy + math.sin(a) * rr
                if ph < 0.5:
                    r = (0.6 + ph * 3.4) * s + 0.3
                    fx.ellipse(x, y, r, r, L2)
                    fx.set(x - r * .4, y - r * .4, L5 if r > 1.5 else L4)
                elif ph < 0.68:
                    r = 2.6 * s + 1
                    for q in range(8):
                        aa = q * math.pi / 4
                        fx.set(x + math.cos(aa) * r, y + math.sin(aa) * r * 0.8, L4)
                    fx.set(x, y - r - 1, L3)
            for k in range(3 + 2 * gr.tiles):                       # flame tongues licking the surface
                ph = (t + hash01(k, seed, 30)) % 1.0
                a = 2 * math.pi * hash01(k, 31)
                rr = R * 0.85 * math.sqrt(hash01(k, 32))
                h = (5 + 9 * math.sin(math.pi * ph)) * s
                flame(fx, gr.cx + math.cos(a) * rr, gr.cy + math.sin(a) * rr, h, (2.6 + hash01(k, 33)) * s + .8,
                      [L1, L2, L3, L4], k, ph)
            for k in range(4 + 2 * gr.tiles):                       # embers drifting up
                ph = (t + hash01(k, 40)) % 1.0
                a = 2 * math.pi * hash01(k, 41)
                rr = R * 0.9 * math.sqrt(hash01(k, 42))
                fx.set(gr.cx + math.cos(a) * rr + math.sin(ph * 6 + k) * 2, gr.cy + math.sin(a) * rr - ph * 22 * s, L3 if ph < .6 else L1)
            wisps(sm, gr, t, 2 + gr.tiles, [SM2, SM1, SM0], seed + 50, rise=30, size=3.0)
        else:  # fade
            i = int(round(t * FADE))                                # 1..4
            scorch(sc, R)
            heat = [1, 0.75, 0.45, 0.2, 0.0][i]
            cool_r = R * (1 - 0.22 * i)
            def cooled(x, y):
                dist, ang = gr.polar(x, y)
                if dist > gr.blob_r(ang, R * 0.97, seed):
                    return None
                if dist < gr.blob_r(ang, cool_r, seed + 8, 0.2):
                    return pool_px(x, y, R * 0.97, 0.5, heat)
                n = loop_noise(x, y, 0.5, seed + 5, 6 * s, 0)
                return CR1 if n > 0.62 else (CR0 if n > 0.3 else CH1)
            lv.field(cooled)
            if i < 4:
                _draw_cracks(lv, cracks, 1.0 - 0.25 * i, (L4 if i < 3 else CR1, L0 if i < 2 else L4), gr)
            wisps(sm, gr, 0.15 * i, 5 + 2 * gr.tiles, [SM2, SM1, SM0], seed + 60, rise=34, size=2.6)
            for k in range(6):
                ph = (0.2 * i + hash01(k, 70)) % 1.0
                a = 2 * math.pi * hash01(k, 71)
                rr = R * 0.6 * math.sqrt(hash01(k, 72))
                if i < 4:
                    fx.set(gr.cx + math.cos(a) * rr, gr.cy + math.sin(a) * rr - ph * 16 * s, L2 if i < 2 else L0)
        d.paint(sc, l_scorch, fi)
        d.paint(lv, l_lava, fi)
        d.paint(fx, l_fx, fi)
        d.paint(sm, l_smoke, fi)
        d.duration(fi, durations[kind][min(len(durations[kind]) - 1, int(round(t * {"cast": CAST, "burn": BURN, "fade": FADE}[kind])) - (1 if kind == "fade" else 0))])
        fi += 1
    start = 0
    for name, n in (("cast", CAST), ("burn", BURN), ("fade", FADE)):
        if phase in ("all", name):
            d.tag(name, start, start + n - 1)
            start += n
    return d.calls
