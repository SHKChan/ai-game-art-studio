"""8-frame sword-slash effect: anticipation glint, crescent sweep with tapered trail, bright impact,
then the arc thins and breaks into fading shards. Faces right (mirror in engine for left)."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, hash01

DESCRIPTION = "8-frame crescent sword-slash effect with anticipation, sweep, impact flash and dissipation."
ASSET_TYPE = "effect"
PARAMS = {"size": {"type": "int", "default": 64}, "color": {"type": "string", "default": "azure", "enum": ["azure", "gold", "crimson"]},
          "thickness": {"type": "float", "default": 1.0, "min": 0.5, "max": 1.6, "step": 0.1}}

PALETTES = {
    "azure": ["#0c1636", "#1d3f8f", "#3279e0", "#78c4ff", "#c6f0ff", "#ffffff"],
    "gold": ["#3a1c06", "#8a4a0c", "#d98a12", "#ffc63a", "#fff09a", "#ffffff"],
    "crimson": ["#2e0610", "#7a0f22", "#d42a3a", "#ff7a6a", "#ffd0c4", "#ffffff"],
}
# (head_deg, tail_deg, max_thickness, energy) — energy fades the colours during dissipation
FRAMES = [
    (-128, -128, 0, 1.0),
    (-95, -135, 4.5, 1.0),
    (-35, -135, 9.0, 1.0),
    (25, -125, 12.5, 1.0),
    (58, -95, 13.5, 1.0),
    (64, -40, 10.0, 0.8),
    (67, 10, 5.5, 0.55),
    (69, 48, 2.5, 0.3),
]
DURATIONS = [90, 40, 40, 40, 60, 60, 70, 80]


def build(size: int = 64, color: str = "azure", thickness: float = 1.0, **_):
    thickness = max(0.5, min(1.6, float(thickness)))
    s = size / 64.0
    pal = PALETTES[color]
    d = DocBuilder(f"sword-slash-{color}", size, size)
    d.palette(pal)
    l_trail = d.layer("trail")
    l_spark = d.layer("sparks")
    d.add_frames(len(FRAMES) - 1, 50)
    cx, cy, R = 28 * s, 32 * s, 25 * s
    for fi, (head, tail, thick, energy) in enumerate(FRAMES):
        trail, spark = Grid(size, size), Grid(size, size)
        span = head - tail
        if thick > 0 and span > 0:
            for y in range(size):
                for x in range(size):
                    dx, dy = x + .5 - cx, y + .5 - cy
                    r = math.hypot(dx, dy)
                    a = math.degrees(math.atan2(dy, dx))
                    if a < tail - 5 or a > head + 1:
                        continue
                    u = (a - tail) / span  # 0 at tail, 1 at head
                    if u < 0:
                        continue
                    w = thick * thickness * s * (u ** 0.45) * (1.0 if u < 0.92 else max(0.2, (1 - u) / 0.08))
                    inner = R - w
                    if not (inner <= r <= R + 0.5):
                        continue
                    depth = (R - r) / max(0.5, w)       # 0 at outer edge, 1 at inner edge
                    if energy < 0.9 and hash01(x, y, fi) > energy + 0.25 * (1 - u):
                        continue  # break into shards while dissipating
                    lvl = (1 - depth) * 0.6 + u * 0.55
                    lvl *= 0.55 + 0.45 * energy
                    idx = 1 + min(4, int(lvl * 4.2))
                    trail.set(x, y, idx)
            # inner dark edge line for contrast on bright backgrounds
            ol = trail.copy()
            ol.outline(0)
            for y in range(size):
                for x in range(size):
                    if ol.px[y][x] == 0 and trail.px[y][x] is None:
                        dx, dy = x + .5 - cx, y + .5 - cy
                        if math.hypot(dx, dy) < R - 0.5 and energy > 0.5:
                            trail.set(x, y, 0)
        hx, hy = cx + R * math.cos(math.radians(head)), cy + R * math.sin(math.radians(head))
        if fi == 0:
            for k, c in [(0, 5), (1, 5), (2, 4), (3, 3), (4, 2)]:
                for ddx, ddy in [(k, 0), (-k, 0), (0, k), (0, -k)]:
                    spark.set(hx + ddx, hy + ddy, c)
        if fi == 4:  # impact flash at the leading edge
            for k in range(1, 6):
                c = 5 if k < 3 else (4 if k < 5 else 3)
                for ddx, ddy in [(k, 0), (-k, 0), (0, k), (0, -k)]:
                    spark.set(hx + ddx, hy + ddy, c)
                if k < 4:
                    for ddx, ddy in [(k, k), (-k, k), (k, -k), (-k, -k)]:
                        spark.set(hx + ddx, hy + ddy, 4)
        if fi >= 4:  # shards flung along the tangent
            for k in range(7):
                t = (fi - 4 + hash01(k, 9)) / 4.0
                ang = math.radians(head - 25 - hash01(k, 8) * 70)
                rr = R + 2 * s + t * 9 * s
                x = cx + rr * math.cos(ang) + t * 4 * s
                y = cy + rr * math.sin(ang)
                c = 5 if t < 0.4 else (4 if t < 0.7 else 2)
                if t < 1.05 and 2 <= x < size - 3 and 2 <= y < size - 2:
                    spark.set(x, y, c)
                    if k % 2 == 0 and t < 0.6:
                        spark.set(x + 1, y, 3)
        d.paint(trail, l_trail, fi)
        d.paint(spark, l_spark, fi)
        d.duration(fi, DURATIONS[fi])
    d.tag("slash", 0, len(FRAMES) - 1)
    return d.calls
