"""Deterministic palette-index raster used by procedural builders to *compute* drawing
instructions. The pixels are then painted by the pixel engine (doc_paint_grid with palette indices),
so the editable source of truth is the layered engine document and its replayable recipe."""
from __future__ import annotations

import math

LEGEND_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


class Grid:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def set(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None

    def copy(self):
        g = Grid(self.w, self.h)
        g.px = [row[:] for row in self.px]
        return g

    def clear(self):
        self.px = [[None] * self.w for _ in range(self.h)]

    # ---- primitives
    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.set(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def polygon(self, pts, c):
        """Fill polygon sampling pixel centres (even-odd)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, int(math.floor(min(ys)))), min(self.h, int(math.ceil(max(ys))) + 1)):
            cy = y + 0.5
            xs = []
            n = len(pts)
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (y0 <= cy < y1) or (y1 <= cy < y0):
                    xs.append(x0 + (cy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.ceil(a - 0.5)), int(math.floor(b - 0.5)) + 1):
                    self.set(x, y, c if not callable(c) else c(x, y))

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.set(x, y, c if not callable(c) else c(x, y))

    def field(self, fn):
        """fn(x, y) -> colour index or None (None keeps the existing pixel)."""
        for y in range(self.h):
            for x in range(self.w):
                v = fn(x, y)
                if v is not None:
                    self.px[y][x] = v

    def outline(self, c, only_outer=True, diagonal=False):
        """Add a 1px outline around filled pixels (selective outer outline)."""
        src = [row[:] for row in self.px]
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (1, -1), (-1, 1), (-1, -1)] if diagonal else [])
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] is None and any(0 <= x + dx < self.w and 0 <= y + dy < self.h and src[y + dy][x + dx] is not None for dx, dy in nb):
                    self.px[y][x] = c

    def merge(self, other: "Grid"):
        for y in range(self.h):
            for x in range(self.w):
                if other.px[y][x] is not None:
                    self.px[y][x] = other.px[y][x]

    def bbox(self):
        pts = [(x, y) for y in range(self.h) for x in range(self.w) if self.px[y][x] is not None]
        if not pts:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def to_paint_grid(self, layer: int, frame: int, frame_to: int | None = None, replace: bool = False) -> dict | None:
        """Cropped doc_paint_grid call with integer palette-index legend."""
        bb = self.bbox()
        if bb is None:
            return None
        x0, y0, x1, y1 = bb
        used = sorted({v for row in self.px for v in row if v is not None})
        if len(used) > len(LEGEND_CHARS):
            raise ValueError("Too many colours for legend")
        key = {v: LEGEND_CHARS[i] for i, v in enumerate(used)}
        rows = ["".join(key[self.px[y][x]] if self.px[y][x] is not None else "." for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
        args = {"doc_id": "$DOC", "layer": layer, "frame": frame, "x": x0, "y": y0,
                "legend": {key[v]: v for v in used}, "rows": rows}
        if frame_to is not None:
            args["frame_to"] = frame_to
        if replace:
            args["replace"] = True
        return {"name": "doc_paint_grid", "arguments": args}


def bayer4(x, y):
    m = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
    return (m[int(y) % 4][int(x) % 4] + 0.5) / 16.0


def ramp_pick(t: float, ramp: list[int], x: int = 0, y: int = 0, dither: float = 0.35):
    """Map t in [0,1] to a ramp index, with ordered dithering at band edges."""
    t = max(0.0, min(0.9999, t))
    f = t * len(ramp)
    i = int(f)
    frac = f - i
    if dither and i + 1 < len(ramp) and frac > 1 - dither and bayer4(x, y) < (frac - (1 - dither)) / dither:
        i += 1
    return ramp[i]


def hash01(*v) -> float:
    """Deterministic hash noise in [0,1)."""
    h = 2166136261
    for x in v:
        h = ((h ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5bd1e995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def vnoise(x: float, y: float, seed: int = 0) -> float:
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b = hash01(xi, yi, seed), hash01(xi + 1, yi, seed)
    c, d = hash01(xi, yi + 1, seed), hash01(xi + 1, yi + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


class DocBuilder:
    """Accumulates pixel-engine tool calls for one document ("$DOC" is substituted at run time)."""

    def __init__(self, name: str, w: int, h: int):
        self.w, self.h = w, h
        self.calls = [{"name": "doc_new", "arguments": {"name": name, "width": w, "height": h}}]
        self.layers = ["Layer 1"]
        self.frames = 1

    def c(self, _tool, **args):
        args["doc_id"] = "$DOC"
        self.calls.append({"name": _tool, "arguments": args})

    def palette(self, colors):
        self.c("doc_palette", op="set", colors=list(colors))

    def layer(self, name) -> int:
        if self.layers == ["Layer 1"] and not any(c["name"] == "doc_layer" for c in self.calls):
            self.c("doc_layer", op="rename", index=0, name=name)
            self.layers = [name]
            return 0
        self.c("doc_layer", op="add", name=name)
        self.layers.append(name)
        return len(self.layers) - 1

    def add_frames(self, count, duration_ms=100, copy_from=None):
        a = {"op": "add", "count": count, "duration_ms": duration_ms}
        if copy_from is not None:
            a["copy_from"] = copy_from
        self.c("doc_frame", **a)
        self.frames += count

    def duration(self, frame, ms):
        self.c("doc_frame", op="duration", frame=frame, duration_ms=ms)

    def paint(self, grid: Grid, layer: int, frame: int, frame_to=None, replace=False):
        call = grid.to_paint_grid(layer, frame, frame_to, replace)
        if call:
            self.calls.append(call)

    def tag(self, name, frm, to):
        self.c("doc_add_tag", name=name, **{"from": frm, "to": to})
