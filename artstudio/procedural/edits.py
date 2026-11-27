"""Pixel Forge edits: quick adjustments applied on top of a builder, kept replayable.

`palette_map` replaces colours by value (the base colour → its replacement), so a swatch edit survives switching the
builder's own colour scheme: colours the new scheme does not use are simply not touched. `palette` (by index) is the
older form, kept for saved recipes. Colour edits rewrite the builder's `doc_palette` call *before* painting (builders paint by palette index, so the
whole asset recolours consistently). Everything else is appended as ordinary pixel-engine calls after the build
(frame durations, an outline / glow layer, flip, rescale), so the saved `doc.recipe` reproduces the edited asset.

    edits = {"speed": 1.0, "palette": ["#rrggbb", ...] | None, "palette_map": {"#from": "#to"} | None,
             "hue": 0, "saturation": 1.0, "brightness": 1.0,
             "outline": 0..3, "outline_color": "#rrggbb", "glow": 0..4, "glow_color": "#rrggbb" | None,
             "flip": False, "scale": 1..4, "loop": True | False | None}
"""
from __future__ import annotations

import colorsys
import copy
import re

import numpy as np

DEFAULTS = {"speed": 1.0, "palette": None, "palette_map": None, "hue": 0.0, "saturation": 1.0, "brightness": 1.0, "outline": 0,
            "outline_color": "#14101e", "glow": 0, "glow_color": None, "flip": False, "scale": 1, "loop": None}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class EditError(ValueError):
    pass


def _num(v, lo, hi, name, integer=False):
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise EditError(f"{name} must be a number") from None
    if not lo <= v <= hi:
        raise EditError(f"{name} must be between {lo} and {hi}")
    return int(round(v)) if integer else v


def normalize(edits: dict | None) -> dict:
    e = dict(DEFAULTS)
    for k, v in (edits or {}).items():
        if k not in DEFAULTS:
            raise EditError(f"Unknown edit {k}")
        e[k] = v
    e["speed"] = _num(e["speed"], 0.1, 5.0, "speed")
    e["hue"] = _num(e["hue"], -180, 180, "hue")
    e["saturation"] = _num(e["saturation"], 0.0, 2.0, "saturation")
    e["brightness"] = _num(e["brightness"], 0.3, 2.0, "brightness")
    e["outline"] = _num(e["outline"], 0, 3, "outline", True)
    e["glow"] = _num(e["glow"], 0, 4, "glow", True)
    e["scale"] = _num(e["scale"], 1, 4, "scale", True)
    e["flip"] = bool(e["flip"])
    for k in ("outline_color", "glow_color"):
        if e[k] is not None and not HEX.match(str(e[k])):
            raise EditError(f"{k} must be #rrggbb")
    if e["palette"] is not None:
        if not isinstance(e["palette"], list) or not all(HEX.match(str(c)) for c in e["palette"]):
            raise EditError("palette must be a list of #rrggbb colours")
    if e["palette_map"] is not None:
        m = e["palette_map"]
        if not isinstance(m, dict) or not all(HEX.match(str(k)) and HEX.match(str(v)) for k, v in m.items()):
            raise EditError("palette_map must map #rrggbb to #rrggbb")
        e["palette_map"] = {str(k).lower(): str(v).lower() for k, v in m.items() if str(k).lower() != str(v).lower()} or None
    if e["loop"] is not None:
        e["loop"] = bool(e["loop"])
    return e


def is_default(e: dict) -> bool:
    return all(e.get(k) == v for k, v in DEFAULTS.items())


def base_palette(calls: list[dict]) -> list[str] | None:
    for c in calls:
        if c.get("name") == "doc_palette" and c["arguments"].get("op") == "set":
            return [str(x)[:7].lower() for x in c["arguments"]["colors"]]
    return None


def adjust(hexcol: str, hue: float, sat: float, bri: float) -> str:
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + hue / 360.0) % 1.0
    s = max(0.0, min(1.0, s * sat))
    l = max(0.0, min(1.0, l * bri if bri <= 1 else l + (1 - l) * (bri - 1)))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in (r, g, b))


