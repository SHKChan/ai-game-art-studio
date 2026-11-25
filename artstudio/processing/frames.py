"""Shared frame-processing pipeline (both Pixel Art and HD Illustration modes).

Design rules (from SPECIFICATION §8-9 and Pixel Atelier's workflow):
  * One scale per animation group — never per-frame bbox fitting.
  * Placement keeps source-relative motion; anchoring is explicit and per-frame overridable.
  * The canvas expands instead of cropping weapons or effects.
  * Every placement is recorded so it can be reproduced or reversed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from ..util import StudioError

MODES = ("pixel", "hd")


# ---------------------------------------------------------------- basics
def to_np(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("RGBA"), dtype=np.uint8)


def from_np(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.ascontiguousarray(a, dtype=np.uint8), "RGBA")


def alpha_bbox(im: Image.Image, threshold: int = 1):
    """Bounding box (l,t,r,b) of pixels with alpha >= threshold, or None."""
    a = im.getchannel("A") if im.mode == "RGBA" else im.convert("RGBA").getchannel("A")
    if threshold > 1:
        a = a.point(lambda v: 255 if v >= threshold else 0)
    return a.getbbox()


def binary_alpha(im: Image.Image, threshold: int = 128) -> Image.Image:
    a = to_np(im).copy()
    on = a[..., 3] >= threshold
    a[..., 3] = np.where(on, 255, 0)
    a[~on, :3] = 0
    return from_np(a)


def has_partial_alpha(im: Image.Image) -> bool:
    a = to_np(im)[..., 3]
    return bool(((a > 0) & (a < 255)).any())


# ---------------------------------------------------------------- background
def _border_pixels(a: np.ndarray, width: int = 2) -> np.ndarray:
    return np.concatenate([a[:width].reshape(-1, 4), a[-width:].reshape(-1, 4),
                           a[:, :width].reshape(-1, 4), a[:, -width:].reshape(-1, 4)])


def detect_background(im: Image.Image) -> dict:
    """Classify the background: transparent, solid colour, or a baked-in checkerboard."""
    a = to_np(im)
    border = _border_pixels(a)
    if (border[:, 3] < 16).mean() > 0.9:
        return {"kind": "transparent"}
    rgb = border[:, :3].astype(int)
    keys, counts = np.unique((rgb // 8), axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    top = counts[order[0]] / len(rgb)
    if top > 0.6:
        c = rgb[(rgb // 8 == keys[order[0]]).all(1)].mean(0).round().astype(int)
        return {"kind": "solid", "color": c.tolist(), "coverage": round(float(top), 3)}
    if len(order) > 1 and (counts[order[0]] + counts[order[1]]) / len(rgb) > 0.8:
        c1 = rgb[(rgb // 8 == keys[order[0]]).all(1)].mean(0).round().astype(int)
        c2 = rgb[(rgb // 8 == keys[order[1]]).all(1)].mean(0).round().astype(int)
        if abs(int(c1.mean()) - int(c2.mean())) < 90 and np.abs(c1 - c2).max() < 90:
            return {"kind": "checker", "colors": [c1.tolist(), c2.tolist()]}
    return {"kind": "complex"}


def _flood_from_border(candidate: np.ndarray) -> np.ndarray:
    """Pixels in `candidate` connected (4-neighbour) to the image border. Vectorised propagation."""
    reach = np.zeros_like(candidate)
    reach[0, :] = candidate[0, :]
    reach[-1, :] = candidate[-1, :]
    reach[:, 0] |= candidate[:, 0]
    reach[:, -1] |= candidate[:, -1]
    for _ in range(4096):
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= candidate
        if (grown == reach).all():
            break
        reach = grown
    return reach


def remove_background(im: Image.Image, mode: str = "pixel", method: str = "auto", color=None,
                      tolerance: float = 28.0, connected: bool = True, feather: float = 0.0) -> tuple[Image.Image, dict]:
    """Remove a solid/checker background colour.

    pixel mode -> binary alpha; hd mode -> soft edge alpha proportional to colour distance
    in the band [tolerance, tolerance+feather] (preserves anti-aliasing).
    """
    a = to_np(im).copy()
    info = detect_background(im) if method == "auto" else {"kind": method}
    if info["kind"] == "transparent" and color is None:
        return im.convert("RGBA"), {"method": "none", "reason": "already transparent"}
    if color is not None:
        colors = [list(color)[:3]]
    elif info["kind"] == "solid":
        colors = [info["color"]]
    elif info["kind"] == "checker":
        colors = info["colors"]
    else:
        raise StudioError("Background is not a solid colour or checkerboard; supply an explicit colour or use an external matting tool.")
    rgb = a[..., :3].astype(np.float32)
    dist = np.min(np.stack([np.sqrt(((rgb - np.array(c, np.float32)) ** 2).sum(-1)) for c in colors]), axis=0)
    soft = 0.0
    if mode == "hd":
        soft = feather if feather > 0 else tolerance  # soft band preserves anti-aliased edges
    candidate = dist <= tolerance + soft
    region = _flood_from_border(candidate) if connected else candidate
    alpha = a[..., 3].astype(np.float32)
    if mode == "hd" and soft > 0:
        t = np.clip((dist - tolerance) / soft, 0, 1)
        new_alpha = np.where(region, alpha * t, alpha)
        # Decontaminate edge colour: remove the background contribution from partially kept pixels.
        bg = np.array(colors[0], np.float32)
        k = np.where(region & (t > 0), t, 1.0)[..., None]
        fixed = np.clip((rgb - bg * (1 - k)) / np.maximum(k, 1e-3), 0, 255)
        a[..., :3] = np.where((region & (t > 0))[..., None], fixed, rgb).astype(np.uint8)
    else:
        new_alpha = np.where(region, 0, alpha)
    a[..., 3] = new_alpha.round().astype(np.uint8)
    a[a[..., 3] == 0, :3] = 0
    out = from_np(a)
    return out, {"method": info["kind"] if color is None else "color", "colors": colors, "tolerance": tolerance,
                 "soft_band": soft, "connected": connected, "removed_px": int(region.sum())}


# ---------------------------------------------------------------- slicing
def slice_grid(sheet: Image.Image, cols: int, rows: int, count: int | None = None,
               margin: int = 0, spacing: int = 0, cell: tuple[int, int] | None = None) -> list[tuple[Image.Image, list[int]]]:
    if cols < 1 or rows < 1:
        raise StudioError("cols/rows must be >= 1")
    W, H = sheet.size
    out = []
    n = count or cols * rows
    for i in range(n):
        cx, cy = i % cols, i // cols
        if cy >= rows:
            break
        if cell:
            x0 = margin + cx * (cell[0] + spacing)
            y0 = margin + cy * (cell[1] + spacing)
            rect = [x0, y0, x0 + cell[0], y0 + cell[1]]
        else:
            uw = (W - 2 * margin - (cols - 1) * spacing) / cols
            uh = (H - 2 * margin - (rows - 1) * spacing) / rows
            rect = [round(margin + cx * (uw + spacing)), round(margin + cy * (uh + spacing)),
                    round(margin + cx * (uw + spacing) + uw), round(margin + cy * (uh + spacing) + uh)]
        out.append((sheet.crop(tuple(rect)).convert("RGBA"), [rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]]))
    return out


def _label_runs(mask: np.ndarray):
    """Connected-component labelling (8-neighbour) via run-length union-find. Returns list of bboxes."""
    parent: list[int] = []

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    prev_runs: list[tuple[int, int, int]] = []
    runs_all: list[tuple[int, int, int, int]] = []
    for y in range(mask.shape[0]):
        row = mask[y]
        if not row.any():
            prev_runs = []
            continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        cur = []
        for s, e in zip(starts, ends):
            lab = len(parent)
            parent.append(lab)
            for ps, pe, pl in prev_runs:
                if ps <= e and pe >= s - 0:  # overlap incl. diagonal (8-conn)
                    ra, rb = find(lab), find(pl)
                    if ra != rb:
                        parent[ra] = rb
            cur.append((s - 1 if s > 0 else 0, e + 0, lab))
            runs_all.append((y, s, e, lab))
        prev_runs = [(s, e, l) for s, e, l in cur]
    boxes: dict[int, list[int]] = {}
    for y, s, e, lab in runs_all:
        r = find(lab)
        b = boxes.setdefault(r, [s, y, e, y + 1])
        b[0], b[1], b[2], b[3] = min(b[0], s), min(b[1], y), max(b[2], e), max(b[3], y + 1)
    return list(boxes.values())


def slice_auto(sheet: Image.Image, merge_px: int = 4, min_area: int = 16, alpha_threshold: int = 16,
               order: str = "rows") -> list[tuple[Image.Image, list[int]]]:
    """Segment sprites on a transparent sheet by connected components (dilated by merge_px so
    detached weapons/effects stay with their sprite). Returns crops ordered row-major."""
    a = to_np(sheet)[..., 3] >= alpha_threshold
    if not a.any():
        raise StudioError("Sheet has no visible pixels (is the background transparent?)")
    m = a.copy()
    for _ in range(max(0, merge_px)):
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        m = g
    boxes = []
    for l, t, r, b in _label_runs(m):
        sub = a[t:b, l:r]
        if sub.sum() < min_area:
            continue
        ys, xs = np.where(sub)
        boxes.append([l + xs.min(), t + ys.min(), l + xs.max() + 1, t + ys.max() + 1])
    if not boxes:
        raise StudioError("No sprites found")
    # Row-major ordering: cluster by vertical centre using median height as row tolerance.
    hmed = float(np.median([b[3] - b[1] for b in boxes]))
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows_, cur = [], [boxes[0]]
    for b in boxes[1:]:
        if abs((b[1] + b[3]) / 2 - (cur[-1][1] + cur[-1][3]) / 2) < hmed * 0.5:
            cur.append(b)
        else:
            rows_.append(cur); cur = [b]
    rows_.append(cur)
    ordered = [b for row in rows_ for b in sorted(row, key=lambda b: b[0])]
    return [(sheet.crop(tuple(int(v) for v in b)).convert("RGBA"), [int(b[0]), int(b[1]), int(b[2] - b[0]), int(b[3] - b[1])]) for b in ordered]


# ---------------------------------------------------------------- scaling / colour
def resample(im: Image.Image, size: tuple[int, int], mode: str) -> Image.Image:
    """pixel: nearest-neighbour. hd: Lanczos on premultiplied alpha (Pillow premultiplies RGBA)."""
    size = (max(1, int(size[0])), max(1, int(size[1])))
    if size == im.size:
        return im.copy()
    return im.resize(size, Image.Resampling.NEAREST if mode == "pixel" else Image.Resampling.LANCZOS)


def estimate_pixel_scale(im: Image.Image, max_block: int = 32) -> int:
    """Estimate the block size of upscaled pixel art (e.g. AI 'pixel art' at 1024 px)."""
    a = to_np(im).astype(np.int32)
    key = (a[..., 0] << 24) ^ (a[..., 1] << 16) ^ (a[..., 2] << 8) ^ a[..., 3]
    runs = []
    for arr in (key, key.T):
        change = np.ones(arr.shape, bool)
        change[:, 1:] = arr[:, 1:] != arr[:, :-1]
        for row in change[:: max(1, arr.shape[0] // 64)]:
            idx = np.flatnonzero(row)
            runs.extend(np.diff(np.append(idx, len(row))).tolist())
    runs = [r for r in runs if 1 <= r <= max_block * 4]
    if not runs:
        return 1
    best, best_score = 1, 0.0
    for b in range(2, max_block + 1):
        score = sum(1 for r in runs if r % b == 0) / len(runs)
        if score > 0.9 and b > best:
            best, best_score = b, score
    return best


def depixelate(im: Image.Image, block: int) -> Image.Image:
    """Downsample upscaled pixel art by sampling block centres (no new colours)."""
    if block <= 1:
        return im.copy()
    a = to_np(im)
    off = block // 2
    return from_np(a[off::block, off::block])


def median_cut_palette(images: list[Image.Image], count: int = 32, alpha_threshold: int = 128) -> list[str]:
    px = []
    for im in images:
        a = to_np(im).reshape(-1, 4)
        px.append(a[a[:, 3] >= alpha_threshold][:, :3])
    allpx = np.concatenate(px) if px else np.zeros((0, 3), np.uint8)
    if len(allpx) == 0:
        raise StudioError("No opaque pixels to build a palette from")
    if len(allpx) > 200_000:
        allpx = allpx[:: len(allpx) // 200_000]
    q = Image.fromarray(allpx.reshape(1, -1, 3), "RGB").quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    used = sorted(set(q.getdata()))
    return list(dict.fromkeys("#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]) for i in used))


def apply_palette(im: Image.Image, palette: list[str], alpha_threshold: int = 128) -> Image.Image:
    """Snap opaque pixels to the nearest palette colour (vectorised; equivalent in result to
    Pixel Atelier's spritepipe.core.map_palette which is used for its own pipeline)."""
    cols = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in palette], np.int32)
    a = to_np(im).copy()
    flat = a.reshape(-1, 4)
    on = flat[:, 3] >= alpha_threshold
    rgb = flat[on, :3].astype(np.int32)
    if len(rgb):
        uniq, inv = np.unique(rgb, axis=0, return_inverse=True)
        d = ((uniq[:, None, :] - cols[None, :, :]) ** 2).sum(-1)
        flat[on, :3] = cols[d.argmin(1)][inv.reshape(-1)]
    flat[on, 3] = 255
    flat[~on] = 0
    return from_np(flat.reshape(a.shape))


