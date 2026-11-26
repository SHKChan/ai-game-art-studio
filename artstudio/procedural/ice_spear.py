"""Skill icon: an ice spear on a round frame (32x32 by default). Worked example in docs/pixel-forge-guide.md.

Demonstrates the builder pattern: palette ramps, one Grid per layer, shading from a light direction,
selective outline, optional element variants via params."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, ramp_pick

DESCRIPTION = "Round skill icon with a diagonal elemental spear (ice by default) and a framed background."
ASSET_TYPE = "icon"
GROUP = "Skill icons"
PARAMS = {"size": {"type": "int", "default": 32}, "element": {"type": "string", "default": "ice", "enum": ["ice", "lightning", "poison"]}}

ELEMENTS = {  # dark → light ramp for the spear + glow colour
    "ice": ["#0e2a52", "#1f5fa8", "#4fb0f0", "#a8e8ff", "#ffffff"],
    "lightning": ["#3a2a06", "#9a6a0a", "#f0c020", "#fff27a", "#ffffff"],
    "poison": ["#0e2a12", "#1f7a2a", "#4fd04a", "#b8ff8a", "#ffffff"],
}
FRAME = ["#151020", "#3a3552", "#6e6890", "#b4aed0"]   # outline, rim dark, rim mid, rim light
BG = ["#1a1830", "#262340"]                            # inner background, vignette


def build(size: int = 32, element: str = "ice", **_):
    s = size / 32.0
    spear = ELEMENTS[element]
    pal = FRAME + BG + spear
    OUT, RD, RM, RL, BG0, BG1 = range(6)
    SP = list(range(6, 6 + len(spear)))          # spear ramp indices
    d = DocBuilder(f"skill-icon-{element}-spear", size, size)
    d.palette(pal)
    l_frame, l_glow, l_spear = d.layer("frame"), d.layer("glow"), d.layer("spear")
    c = (size - 1) / 2

    # 1) frame: filled disc with a lit rim (top-left light) and a dark outline
    frame = Grid(size, size)
    r_out, r_in = 14.6 * s, 12.2 * s

    def frame_px(x, y):
        dx, dy = x - c, y - c
        dist = math.hypot(dx, dy)
        if dist > r_out:
            return None
        if dist > r_out - 1:
            return OUT
        if dist > r_in:
            light = -(dx + dy) / (dist * 1.414 + 1e-6)   # +1 at top-left
            return RL if light > 0.5 else (RM if light > -0.3 else RD)
        return BG1 if dist > r_in - 2 else BG0
    frame.field(frame_px)

    # 2) spear: shaft from bottom-left to top-right, diamond head, shaded across its width
    sp = Grid(size, size)
    x0, y0, x1, y1 = c - 8 * s, c + 8 * s, c + 1.5 * s, c - 1.5 * s
    ux, uy = (x1 - x0), (y1 - y0)
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L

    def spear_px(x, y):
        px, py = x - x0, y - y0
        t = px * ux + py * uy                 # along the shaft
        n = -px * uy + py * ux                # across (sign = side)
        if 0 <= t <= L:
            if abs(n) <= 1.0 * s:
                return ramp_pick(0.55 - n * 0.35, [SP[1], SP[2], SP[3]], x, y, 0)
        head_t = t - L                        # pointed head: widens over 2px, tapers to a tip over 7px
        if 0 <= head_t <= 9 * s:
            half = (1.2 + head_t) * s if head_t < 2 * s else 3.2 * s * (1 - (head_t - 2 * s) / (7 * s))
            if abs(n) <= half:
                return ramp_pick(0.5 - n / (half + 0.5) * 0.45, [SP[1], SP[2], SP[3], SP[4]], x, y, 0)
        return None
    sp.field(spear_px)
    edge = sp.copy()
    edge.outline(SP[0])                        # dark contour only where the spear meets background
    for y in range(size):
        for x in range(size):
            if edge.px[y][x] == SP[0] and sp.px[y][x] is None and frame.get(x, y) is not None:
                sp.set(x, y, SP[0])

    # 3) glow: soft sparkle dots around the head (pixels, not alpha — GIF safe)
    glow = Grid(size, size)
    hx, hy = x1 + 5 * s * ux, y1 + 5 * s * uy
    for ang, rr, col in [(200, 6, SP[3]), (250, 7, SP[2]), (20, 6, SP[3]), (110, 5, SP[2]), (300, 8, SP[4])]:
        gx, gy = hx + rr * s * math.cos(math.radians(ang)), hy + rr * s * math.sin(math.radians(ang))
        if frame.get(gx, gy) in (BG0, BG1):
            glow.set(gx, gy, col)

    d.paint(frame, l_frame, 0)
    d.paint(glow, l_glow, 0)
    d.paint(sp, l_spear, 0)
    return d.calls
