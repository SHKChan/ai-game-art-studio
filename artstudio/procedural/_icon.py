"""Shared renderer for item / equipment / UI icons (JRPG style), v2.

Icons are *designed* on a 32-unit grid and rasterised at `size` px (32, 48 or 64), so the same drawing gains detail at
larger sizes. Each pixel belongs to a named *part*; every part is lit per pixel like the original potion builder:

1. a height field from the distance to the part's edge (bevel width depends on the part's *style*),
2. a normal from that height field, lit from the top-left (light (-0.6, -0.75, 0.6)),
3. the light value picks a tone from a 5-tone hue-shifted ramp with ordered dithering at band edges,
4. metal / gem / glass styles add specular highlights; wood and cloth add a little grain.

A 1-px outline goes round the silhouette (selective: the lit top-left side takes the part's own darkest tone).
`dot()` adds hand-placed highlights on a separate 'shine' layer. Optional rarity slot frame.
"""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, bayer4, hash01, vnoise

OUTLINE = "#140e1a"
LIGHT = (-0.55, -0.7, 0.62)

# dark, mid, light, highlight (expanded to 5 hue-shifted tones by ramp5)
RAMPS = {
    "iron": ["#3a3e4c", "#6c7282", "#a8aebc", "#eceff4"],
    "bronze": ["#4a2a14", "#8c5a2a", "#c68c4a", "#f2cc90"],
    "mithril": ["#22406c", "#4f86c0", "#92ccf0", "#ecfcff"],
    "gold": ["#5c3a08", "#b07c16", "#eec23c", "#fff4b4"],
    "dark": ["#1c1028", "#44285c", "#7648a0", "#c8a2f0"],
    "silver": ["#40465a", "#7a8298", "#b8c0d2", "#ffffff"],
    "copper": ["#4a1c10", "#8e3e22", "#c8683a", "#f4aa78"],
    "steel": ["#2e3442", "#5e6678", "#9aa2b4", "#e8ecf4"],
    "wood": ["#3a2214", "#6a4024", "#9a6236", "#c88e56"],
    "darkwood": ["#24140c", "#46281a", "#6a4028", "#94603a"],
    "leather": ["#341a10", "#64341e", "#925632", "#c4865a"],
    "red": ["#4a0c14", "#9a1c26", "#d83a3a", "#ff8a78"],
    "blue": ["#0e1c4a", "#1e4a9a", "#3a84d8", "#8ad0ff"],
    "green": ["#0e3416", "#1e6e2a", "#3aa83a", "#9ae070"],
    "purple": ["#26103e", "#52248a", "#8a4ac8", "#d4a2ff"],
    "white": ["#6a6a80", "#b0b2c4", "#e6e8f2", "#ffffff"],
    "black": ["#0c0a12", "#24202e", "#3e3850", "#6a6280"],
    "rice": ["#8a8478", "#d0ccc0", "#f2f0e8", "#ffffff"],
    "parchment": ["#6a4a24", "#b48c54", "#e2c48a", "#fff0c8"],
    "glass": ["#3a5a6e", "#7aa4b8", "#c4e4f0", "#ffffff"],
    "ruby": ["#4a0618", "#a8102e", "#ee3a4e", "#ffb4b8"],
    "sapphire": ["#0a1650", "#1a46b8", "#3a8cf4", "#b4e0ff"],
    "emerald": ["#063a20", "#108a44", "#2ed070", "#b4ffcc"],
    "amethyst": ["#2a0a4a", "#6a20b0", "#a85af0", "#e8c8ff"],
    "topaz": ["#5a3006", "#c27a10", "#f8be2a", "#fff0a8"],
    "diamond": ["#4a5a7a", "#a4b8d8", "#e0ecff", "#ffffff"],
    "fire": ["#7a160e", "#e0481a", "#ffa62a", "#fff2a0"],
    "flesh": ["#5a2e1e", "#b06a4a", "#e0a07a", "#ffd8b8"],
    "herb": ["#103a14", "#24742a", "#4eb040", "#a8e878"],
    "stone": ["#2a2630", "#4e4a58", "#7a7488", "#aaa4b6"],
    "bone": ["#5a4a3a", "#a8987e", "#dcd0b4", "#fff8e4"],
    "teal": ["#0a3036", "#14706a", "#2ab4a0", "#9af0dc"],
    "pink": ["#5a1240", "#b02a7a", "#ee6ab4", "#ffc4e4"],
    "orange": ["#5a2008", "#b0500e", "#f08a2a", "#ffd08a"],
}
STYLE_OF = {  # default lighting style per ramp
    **{k: "metal" for k in ("iron", "bronze", "mithril", "gold", "dark", "silver", "copper", "steel")},
    **{k: "wood" for k in ("wood", "darkwood")},
    **{k: "gem" for k in ("ruby", "sapphire", "emerald", "amethyst", "topaz", "diamond")},
    "glass": "glass", "fire": "glow",
}
STYLES = {  # bevel width (design units; 0 = dome over the whole part), contrast, specular threshold, grain
    "metal": (1.6, 1.35, 0.95, 0.0),
    "blade": (0.0, 1.45, 0.95, 0.0),
    "soft": (2.2, 1.0, 2.0, 0.07),
    "wood": (1.4, 1.05, 2.0, 0.12),
    "gem": (0.0, 1.5, 0.985, 0.0),
    "glass": (0.0, 1.1, 0.975, 0.0),
    "round": (0.0, 1.15, 2.0, 0.03),
    "glow": (0.0, 0.8, 2.0, 0.0),
    "flat": (0.0, 0.0, 2.0, 0.0),
}
RARITY = {  # border dark, border mid, border light, bg dark, bg light
    "common": ["#3a3a46", "#6e6e7c", "#a8a8b8", "#1c1c24", "#2e2e3a"],
    "uncommon": ["#14401e", "#2a7a3a", "#7ad07a", "#10241a", "#1c3a26"],
    "rare": ["#142a66", "#2a5aba", "#7ab4ff", "#101a36", "#1c2c58"],
    "epic": ["#3a1260", "#7a2ab8", "#d08aff", "#1e1030", "#34194f"],
    "legendary": ["#5a3a08", "#b8801a", "#ffe07a", "#2e1d08", "#4e3410"],
}
FRAMES = ["none"] + list(RARITY)
SIZES = [32, 48, 64]


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _mix(a, b, t):
    a, b = _hex(a), _hex(b)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ramp5(r4):
    """4 key tones → 5 tones: shadows lean cool/purple, highlights lean warm."""
    d, m, l, h = r4
    return [_mix(d, "#120a24", 0.25), _mix(d, m, 0.5), m, l, _mix(h, "#fffbe8", 0.15)]


