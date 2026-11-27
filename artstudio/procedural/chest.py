"""64x64 treasure chest, rendered from a small 3D model (box body + arched lid hinged at the back)
projected orthographically with a top-down tilt. Shared by `chest` (static) and `chest_open` (animation)."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "Wooden treasure chest with iron trim and a gold lock (closed)."
ASSET_TYPE = "item"
PARAMS = {"size": {"type": "int", "default": 64}}

PALETTE = ["#1b1020", "#3d1f12", "#6b3a1f", "#9a5a2e", "#c78445", "#e2a964",
           "#353a4e", "#6c7690", "#b0bcd4", "#8a5a12", "#d49a22", "#f7d14a",
           "#fff4b0", "#200c16", "#ffffff", "#fff2c2"]
O, WD0, WD1, WD2, WD3, WD4, M0, M1, M2, G0, G1, G2, G3, IN, WH, GLOW = range(16)
WOOD = [WD0, WD1, WD2, WD3, WD4]
METAL = [M0, M0, M1, M2, M2]
GOLD = [G0, G0, G1, G2, G3]

TILT = math.radians(34)
SA, CA = math.sin(TILT), math.cos(TILT)
LIGHT = (0.93, 0.37)  # (y, z) components, normalised below
_ln = math.hypot(*LIGHT)
LIGHT = (LIGHT[0] / _ln, LIGHT[1] / _ln)


KX = 0.45  # oblique (cabinet-style) receding offset: the back shifts right, showing the right side as a real face


def _proj(x, y, z, s, base_y):
    return ((x - 2.5 - z * KX) * s, base_y + (-y * CA + z * SA) * s)


def _depth(y, z):
    return z * CA + y * SA


def _shade(ny, nz, ramp, bias=0.0):
    b = max(0.0, ny * LIGHT[0] + nz * LIGHT[1]) * 0.85 + 0.15 + bias
    return ramp[max(0, min(len(ramp) - 1, int(b * len(ramp))))]


X0, X1 = 11.0, 53.0         # chest width
Z0, Z1 = -10.0, 10.0        # depth
BODY_H = 17.0
LID_T = 3.0                 # lid wall height before the arch
ARCH = 7.5
TRIM = [(11.0, 14.0), (30.0, 34.0), (50.0, 53.0)]   # metal bands (x ranges)


def _segments():
    xs = sorted({X0, X1} | {v for a, b in TRIM for v in (a, b)})
    segs = []
    for a, b in zip(xs, xs[1:]):
        metal = any(ta <= a and b <= tb for ta, tb in TRIM)
        segs.append((a, b, metal))
    return segs


def lid_profile(theta: float, n: int = 10):
    """Closed lid profile in (z, y) rotated about the hinge (Z0, BODY_H) by theta (radians, opening backwards)."""
    pts = [(Z0, BODY_H), (Z0, BODY_H + LID_T)]
    for k in range(1, n):
        t = k / n
        pts.append((Z0 + (Z1 - Z0) * t, BODY_H + LID_T + ARCH * math.sin(math.pi * t)))
    pts += [(Z1, BODY_H + LID_T), (Z1, BODY_H)]
    hz, hy = Z0, BODY_H
    out = []
    for z, y in pts:
        dz, dy = z - hz, y - hy
        # rotating "up and back": front edge moves up then towards -z
        nz = hz + dz * math.cos(theta) - dy * math.sin(theta)
        ny = hy + dz * math.sin(theta) + dy * math.cos(theta)
        out.append((nz, ny))
    return out


def render(theta: float = 0.0, size: int = 64, glow: float = 0.0, sparkle: int = -1, rattle: int = 0, coins: bool = True):
    s = size / 64.0
    base_y = 52.0 + rattle * 0.0
    body, interior, lid, fx = Grid(size, size), Grid(size, size), Grid(size, size), Grid(size, size)
    segs = _segments()

    def quad(g, x0, x1, p, q, color):
        a = _proj(x0, p[1], p[0], s, base_y); b = _proj(x1, p[1], p[0], s, base_y)
        c = _proj(x1, q[1], q[0], s, base_y); d = _proj(x0, q[1], q[0], s, base_y)
        g.polygon([a, b, c, d], color)

    # ---- body right side (x = X1), in shadow, with an iron edge strip
    def side(g, pts, color):
        g.polygon([_proj(X1, y, z, s, base_y) for z, y in pts], color)
    side(body, [(Z1, 0), (Z0, 0), (Z0, BODY_H), (Z1, BODY_H)], WD1)
    side(body, [(Z1, 0), (Z1 - 3, 0), (Z1 - 3, BODY_H), (Z1, BODY_H)], M0)
    side(body, [(Z0 + 2.5, 0), (Z0, 0), (Z0, BODY_H), (Z0 + 2.5, BODY_H)], M0)
    # ---- body front face (z = Z1)
    for a, b, metal in segs:
        if metal:
            quad(body, a, b, (Z1, 0.0), (Z1, BODY_H), M1)
            continue
        quad(body, a, b, (Z1, 0.0), (Z1, BODY_H), WD2)
        quad(body, a, b, (Z1, BODY_H * 0.55), (Z1, BODY_H), WD3)
    # planks + bottom trim on front face
    for py in (5.5, 11.5):
        y0 = _proj(0, py, Z1, s, base_y)[1]
        for x in range(int(X0 * s), int(X1 * s)):
            if not any(ta * s <= x < tb * s for ta, tb in TRIM):
                body.set(x, y0, WD1)
    yb = _proj(0, 1.6, Z1, s, base_y)[1]
    for x in range(int(X0 * s), int(X1 * s)):
        body.set(x, yb, M1)
        body.set(x, yb + 1, M0)
    # rivets on bands
    for ta, tb in TRIM:
        cxr = (ta + tb) / 2 * s
        for py in (3.0, 16.0):
            if ta == TRIM[1][0]:
                continue
            body.set(cxr, _proj(0, py, Z1, s, base_y)[1], M2)
    # metal band highlight edges
    for ta, tb in TRIM:
        for py in range(1, int(BODY_H)):
            body.set(ta * s, _proj(0, py, Z1, s, base_y)[1], M2)
    # ---- body top opening (visible only when lid is open)
    open_amt = min(1.0, theta / math.radians(40))
    if theta > 0.02:
        quad(interior, X0 + 1.2, X1 - 1.2, (Z0 + 1.2, BODY_H), (Z1 - 0.8, BODY_H), IN)
        if coins and open_amt > 0.2:
            # gold heap: dome inside the opening
            gx0, gx1 = (X0 + 3) * s, (X1 - 3) * s
            ytop = _proj(0, BODY_H + 2.5, 2, s, base_y)[1]
            yfront = _proj(0, BODY_H, Z1 - 1, s, base_y)[1]
            for x in range(int(gx0), int(gx1)):
                t = (x - gx0) / (gx1 - gx0)
                h = math.sin(math.pi * t) ** 0.6
                top = yfront - (yfront - ytop) * h - 1
                for y in range(int(top), int(yfront)):
                    v = hash01(x, y, 7)
                    depth_t = (y - top) / max(1, yfront - top)
                    col = G2 if depth_t < 0.25 else (G1 if v > 0.25 else G0)
                    if v > 0.93 and depth_t < 0.7:
                        col = G3
                    interior.set(x, y, col)
            for (gx, gy) in [(20, -1), (27, -2), (40, -1), (45, 0)]:
                interior.set(gx * s, ytop + 3 + gy, WH)
    # ---- lid faces, painter's algorithm
    prof = lid_profile(theta)
    cz = sum(p[0] for p in prof) / len(prof)
    cy = sum(p[1] for p in prof) / len(prof)
    faces = []
    for i in range(len(prof) - 1):
        p, q = prof[i], prof[i + 1]
        ez, ey = q[0] - p[0], q[1] - p[1]
        nz, ny = ey, -ez
        mz, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        if nz * (mz - cz) + ny * (my - cy) < 0:
            nz, ny = -nz, -ny
        ln = math.hypot(nz, ny) or 1
        nz, ny = nz / ln, ny / ln
        faces.append((_depth(my, mz), p, q, ny, nz, i))
    # closing edge (underside) from last point back to first
    p, q = prof[-1], prof[0]
    ez, ey = q[0] - p[0], q[1] - p[1]
    nz, ny = ey, -ez
    mz, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    if nz * (mz - cz) + ny * (my - cy) < 0:
        nz, ny = -nz, -ny
    ln = math.hypot(nz, ny) or 1
    faces.append((_depth(my, mz), p, q, ny / ln, nz / ln, -1))
    view = (SA, CA)
    for depth, p, q, ny, nz, idx in sorted(faces, key=lambda f: f[0]):
        if ny * view[0] + nz * view[1] <= 0.02:
            continue
        for a, b, metal in segs:
            if idx == -1:
                col = WD1 if not metal else M0  # inner lid boards, in shadow
            else:
                col = _shade(ny, nz, METAL if metal else WOOD, 0.12)
            quad(lid, a, b, p, q, col)
    # lid right cap (arched profile) with an iron rim
    cap = [_proj(X1, y, z, s, base_y) for z, y in prof]
    lid.polygon(cap, WD1 if theta < 1.2 else WD2)
    for i in range(len(cap)):
        (ax, ay), (bx, by) = cap[i], cap[(i + 1) % len(cap)]
        if i < len(cap) - 1:
            lid.line(ax, ay, bx, by, M1)
    # seam between lid and body + lid board lines (follow the lid)
    seam_p = prof[-1]
    if theta < 0.25:
        y = _proj(0, seam_p[1], seam_p[0], s, base_y)[1]
        for x in range(int(X0 * s), int(X1 * s)):
            lid.set(x, y, O)
            lid.set(x, y - 1, WD1 if not any(ta * s <= x < tb * s for ta, tb in TRIM) else M0)
    else:
        for k in (3, 6):
            pa = prof[k]
            y = _proj(0, pa[1], pa[0], s, base_y)[1]
            for x in range(int(X0 * s), int(X1 * s)):
                if lid.get(x, y) in (WD2, WD3, WD4, WD1) and not any(ta * s <= x < tb * s for ta, tb in TRIM):
                    lid.set(x, y, WD0 if lid.get(x, y) == WD1 else WD1)
    # lid rim line + lock plate
    front_bottom = prof[-1]
    front_top = prof[-2]
    if theta < 0.3:
        # hasp hanging from the lid onto the body lock
        lx = 32.0 * s
        ly0 = _proj(0, front_top[1], front_top[0], s, base_y)[1]
        ly1 = _proj(0, BODY_H - 5.5, Z1, s, base_y)[1]
        plate = [(lx - 4 * s, ly0 + 1), (lx + 4 * s, ly0 + 1), (lx + 4 * s, ly1), (lx, ly1 + 3 * s), (lx - 4 * s, ly1)]
        lid.polygon(plate, G1)
        lid.polygon([(lx - 4 * s, ly0 + 1), (lx - 2.5 * s, ly0 + 1), (lx - 2.5 * s, ly1), (lx - 4 * s, ly1)], G2)
        lid.polygon([(lx + 2.5 * s, ly0 + 1), (lx + 4 * s, ly0 + 1), (lx + 4 * s, ly1), (lx + 2.5 * s, ly1)], G0)
        lid.rect(lx - 1, ly1 - 4 * s, lx, ly1 - 2 * s, O)  # keyhole
        lid.set(lx - 1, ly1 - 5 * s, O); lid.set(lx, ly1 - 5 * s, O)
    else:
        # lock body remains on the chest; hasp travels with the lid (drawn on its front strip)
        lx = 32.0 * s
        ly = _proj(0, BODY_H - 2, Z1, s, base_y)[1]
        body.polygon([(lx - 3.5 * s, ly), (lx + 3.5 * s, ly), (lx + 3.5 * s, ly + 5 * s), (lx - 3.5 * s, ly + 5 * s)], G1)
        body.rect(lx - 3.5 * s, ly, lx - 2.5 * s, ly + 5 * s, G2)
        body.rect(lx - 1, ly + 2 * s, lx, ly + 3.5 * s, O)
    # ---- fx: light spilling out, sparkles
    if glow > 0 and theta > 0.05:
        top_y = _proj(0, BODY_H, 0, s, base_y)[1]
        height = int(22 * s * glow)
        from .raster import bayer4
        beams = [(17, 3, 0.75), (24, 4, 1.0), (32, 5, 0.9), (40, 4, 1.0), (47, 3, 0.7)]
        for bx, bw, bh in beams:
            for x in range(int((bx - bw / 2) * s), int((bx + bw / 2) * s) + 1):
                edge = abs(x - bx * s) / (bw / 2 * s + 0.5)
                h = int(height * bh * (1 - 0.35 * edge))
                for k in range(h):
                    y = top_y - 1 - k
                    fade = 1 - k / max(1, h)
                    if bayer4(x, y) < fade * 1.25 - edge * 0.3:
                        fx.set(x, y, GLOW if fade > 0.5 and edge < 0.6 else G2)
    if sparkle >= 0:
        for j, (sx, sy) in enumerate([(18, 18), (44, 14), (30, 8), (50, 26), (13, 28)]):
            phase = (sparkle + j * 2) % 6
            r = [0, 1, 2, 3, 2, 1][phase]
            if r == 0:
                continue
            x, y = sx * s, sy * s
            fx.set(x, y, WH)
            for k in range(1, r + 1):
                c = WH if k < r else GLOW
                fx.set(x + k, y, c); fx.set(x - k, y, c); fx.set(x, y + k, c); fx.set(x, y - k, c)
    return {"body": body, "interior": interior, "lid": lid, "fx": fx}


def outline_for(grids, size):
    sil = Grid(size, size)
    for k in ("body", "interior", "lid"):
        sil.merge(grids[k])
    ol = sil.copy()
    ol.outline(O)
    out = Grid(size, size)
    out.field(lambda x, y: O if ol.get(x, y) == O and sil.get(x, y) is None else None)
    return out


def paint_frames(d: DocBuilder, frames_spec, size):
    layers = {}
    for name in ("outline", "body", "interior", "lid", "fx"):
        layers[name] = d.layer(name)
    n = len(frames_spec)
    if n > 1:
        d.add_frames(n - 1, 100)
    for fi, spec in enumerate(frames_spec):
        g = render(size=size, **{k: v for k, v in spec.items() if k != "ms"})
        g["outline"] = outline_for(g, size)
        for name, gi in g.items():
            d.paint(gi, layers[name], fi)
        d.duration(fi, spec.get("ms", 100))


def build(size: int = 64, **_):
    d = DocBuilder("treasure-chest", size, size)
    d.palette(PALETTE)
    paint_frames(d, [{"theta": 0.0, "ms": 100}], size)
    return d.calls