# ---------------------------------------------------------------- normalisation
@dataclass
class NormalizeParams:
    mode: str = "pixel"                 # pixel | hd
    anchor: str = "source"              # source | ground | support_foot | torso | custom
    scale: float = 1.0                  # one uniform scale for the whole group
    target_height: int | None = None    # alternative: scale so the reference frame's height == this
    reference_frame: int = 0
    canvas: list[int] | None = None     # None = auto (fits everything, expands, never crops)
    pivot: list[int] | None = None      # logical root in the canvas; None = bottom-centre of auto canvas
    padding: int = 4
    alpha_threshold: int = 16
    airborne: list[int] = field(default_factory=list)   # frames exempt from ground snapping
    manual_offsets: dict = field(default_factory=dict)  # {frame_index: [dx, dy]} added last
    foot_band: float = 0.08            # fraction of sprite height treated as the "foot" band
    torso_band: tuple = (0.35, 0.6)
    binary_alpha: bool | None = None    # default: True in pixel mode, False in hd
    palette: list[str] | None = None    # pixel mode optional fixed palette
    palette_size: int | None = None     # pixel mode optional auto palette
    source_pivot: list[int] | None = None  # anchor=source: this cell-space point maps to the canvas pivot

    @classmethod
    def from_dict(cls, d: dict | None) -> "NormalizeParams":
        d = dict(d or {})
        p = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        if p.mode not in MODES:
            raise StudioError("mode must be pixel or hd")
        if p.anchor not in ("source", "ground", "support_foot", "torso", "custom"):
            raise StudioError("unknown anchor")
        p.manual_offsets = {int(k): list(v) for k, v in (p.manual_offsets or {}).items()}
        p.airborne = [int(x) for x in p.airborne]
        if not (0 < float(p.scale) <= 64):
            raise StudioError("scale must be in (0, 64]")
        return p


