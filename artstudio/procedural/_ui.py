"""Shared UI-kit drawing (themes, bevelled frames, fills, emit helpers) for ui_panel / ui_button / ui_bar / ui_frame.

Everything is computed as hex-colour grids, then painted by palette index (so Pixel Forge colour edits still work).
Frames are designed for **9-slice** scaling: corners and ornaments stay inside `slice_margin(theme)` px from each edge,
borders and fills repeat cleanly in between."""
from __future__ import annotations

import colorsys
import math

from ._icon import OUTLINE
from .raster import DocBuilder, Grid, bayer4, hash01, vnoise

THEMES = {
    # border (dark, mid, light, highlight), fill (top, mid, bottom), accent (dark, mid, light), border width, fill texture
    "classic_blue": {"border": ["#4a5270", "#9aa4c0", "#dfe4f2", "#ffffff"], "fill": ["#3e5ed0", "#26409e", "#121e5e"],
                     "accent": ["#8a5a10", "#e8b830", "#fff0a0"], "bw": 3, "tex": "none"},
    "wood_gold": {"border": ["#5c3a08", "#b07c16", "#eec23c", "#fff4b4"], "fill": ["#7a4a28", "#5e3820", "#3e2414"],
                  "accent": ["#6a1a12", "#c8302a", "#ff7a5a"], "bw": 4, "tex": "planks"},
    "stone_iron": {"border": ["#2e3240", "#5e6676", "#9aa2b4", "#d4d8e4"], "fill": ["#4a4654", "#38343f", "#24212a"],
                   "accent": ["#2a4a8a", "#4a8ae8", "#a8d4ff"], "bw": 4, "tex": "blocks"},
    "parchment": {"border": ["#4a2a14", "#7a4a26", "#a8723e", "#d8a868"], "fill": ["#f2dcac", "#e2c48a", "#c8a46a"],
                  "accent": ["#5a0e14", "#a8202a", "#e85a4a"], "bw": 3, "tex": "paper"},
}
TEXT = {"classic_blue": "#ffffff", "wood_gold": "#fff0c8", "stone_iron": "#e8ecf4", "parchment": "#3a2414"}


def slice_margin(theme: str) -> int:
    return THEMES[theme]["bw"] + 5


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    a, b = _hex(a), _hex(b)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def grey(c, amount=0.85, dark=0.1):
    r, g, b = (v / 255 for v in _hex(c))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, l * (1 - dark), s * (1 - amount))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def blank(w, h):
    return [[None] * w for _ in range(h)]


def rounded_inside(x, y, w, h, r):
    """True if (x, y) lies inside a w×h rect with stepped corners of radius r."""
    cx = r - 1 - x if x < r else (x - (w - r) if x >= w - r else -1)
    cy = r - 1 - y if y < r else (y - (h - r) if y >= h - r else -1)
    if cx < 0 or cy < 0:
        return True
    return (cx + 0.5) ** 2 + (cy + 0.5) ** 2 <= r * r + 0.5


def fill_px(theme, x, y, w, h, tone=0.0):
    """Panel fill colour at (x, y) for a w×h fill area; tone shifts brightness (−1 … +1)."""
    T = THEMES[theme]
    top, mid, bot = T["fill"]
    tones = [top, mix(top, mid, 0.5), mid, mix(mid, bot, 0.5), bot]
    v = max(0.0, min(0.999, y / max(1, h - 1)))
    f = v * 4
    i = int(f)
    if i < 4 and (f - i) > 0.5 and bayer4(x, y) < ((f - i) - 0.5) * 2:
        i += 1
    c = tones[i]
    tex = T["tex"]
    if tex == "planks":
        plank = y // 8
        if y % 8 == 7:
            c = bot
        elif y % 8 == 0:
            c = mix(top, "#ffffff", 0.08)
        elif abs(vnoise(x / 9.0 + plank * 7, (y % 8) * 0.55, 3) - 0.5) < 0.035:
            c = mix(c, bot, 0.6)                                  # grain streak
        if (x + plank * 23) % 41 == 0 and y % 8 not in (0, 7):
            c = bot                                               # plank joint
        if (x + plank * 23) % 82 == 3 and y % 8 == 3 and plank % 2 == 0:
            c = THEMES[theme]["border"][1]                        # occasional nail by a joint
    elif tex == "blocks":
        row = y // 8
        if y % 8 == 7 or (x + (row % 2) * 8) % 16 == 15:
            c = bot
        elif y % 8 == 0 or (x + (row % 2) * 8) % 16 == 0:
            c = top
        elif hash01(x, y, 4) < 0.06:
            c = bot
    elif tex == "paper":
        edge = min(x, y, w - 1 - x, h - 1 - y)
        if edge < 3 and bayer4(x, y) < (3 - edge) / 4:
            c = bot
        elif hash01(x, y, 7) < 0.04:
            c = mid
    if tone > 0:
        c = mix(c, "#ffffff", 0.18 * tone)
    elif tone < 0:
        c = mix(c, "#000000", 0.3 * -tone)
    return c