class Icon:
    def __init__(self, size: int = 32):
        if size not in SIZES and not (8 <= size <= 128):
            raise ValueError("size must be 32, 48 or 64")
        self.n = int(size)
        self.k = self.n / 32.0
        self.parts = [[None] * self.n for _ in range(self.n)]
        self.spec: dict[str, tuple] = {}            # part → (ramp5, style)
        self.fixed: dict[str, str] = {}
        self.extra: list[tuple[int, int, str]] = []

    # ---- parts
    def part(self, name, ramp, flat=False, style=None):
        r4 = RAMPS[ramp] if isinstance(ramp, str) else list(ramp)
        st = "flat" if flat else (style or (STYLE_OF.get(ramp, "soft") if isinstance(ramp, str) else "soft"))
        self.spec[name] = (ramp5(r4) if len(r4) == 4 else list(r4), st)
        return name

    def color(self, name, hex_):
        self.fixed[name] = hex_
        return name

    # ---- design-space primitives (32-unit grid)
    def _px(self, v):
        return v * self.k

    def set(self, x, y, p):
        """Mark one design cell (covers k×k pixels)."""
        k = self.k
        for yy in range(int(y * k), max(int(y * k) + 1, int((y + 1) * k))):
            for xx in range(int(x * k), max(int(x * k) + 1, int((x + 1) * k))):
                if 0 <= xx < self.n and 0 <= yy < self.n:
                    self.parts[yy][xx] = p

    def get(self, x, y):
        xx, yy = int((x + .5) * self.k), int((y + .5) * self.k)
        return self.parts[yy][xx] if 0 <= xx < self.n and 0 <= yy < self.n else None

    def _grid(self):
        return Grid(self.n, self.n)

    def poly(self, pts, p):
        g = self._grid()
        g.polygon([(x * self.k, y * self.k) for x, y in pts], 1)
        self._merge(g, p)

    def ellipse(self, cx, cy, rx, ry, p):
        g = self._grid()
        k = self.k
        g.ellipse(cx * k + (k - 1) / 2, cy * k + (k - 1) / 2, rx * k, ry * k, 1)
        self._merge(g, p)

    def rect(self, x0, y0, x1, y1, p):
        k = self.k
        for yy in range(int(round(y0 * k)), int(round((y1 + 1) * k))):
            for xx in range(int(round(x0 * k)), int(round((x1 + 1) * k))):
                if 0 <= xx < self.n and 0 <= yy < self.n:
                    self.parts[yy][xx] = p

    def line(self, x0, y0, x1, y1, p, w=None):
        """Line of width ~1 design unit (≥ 1 px)."""
        w = 1.0 if w is None else w
        if self.k <= 1.01 and w <= 1.0:
            g = self._grid()
            g.line(x0, y0, x1, y1, 1)
            self._merge(g, p)
        else:
            self.bar(x0 + .5, y0 + .5, x1 + .5, y1 + .5, w, w, p)

    def bar(self, x0, y0, x1, y1, w0, w1=None, p=None):
        w1 = w0 if w1 is None else w1
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        self.poly([(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
                   (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)], p)

    def field(self, fn):
        """fn(design_x, design_y) per pixel (pixel centres mapped to design space)."""
        k = self.k
        for y in range(self.n):
            for x in range(self.n):
                v = fn((x + .5) / k - .5, (y + .5) / k - .5)
                if v is not None:
                    self.parts[y][x] = v

    def _merge(self, g: Grid, p):
        for y in range(self.n):
            for x in range(self.n):
                if g.px[y][x] is not None:
                    self.parts[y][x] = p

    def dot(self, x, y, hex_, big=None):
        """Hand-placed highlight on the shine layer (1 design unit; at 64 px a 2×2 block)."""
        k = self.k
        s = max(1, int(round(k * 0.75))) if big is None else big
        x0, y0 = int(round((x + .5) * k - s / 2)), int(round((y + .5) * k - s / 2))
        for yy in range(y0, y0 + s):
            for xx in range(x0, x0 + s):
                self.extra.append((xx, yy, hex_))

    # ---- shading
    def _dist(self, name):
        """Chamfer distance (px) from each pixel of part `name` to the nearest pixel outside it."""
        n, INF = self.n, 1e9
        P = self.parts
        d = [[(INF if P[y][x] == name else 0.0) for x in range(n)] for y in range(n)]
        a, b = 1.0, 1.4142
        for y in range(n):
            for x in range(n):
                if d[y][x]:
                    v = d[y][x]
                    for dx, dy, w in ((-1, 0, a), (0, -1, a), (-1, -1, b), (1, -1, b)):
                        xx, yy = x + dx, y + dy
                        v = min(v, (d[yy][xx] if 0 <= xx < n and 0 <= yy < n else 0.0) + w)
                    d[y][x] = v
        for y in range(n - 1, -1, -1):
            for x in range(n - 1, -1, -1):
                if d[y][x]:
                    v = d[y][x]
                    for dx, dy, w in ((1, 0, a), (0, 1, a), (1, 1, b), (-1, 1, b)):
                        xx, yy = x + dx, y + dy
                        v = min(v, (d[yy][xx] if 0 <= xx < n and 0 <= yy < n else 0.0) + w)
                    d[y][x] = v
        return d

    def shade(self) -> list[list[str | None]]:
        n, P = self.n, self.parts
        out = [[None] * n for _ in range(n)]
        lx, ly, lz = LIGHT
        ll = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ll, ly / ll, lz / ll
        hx, hy, hz = lx, ly, lz + 1
        hl = math.sqrt(hx * hx + hy * hy + hz * hz)
        hx, hy, hz = hx / hl, hy / hl, hz / hl
        names = {p for row in P for p in row if p is not None}
        for name in names:
            if name in self.fixed:
                for y in range(n):
                    for x in range(n):
                        if P[y][x] == name:
                            out[y][x] = self.fixed[name]
                continue
            ramp, style = self.spec[name]
            bevel, contrast, spec_t, grain = STYLES[style]
            if style == "flat":
                for y in range(n):
                    for x in range(n):
                        if P[y][x] == name:
                            out[y][x] = ramp[2]
                continue
            dist = self._dist(name)
            dmax = max(max(r) for r in dist) or 1.0
            pts = [(x, y) for y in range(n) for x in range(n) if P[y][x] == name]
            cxp = sum(p[0] for p in pts) / len(pts)
            cyp = sum(p[1] for p in pts) / len(pts)
            B = bevel * self.k if bevel else dmax
            B = max(B, 1.0)

            def H(x, y):
                if not (0 <= x < n and 0 <= y < n) or P[y][x] != name:
                    return 0.0
                t = min(dist[y][x], B) / B
                return math.sqrt(max(0.0, 1 - (1 - t) ** 2))
            strength = 1.1 * B if style in ("metal", "soft", "wood") else 1.5 * B
            for y in range(n):
                for x in range(n):
                    if P[y][x] != name:
                        continue
                    gx = (H(x + 1, y) - H(x - 1, y)) * 0.5
                    gy = (H(x, y + 1) - H(x, y - 1)) * 0.5
                    nx, ny, nz = -gx * strength, -gy * strength, 1.0
                    nl = math.sqrt(nx * nx + ny * ny + nz * nz)
                    nx, ny, nz = nx / nl, ny / nl, nz / nl
                    diff = nx * lx + ny * ly + nz * lz
                    lum = 0.56 + (diff - lz) * contrast * 1.25 - 0.16 * ((x - cxp) + (y - cyp)) / (2 * max(dmax, 4.0))
                    if style in ("gem", "glass"):            # light passes through: glow on the far (lower-right) side
                        rel = ((x - cxp) + (y - cyp)) / (1.4 * dmax)
                        inner = min(1.0, dist[y][x] / max(1.0, dmax * 0.3))
                        if style == "gem":
                            lum = 0.5 + (diff - lz) * 0.6 + 1.1 * max(0.0, rel) * inner - 0.25 * (1 - inner)
                            if math.hypot(x - (cxp - 0.42 * dmax), y - (cyp - 0.42 * dmax)) < max(0.8, 0.22 * dmax):
                                out[y][x] = ramp[4]
                                continue
                        else:
                            lum += 0.25 * max(0.0, rel) * inner
                    if grain:
                        if style == "wood":
                            lum += grain * (vnoise(x * 0.35 / self.k, y * 2.2 / self.k, 5) - 0.5) * 2
                        else:
                            lum += grain * (hash01(x, y, 9) - 0.5) * 2
                    spec = nx * hx + ny * hy + nz * hz
                    if spec > spec_t and H(x, y) > 0.3:
                        out[y][x] = ramp[4]
                        continue
                    lum = max(0.0, min(0.999, lum))
                    i = lum * 4.0
                    j = int(i)
                    frac = i - j
                    if j < 4 and frac > 0.7 and bayer4(x, y) < (frac - 0.7) / 0.3:
                        j += 1
                    out[y][x] = ramp[min(3, j)] if style not in ("metal", "gem", "glass", "blade") else ramp[min(4, j)]
        for y in range(n):                                    # selective outline
            for x in range(n):
                if P[y][x] is not None:
                    continue
                nb = [(P[y][x + 1] if x + 1 < n else None), (P[y + 1][x] if y + 1 < n else None),
                      (P[y][x - 1] if x > 0 else None), (P[y - 1][x] if y > 0 else None)]
                if any(q is not None for q in nb):
                    src = nb[0] or nb[1]
                    if src is not None and src in self.spec and nb[2] is None and nb[3] is None and self.spec[src][1] != "flat":
                        out[y][x] = self.spec[src][0][0]
                    else:
                        out[y][x] = OUTLINE
        return out


def frame_grid(rarity: str, n: int = 32):
    """Rounded, bevelled slot: dark outline, lit/shadowed border, inset background with a soft top-left glow."""
    if rarity == "none":
        return None
    BD, BM, BL, D, L = RARITY[rarity]
    k = n / 32.0
    bw = max(2, int(round(2 * k)))
    g = [[None] * n for _ in range(n)]
    corner = max(2, int(round(2 * k)))
    for y in range(n):
        for x in range(n):
            ex, ey = min(x, n - 1 - x), min(y, n - 1 - y)
            if ex + ey < corner:
                continue
            e = min(ex, ey, ex + ey - corner + 1)
            if e == 0:
                g[y][x] = OUTLINE
            elif e <= bw:
                lit = (x + y) < n - 1
                g[y][x] = BL if (lit and e == 1) else (BM if lit else BD)
            elif e == bw + 1:
                g[y][x] = OUTLINE if (x + y) < n - 1 else BD
            else:
                q = math.hypot(x - n * 0.38, y - n * 0.34) / n
                g[y][x] = L if q < 0.42 + 0.06 * bayer4(x, y) else D
    for (x, y) in ((corner + bw, corner + bw - 1), (corner + bw - 1, corner + bw)):
        if 0 <= x < n and 0 <= y < n:
            g[y][x] = BL
    return g


def _paint(d: DocBuilder, layer: int, grid_hex, idx, n):
    """Paint a hex grid, splitting into several calls if it uses more colours than one legend holds."""
    cols = sorted({c for row in grid_hex for c in row if c})
    for i in range(0, len(cols), 60):
        chunk = set(cols[i:i + 60])
        gg = Grid(n, n)
        gg.px = [[idx[c] if c in chunk else None for c in row] for row in grid_hex]
        d.paint(gg, layer, 0)


def emit(name: str, icon: Icon, rarity: str = "none", extra_layers=()):
    """Shaded icon → engine calls with layers 'frame' (optional), 'item' and 'shine'."""
    art = icon.shade()
    n = icon.n
    shine = [[None] * n for _ in range(n)]
    for x, y, c in icon.extra:
        if 0 <= x < n and 0 <= y < n:
            shine[y][x] = c
    fr = frame_grid(rarity, n)
    layers = ((("frame", fr),) if fr else ()) + tuple(extra_layers) + (("item", art), ("shine", shine))
    cols = []
    for _, g in layers:
        for row in g:
            for c in row:
                if c is not None and c not in cols:
                    cols.append(c)
    idx = {c: i for i, c in enumerate(cols)}
    d = DocBuilder(name, n, n)
    d.palette(cols)
    for lname, g in layers:
        _paint(d, d.layer(lname), g, idx, n)
    return d.calls


def sparkle(icon: Icon, x, y, c="#ffffff", arm=1):
    icon.dot(x, y, c)
    for k in range(1, arm + 1):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            icon.dot(x + dx, y + dy, c)