def final_palette(calls, e) -> list[str] | None:
    base = base_palette(calls)
    if base is None:
        return None
    pal = list(base)
    if e["palette"]:
        pal = [e["palette"][i] if i < len(e["palette"]) else c for i, c in enumerate(pal)]
    if e.get("palette_map"):
        pal = [e["palette_map"].get(c.lower(), c) for c in pal]
    if e["hue"] or e["saturation"] != 1.0 or e["brightness"] != 1.0:
        pal = [adjust(c, e["hue"], e["saturation"], e["brightness"]) for c in pal]
    return pal


def recolor_calls(calls: list[dict], e: dict) -> list[dict]:
    pal = final_palette(calls, e)
    if pal is None or pal == base_palette(calls):
        return calls
    out = copy.deepcopy(calls)
    for c in out:
        if c.get("name") == "doc_palette" and c["arguments"].get("op") == "set":
            c["arguments"]["colors"] = pal
            break
    return out


def _dilate(m: np.ndarray, n: int) -> np.ndarray:
    for _ in range(n):
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        m = g
    return m


def _bayer(h, w):
    b = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 + 1 / 32
    return np.tile(b, (h // 4 + 1, w // 4 + 1))[:h, :w]


def _grid_call(doc_id, layer, frame, mask, color):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    rows = ["".join("o" if mask[y, x] else "." for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
    return {"doc_id": doc_id, "layer": layer, "frame": int(frame), "x": int(x0), "y": int(y0), "legend": {"o": color}, "rows": rows}


def apply_post(eng, doc_id: str, e: dict, calls: list[dict]) -> None:
    """Append the non-colour edits as engine calls (recorded in the recipe). `calls` = the recoloured build calls."""
    d = eng._doc({"doc_id": doc_id})
    n = len(d.frames)
    if e["speed"] != 1.0:
        for i, f in enumerate(list(d.frames)):
            eng.call("doc_frame", {"doc_id": doc_id, "op": "duration", "frame": i,
                                   "duration_ms": max(10, int(round(f["duration_ms"] / e["speed"])))})
    if e["outline"] or e["glow"]:
        d = eng._doc({"doc_id": doc_id})
        masks = [d.render(i)[..., 3] > 0 for i in range(n)]
        pal = base_palette(calls) or ["#ffffff"]  # `calls` are already recoloured
        glow_col = e["glow_color"] or pal[-2 if len(pal) > 1 else -1]
        rings = []
        for i, m in enumerate(masks):
            o = _dilate(m, e["outline"]) if e["outline"] else m
            out_ring = o & ~m
            g_ring = None
            if e["glow"]:
                g = _dilate(o, e["glow"]) & ~o
                dist_mask = np.zeros_like(g, dtype=float)
                prev = o
                for k in range(1, e["glow"] + 1):  # denser close to the sprite, sparser further out
                    nxt = _dilate(prev, 1)
                    dist_mask[nxt & ~prev] = 1 - (k - 1) / e["glow"]
                    prev = nxt
                g_ring = g & (_bayer(*g.shape) < dist_mask * 0.75)
            rings.append((out_ring, g_ring))
        for kind, color in (("glow", glow_col), ("outline", e["outline_color"])):
            if (kind == "glow" and not e["glow"]) or (kind == "outline" and not e["outline"]):
                continue
            eng.call("doc_layer", {"doc_id": doc_id, "op": "add", "name": kind})
            li = len(eng._doc({"doc_id": doc_id}).layers) - 1
            eng.call("doc_layer", {"doc_id": doc_id, "op": "move", "index": li, "to_index": 0})
            for i, (o_ring, g_ring) in enumerate(rings):
                m = g_ring if kind == "glow" else o_ring
                if m is None:
                    continue
                args = _grid_call(doc_id, 0, i, m, color)
                if args:
                    eng.call("doc_paint_grid", args)
    if e["flip"]:
        d = eng._doc({"doc_id": doc_id})
        for li in range(len(d.layers)):
            eng.call("doc_fx", {"doc_id": doc_id, "op": "flip", "layer": li, "frame": 0, "frame_to": n - 1, "horizontal": True})
    if e["scale"] > 1:
        eng.call("doc_rescale", {"doc_id": doc_id, "factor": e["scale"]})