def frame(theme: str, w: int, h: int, *, bw=None, fill=True, tone=0.0, radius=None, ornaments=True, inset=False,
          highlight=False):
    """Bevelled rounded frame (w×h hex grid). inset=True swaps the lighting (a slot / trough)."""
    T = THEMES[theme]
    bw = T["bw"] if bw is None else bw
    r = (bw + 1) if radius is None else radius
    bd, bm, bl, bh = T["border"]
    if highlight:
        bd, bm, bl, bh = mix(bd, T["accent"][1], 0.5), mix(bm, T["accent"][1], 0.6), mix(bl, T["accent"][2], 0.6), "#ffffff"
    g = blank(w, h)
    for y in range(h):
        for x in range(w):
            if not rounded_inside(x, y, w, h, r):
                continue
            # depth into the frame from the nearest edge (with rounded corners)
            e = min(x, y, w - 1 - x, h - 1 - y)
            if e == 0 or not all(rounded_inside(x + dx, y + dy, w, h, r) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = OUTLINE
                continue
            tl = min(x, y) <= min(w - 1 - x, h - 1 - y)
            lit = tl != inset
            if e <= bw:
                if e == 1:
                    g[y][x] = bh if lit else bd
                elif e == bw:
                    g[y][x] = bd if lit else bm
                else:
                    g[y][x] = bl if lit else bm
            elif e == bw + 1:
                g[y][x] = OUTLINE if not inset else (mix(T["fill"][2], "#000000", 0.4) if lit else T["fill"][0])
            elif fill:
                g[y][x] = fill_px(theme, x - bw - 2, y - bw - 2, w - 2 * bw - 4, h - 2 * bw - 4, tone)
                if e == bw + 2 and lit and not inset:
                    g[y][x] = mix(g[y][x], "#000000", 0.35)      # inner shadow under the top/left border
    if ornaments:
        corner_ornaments(g, theme, w, h, bw)
    return g


def corner_ornaments(g, theme, w, h, bw):
    T = THEMES[theme]
    ad, am, al = T["accent"] if theme != "wood_gold" else (T["border"][0], T["border"][2], T["border"][3])
    if theme == "classic_blue":
        ad, am, al = T["accent"]
    for (cx, cy, sx, sy) in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        if theme in ("wood_gold", "classic_blue"):                  # L-shaped metal corner brackets
            L = bw + 4
            for i in range(L):
                for j in range(2):
                    for (x, y) in ((cx + sx * (i + 1), cy + sy * (j + 1)), (cx + sx * (j + 1), cy + sy * (i + 1))):
                        if 0 <= x < w and 0 <= y < h and g[y][x] is not None and g[y][x] != OUTLINE:
                            g[y][x] = al if j == 0 and (sx > 0 or sy > 0) else (am if j == 0 else ad)
            x, y = cx + sx * (bw // 2 + 1), cy + sy * (bw // 2 + 1)
            if 0 <= x < w and 0 <= y < h:
                g[y][x] = "#ffffff"
        elif theme == "stone_iron":                                 # rivets
            x, y = cx + sx * (bw // 2 + 1), cy + sy * (bw // 2 + 1)
            for dx, dy, c in ((0, 0, T["border"][3]), (1, 0, T["border"][1]), (0, 1, T["border"][1]), (1, 1, T["border"][0])):
                xx, yy = x + dx * sx, y + dy * sy
                if 0 <= xx < w and 0 <= yy < h:
                    g[yy][xx] = c if (sx > 0 and sy > 0) else T["border"][1 if (dx or dy) else 3]
        elif theme == "parchment":                                  # red wax dot
            x, y = cx + sx * (bw // 2 + 1), cy + sy * (bw // 2 + 1)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                xx, yy = x + dx * sx, y + dy * sy
                if 0 <= xx < w and 0 <= yy < h:
                    g[yy][xx] = am if (dx, dy) != (0, 0) else al


def overlay(dst, src, ox=0, oy=0):
    for y, row in enumerate(src):
        for x, c in enumerate(row):
            if c is not None and 0 <= y + oy < len(dst) and 0 <= x + ox < len(dst[0]):
                dst[y + oy][x + ox] = c
    return dst


def greyed(g):
    return [[grey(c) if c and c != OUTLINE else c for c in row] for row in g]


def emit(name: str, w: int, h: int, layers: list[tuple[str, list]], durations=None, tags=()):
    """layers: [(layer name, [frame grid, …])]; all layers have the same number of frames."""
    nf = max(len(fr) for _, fr in layers)
    cols = []
    for _, frames in layers:
        for g in frames:
            for row in g:
                for c in row:
                    if c and c not in cols:
                        cols.append(c)
    idx = {c: i for i, c in enumerate(cols)}
    d = DocBuilder(name, w, h)
    d.palette(cols)
    lids = [d.layer(n) for n, _ in layers]
    if nf > 1:
        d.add_frames(nf - 1, 100)
    for li, (_, frames) in zip(lids, layers):
        for fi in range(nf):
            g = frames[min(fi, len(frames) - 1)]
            used = sorted({c for row in g for c in row if c})
            for i in range(0, len(used), 60):
                chunk = set(used[i:i + 60])
                gg = Grid(w, h)
                gg.px = [[idx[c] if c in chunk else None for c in row] for row in g]
                d.paint(gg, li, fi)
    for fi, ms in enumerate(durations or []):
        d.duration(fi, ms)
    for tname, a, b in tags:
        d.tag(tname, a, b)
    return d.calls