def _band_centroid_x(alpha: np.ndarray, top: int, bottom: int):
    band = alpha[max(0, top):max(top + 1, bottom)]
    ys, xs = np.nonzero(band)
    return float(xs.mean()) if len(xs) else None


def normalize_group(frames: list[Image.Image], params: NormalizeParams | dict | None = None) -> tuple[list[Image.Image], dict]:
    """Place a group of source frames (same coordinate system, e.g. cells of one sheet) on a
    shared canvas with ONE uniform scale and an explicit anchor policy.

    Returns (frames, record). record['frames'][i]['offset'] is where the scaled source cell's
    top-left lands on the canvas; with record['scale'] it fully reproduces the result.
    """
    p = params if isinstance(params, NormalizeParams) else NormalizeParams.from_dict(params)
    if not frames:
        raise StudioError("No frames")
    if p.binary_alpha is None:
        p.binary_alpha = p.mode == "pixel"
    srcs = [f.convert("RGBA") for f in frames]
    bbs = [alpha_bbox(f, p.alpha_threshold) for f in srcs]
    if any(b is None for b in bbs):
        bad = [i for i, b in enumerate(bbs) if b is None]
        raise StudioError(f"Empty frames: {bad}")
    scale = float(p.scale)
    if p.target_height:
        rb = bbs[p.reference_frame]
        scale = p.target_height / (rb[3] - rb[1])
    if p.mode == "pixel" and scale >= 1:
        scale = max(1, round(scale))  # integer upscale keeps square pixel clusters
    scaled = [resample(f, (round(f.width * scale), round(f.height * scale)), p.mode) for f in srcs]
    sbbs = [alpha_bbox(f, p.alpha_threshold) for f in scaled]
    # Source-relative common reference: union of bboxes in cell space.
    ul = min(b[0] for b in sbbs); ur = max(b[2] for b in sbbs); ub = max(b[3] for b in sbbs)
    common_x, common_y = (ul + ur) / 2, ub
    if p.source_pivot:
        common_x, common_y = p.source_pivot[0] * scale, p.source_pivot[1] * scale
    ref_points = []
    for i, (f, b) in enumerate(zip(scaled, sbbs)):
        al = to_np(f)[..., 3] >= p.alpha_threshold
        h = b[3] - b[1]
        rx, ry = common_x, common_y
        if p.anchor in ("ground", "support_foot") and i not in p.airborne:
            ry = b[3]
        if p.anchor == "support_foot":
            cx = _band_centroid_x(al, b[3] - max(1, round(h * p.foot_band)), b[3])
            rx = cx if cx is not None else rx
        if p.anchor == "torso":
            ut = min(x[1] for x in sbbs)
            uh = ub - ut
            cx = _band_centroid_x(al, round(ut + uh * p.torso_band[0]), round(ut + uh * p.torso_band[1]))
            rx = cx if cx is not None else rx
        ref_points.append((rx, ry))
    # Airborne frames in ground mode keep their source-relative height: offset relative to common ground.
    # Provisional placement with pivot at (0,0): offset = -ref
    offs = []
    for i, (rx, ry) in enumerate(ref_points):
        dx, dy = -rx, -ry
        m = p.manual_offsets.get(i, [0, 0])
        offs.append([round(dx + m[0]), round(dy + m[1])])
    placed = [(o[0] + b[0], o[1] + b[1], o[0] + b[2], o[1] + b[3]) for o, b in zip(offs, sbbs)]
    L = min(x[0] for x in placed); T = min(x[1] for x in placed); R = max(x[2] for x in placed); B = max(x[3] for x in placed)
    if p.canvas and p.pivot:
        cw, ch = p.canvas
        px, py = p.pivot
        # Expand canvas if content would be cropped (never crop weapons/effects).
        grow_l = max(0, -(px + L) + p.padding)
        grow_t = max(0, -(py + T) + p.padding)
        grow_r = max(0, px + R + p.padding - cw)
        grow_b = max(0, py + B + p.padding - ch)
        if grow_l or grow_t or grow_r or grow_b:
            cw, ch, px, py = cw + grow_l + grow_r, ch + grow_t + grow_b, px + grow_l, py + grow_t
        expanded = bool(grow_l or grow_t or grow_r or grow_b)
    else:
        half = max(-L, R) + p.padding
        cw = int(math.ceil(half * 2))
        px = int(math.ceil(half))
        top_room = -T + p.padding
        py = int(math.ceil(top_room))
        ch = int(math.ceil(py + max(B, 0) + p.padding))
        expanded = False
    out, recs = [], []
    for i, (f, o, b) in enumerate(zip(scaled, offs, sbbs)):
        canvas = Image.new("RGBA", (int(cw), int(ch)), (0, 0, 0, 0))
        x, y = int(px + o[0]), int(py + o[1])
        canvas.alpha_composite(f, (x, y)) if x >= 0 and y >= 0 else canvas.paste(f, (x, y), f)
        if p.mode == "pixel":
            if p.palette:
                canvas = apply_palette(canvas, p.palette, 128)
            elif p.binary_alpha:
                canvas = binary_alpha(canvas, 128)
        bb = alpha_bbox(canvas)
        recs.append({"index": i, "offset": [x, y], "source_size": list(srcs[i].size),
                     "scaled_size": list(f.size), "trimmed_rect": [bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]] if bb else None,
                     "reference_point": [round(ref_points[i][0], 2), round(ref_points[i][1], 2)],
                     "airborne": i in p.airborne})
        out.append(canvas)
    if p.mode == "pixel" and p.palette_size and not p.palette:
        pal = median_cut_palette(out, p.palette_size)
        out = [apply_palette(f, pal, 128) for f in out]
        palette = pal
    else:
        palette = p.palette
    record = {"params": {k: getattr(p, k) for k in p.__dataclass_fields__}, "scale": scale,
              "canvas": [int(cw), int(ch)], "pivot": [int(px), int(py)], "canvas_expanded": expanded,
              "palette": palette, "frames": recs}
    record["params"]["manual_offsets"] = {str(k): v for k, v in p.manual_offsets.items()}
    return out, record


def compose_layers(base: Image.Image, overlay: Image.Image, base_pivot, overlay_pivot, offset=(0, 0)) -> Image.Image:
    """Composite an overlay layer (e.g. effect) aligned by pivots; expands the canvas as needed."""
    ox = base_pivot[0] - overlay_pivot[0] + offset[0]
    oy = base_pivot[1] - overlay_pivot[1] + offset[1]
    L, T = min(0, ox), min(0, oy)
    R, B = max(base.width, ox + overlay.width), max(base.height, oy + overlay.height)
    c = Image.new("RGBA", (R - L, B - T), (0, 0, 0, 0))
    c.alpha_composite(base, (-L, -T))
    c.alpha_composite(overlay, (ox - L, oy - T))
    return c
