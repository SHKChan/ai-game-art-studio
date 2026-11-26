"""Action sheet processing: one generated image (all frames of one action in a fixed grid) -> clean frames.

Pipeline (each step recorded so it can be re-run with new parameters from the preserved sheet):

  1. background  — solid/checker background -> transparent (no-op for real transparent PNGs)
  2. segment     — connected components assigned to grid cells by centre; specks dropped; a component that
                   spans two cells or touches the sheet border is reported (usually a broken generation)
  3. resample    — AI "pixel art" is drawn at a large size with soft, uneven pseudo-pixels. Every output pixel
                   samples ONE source pixel on a regular grid. The step is chosen ONCE per sheet so the
                   reference pose reaches `target_height` (default 64 px) — never per-frame fitting
                   (Pixel Atelier rule: one scale per sheet). The grid phase follows the detected pixel grid.
  4. cleanup     — binary alpha, background-coloured fringe removed, isolated specks removed, 1-px holes filled
  5. palette     — snap to the character palette (taken from the reference image) so colours never drift
  6. QA          — cell count, empty cells, size drift, cross-cell components -> pass / retry

Placement on the shared canvas (ground line, pivot) is done afterwards by processing.frames.normalize_group.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from ..util import StudioError
from .frames import apply_palette, from_np, median_cut_palette, remove_background, to_np

DEFAULTS = {"target_height": 64, "scale_ref": "first", "alpha_threshold": 128, "min_speck": 3, "palette": None,
            "palette_size": 32, "fringe_tolerance": 60, "fill_holes": True, "step": None}


# ------------------------------------------------------------------ layout
def grid_for(n: int) -> tuple[int, int]:
    """Columns x rows used to ask the model for n frames (near-square sheets generate far more reliably)."""
    n = int(n)
    if n <= 3:
        return n, 1
    if n == 4:
        return 2, 2
    if n <= 6:
        return 3, 2
    cols = 4
    return cols, math.ceil(n / cols)


# ------------------------------------------------------------------ connected components with labels
def label(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """8-connected component labelling (run-length union-find). Returns (labels, count); 0 = background."""
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    prev: list[tuple[int, int, int]] = []
    runs: list[tuple[int, int, int, int]] = []
    for y in range(H):
        row = mask[y]
        if not row.any():
            prev = []
            continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur = []
        for s, e in zip(starts, ends):
            k = len(parent)
            parent.append(k)
            for ps, pe, pk in prev:
                if ps <= e and pe >= s:  # touching incl. diagonals ([s,e) vs [ps,pe) widened by one)
                    a, b = find(k), find(pk)
                    if a != b:
                        parent[max(a, b)] = min(a, b)
            cur.append((s - 1, e + 1, k))
            runs.append((y, s, e, k))
        prev = cur
    roots: dict[int, int] = {}
    for y, s, e, k in runs:
        r = find(k)
        lab[y, s:e] = roots.setdefault(r, len(roots) + 1)
    return lab, len(roots)


# ------------------------------------------------------------------ pseudo-pixel grid
def detect_grid(im: Image.Image, max_block: int = 24) -> dict:
    """Estimate the pseudo-pixel size and phase of upscaled / AI pixel art from colour-edge periodicity.

    Returns {"block": float, "phase": [px, py], "confidence": 0..1}. block 1.0 means no upscaling detected."""
    a = to_np(im).astype(np.float32)
    on = a[..., 3] >= 128
    if on.sum() < 64:
        return {"block": 1.0, "phase": [0.0, 0.0], "confidence": 0.0}
    rgb = a[..., :3] * (a[..., 3:4] / 255.0)
    out = {}
    for axis, name in ((1, "x"), (0, "y")):
        g = np.abs(np.diff(rgb, axis=axis)).sum(-1)
        sig = g.sum(axis=0 if axis == 1 else 1)
        sig = sig - sig.mean()
        n = len(sig)
        if n < 8:
            out[name] = (1.0, 0.0, 0.0)
            continue
        ac = np.correlate(sig, sig, "full")[n - 1:]
        ac = ac / (ac[0] + 1e-9)
        peaks = [(p, float(ac[p])) for p in range(2, min(max_block, n // 4) + 1)
                 if ac[p] >= ac[p - 1] and (p + 1 >= len(ac) or ac[p] >= ac[p + 1]) and ac[p] > 0.05]
        best_p, best_v = 1.0, 0.0
        if peaks:
            top = max(v for _, v in peaks)
            best_p, best_v = next((float(p), v) for p, v in peaks if v >= 0.6 * top)  # fundamental, not a harmonic
        if best_p > 1 and best_v > 0.05:
            # refine period with the 4th harmonic when available (handles non-integer blocks like 5.33)
            k = int(best_p * 4)
            if k + 2 < len(ac):
                lo, hi = max(1, int(best_p * 4 - 3)), min(len(ac) - 1, int(best_p * 4 + 3))
                k = lo + int(np.argmax(ac[lo:hi + 1]))
                best_p = k / 4.0 if abs(k / 4.0 - best_p) < 0.75 else best_p
            idx = np.arange(n)
            phase_score = [sig[np.round(np.arange(ph, n, best_p)).astype(int).clip(0, n - 1)].mean()
                           for ph in np.linspace(0, best_p, 12, endpoint=False)]
            phase = float(np.linspace(0, best_p, 12, endpoint=False)[int(np.argmax(phase_score))]) + 1.0  # edge -> next pixel
            out[name] = (best_p, phase % best_p, best_v)
        else:
            out[name] = (1.0, 0.0, 0.0)
    bx, by = out["x"][0], out["y"][0]
    block = (bx + by) / 2 if bx > 1 and by > 1 and abs(bx - by) < 1.0 else max(bx, by) if min(bx, by) <= 1 else (bx + by) / 2
    return {"block": round(float(block), 3), "phase": [round(out["x"][1], 2), round(out["y"][1], 2)],
            "confidence": round(float(min(out["x"][2], out["y"][2]) if bx > 1 and by > 1 else 0.0), 3)}


def sample(im: Image.Image, step: float, phase=(0.0, 0.0)) -> Image.Image:
    """Point-sample im on a regular grid with spacing `step` (one source pixel per output pixel)."""
    a = to_np(im)
    H, W = a.shape[:2]
    px, py = phase
    xs = np.arange(px % step + step / 2, W, step)
    ys = np.arange(py % step + step / 2, H, step)
    xs = np.clip(np.floor(xs).astype(int), 0, W - 1)
    ys = np.clip(np.floor(ys).astype(int), 0, H - 1)
    if not len(xs) or not len(ys):
        raise StudioError("Frame too small to resample")
    return from_np(a[np.ix_(ys, xs)])


# ------------------------------------------------------------------ cleanup
def _neighbours(m: np.ndarray) -> np.ndarray:
    p = np.pad(m.astype(np.int16), 1)
    return sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx]
               for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)


def cleanup(im: Image.Image, *, alpha_threshold: int = 128, min_speck: int = 3, bg_colors=None, fringe_tolerance: float = 60,
            fill_holes: bool = True) -> tuple[Image.Image, dict]:
    a = to_np(im).copy()
    on = a[..., 3] >= alpha_threshold
    stats = {"fringe": 0, "specks": 0, "holes": 0}
    # fringe: edge pixels that are close to the removed background colour (white/grey halos)
    if bg_colors:
        edge = on & (_neighbours(on) < 8)
        rgb = a[..., :3].astype(np.float32)
        d = np.min(np.stack([np.sqrt(((rgb - np.array(c, np.float32)) ** 2).sum(-1)) for c in bg_colors]), axis=0)
        fr = edge & (d <= fringe_tolerance)
        stats["fringe"] = int(fr.sum())
        on &= ~fr
    # specks: tiny components far from the body
    lab, n = label(on)
    if n > 1:
        sizes = np.bincount(lab.ravel())
        small = [i for i in range(1, n + 1) if sizes[i] < min_speck]
        if small:
            kill = np.isin(lab, small)
            stats["specks"] = int(kill.sum())
            on &= ~kill
    # 1-px holes fully surrounded by the sprite
    if fill_holes:
        hole = (~on) & (_neighbours(on) >= 8)
        if hole.any():
            ys, xs = np.nonzero(hole)
            for y, x in zip(ys, xs):
                nb = a[max(0, y - 1):y + 2, max(0, x - 1):x + 2].reshape(-1, 4)
                nb = nb[nb[:, 3] >= alpha_threshold]
                if len(nb):
                    a[y, x, :3] = np.median(nb[:, :3], axis=0)
            stats["holes"] = int(hole.sum())
            on |= hole
    a[..., 3] = np.where(on, 255, 0)
    a[~on, :3] = 0
    return from_np(a), stats


# ------------------------------------------------------------------ main entry
def reference_palette(ref: Image.Image, size: int = 32, target_height: int | None = None) -> list[str]:
    r = ref.convert("RGBA")
    if r.getchannel("A").getextrema()[0] == 255:
        r, _ = remove_background(r, mode="pixel")
    bb = r.getchannel("A").point(lambda v: 255 if v >= 128 else 0).getbbox()
    if bb:
        r = r.crop(bb)
    g = detect_grid(r)
    if g["block"] > 1.5:
        r = sample(r, g["block"], g["phase"])
    elif target_height and r.height > target_height * 1.5:
        r = sample(r, r.height / target_height)
    return median_cut_palette([r], size)


def process_sheet(sheet: Image.Image, frames: int, cols: int | None = None, rows: int | None = None,
                  params: dict | None = None) -> tuple[list[Image.Image], dict]:
    """Cut one action sheet into `frames` clean frames (cell-relative placement, common scale).

    Returns (frames, record). record["qa"] = {"status": pass|retry, "issues": [...]}."""
    p = {**DEFAULTS, **(params or {})}
    if not cols or not rows:
        cols, rows = grid_for(frames)
    if cols * rows < frames:
        raise StudioError(f"grid {cols}x{rows} cannot hold {frames} frames")
    rec = {"params": {k: p[k] for k in DEFAULTS}, "grid": [cols, rows], "frames_expected": frames, "issues": []}
    issues = rec["issues"]
    im = sheet.convert("RGBA")
    bg_colors = None
    if im.getchannel("A").getextrema()[0] == 255:
        try:
            im, info = remove_background(im, mode="pixel", tolerance=40)
            bg_colors = info.get("colors")
            rec["background"] = {k: info[k] for k in ("method", "colors", "removed_px") if k in info}
        except StudioError as e:
            raise StudioError(f"Could not remove the sheet background: {e}", code="sheet_background") from e
    else:
        rec["background"] = {"method": "none"}
    a = to_np(im)
    on = a[..., 3] >= 64
    H, W = on.shape
    cw, ch = W / cols, H / rows
    lab, n = label(on)
    if not n:
        raise StudioError("The generated sheet is empty", code="sheet_empty")
    sizes = np.bincount(lab.ravel())
    # assign each component to the cell holding its pixel-mass centre
    ys, xs = np.nonzero(lab)
    labs = lab[ys, xs]
    cx = np.bincount(labs, weights=xs, minlength=n + 1) / np.maximum(sizes, 1)
    cy = np.bincount(labs, weights=ys, minlength=n + 1) / np.maximum(sizes, 1)
    minx = np.full(n + 1, W); maxx = np.zeros(n + 1, int); miny = np.full(n + 1, H); maxy = np.zeros(n + 1, int)
    np.minimum.at(minx, labs, xs); np.maximum.at(maxx, labs, xs); np.minimum.at(miny, labs, ys); np.maximum.at(maxy, labs, ys)
    body_min = max(12, int(sizes[1:].max() * 0.002))
    cell_of = {}
    for k in range(1, n + 1):
        if sizes[k] < body_min:
            continue
        c = min(cols - 1, int(cx[k] // cw)) + cols * min(rows - 1, int(cy[k] // ch))
        cell_of[k] = c
        c0, c1 = int(minx[k] // cw), int(maxx[k] // cw)
        r0, r1 = int(miny[k] // ch), int(maxy[k] // ch)
        if sizes[k] > sizes[1:].max() * 0.25 and (c0 != c1 or r0 != r1):
            span = (maxx[k] - minx[k]) / cw, (maxy[k] - miny[k]) / ch
            if max(span) > 1.15:  # clearly larger than one cell -> merged characters
                issues.append({"code": "cross_cell", "severity": "error", "cell": c, "msg": f"a sprite spans several cells (cell {c + 1})"})
        if minx[k] <= 0 or miny[k] <= 0 or maxx[k] >= W - 1 or maxy[k] >= H - 1:
            issues.append({"code": "touches_border", "severity": "warning", "cell": c, "msg": f"cell {c + 1} touches the sheet border (cropped?)"})
    cells = []
    for c in range(cols * rows):
        ks = [k for k, cc in cell_of.items() if cc == c]
        x0, y0 = c % cols * cw, c // cols * ch
        if not ks:
            cells.append(None)
            continue
        mask = np.isin(lab, ks)
        l, t = int(min(minx[k] for k in ks)), int(min(miny[k] for k in ks))
        r, b = int(max(maxx[k] for k in ks)) + 1, int(max(maxy[k] for k in ks)) + 1
        crop = a[t:b, l:r].copy()
        crop[~mask[t:b, l:r]] = 0
        cells.append({"img": from_np(crop), "rect": [l, t, r - l, b - t], "cell_origin": [x0, y0], "height": b - t, "width": r - l})
    used = [c for c in cells[:frames]]
    extra = [i for i, c in enumerate(cells[frames:], frames) if c is not None]
    empty = [i for i, c in enumerate(used) if c is None]
    for i in empty:
        issues.append({"code": "empty_cell", "severity": "error", "cell": i, "msg": f"cell {i + 1} is empty"})
    if extra:
        issues.append({"code": "extra_cells", "severity": "warning", "msg": f"{len(extra)} extra sprite(s) outside the expected frames ignored"})
    if empty:
        rec["qa"] = {"status": "retry", "issues": issues}
        raise SheetRejected(f"{len(empty)} of {frames} cells are empty", rec)
    heights = np.array([c["height"] for c in used], float)
    med = float(np.median(heights))
    # one step for the whole sheet
    ref_h = heights[0] if p["scale_ref"] == "first" else med
    grid = detect_grid(im.crop(tuple(int(v) for v in (used[0]["rect"][0], used[0]["rect"][1],
                                                      used[0]["rect"][0] + used[0]["rect"][2], used[0]["rect"][1] + used[0]["rect"][3]))))
    if p.get("step"):
        step = float(p["step"])
    elif p["target_height"]:
        step = ref_h / float(p["target_height"])
    else:
        step = grid["block"] if grid["block"] > 1.5 else 1.0
    step = max(step, 1.0)
    rec["detected_grid"] = grid
    rec["step"] = round(step, 4)
    # sample every cell on the SAME global grid (phase from the detected pixel grid), cell-relative output
    phase = grid["phase"] if grid["block"] > 1.5 and abs(grid["block"] - step) < 0.25 * step else [0.0, 0.0]
    out, frecs = [], []
    canvas_w = int(math.ceil(cw / step)) + 2
    canvas_h = int(math.ceil(ch / step)) + 2
    for i, c in enumerate(used):
        l, t, w, h = c["rect"]
        # global grid positions keep sub-pixel motion consistent between cells
        gx0 = math.floor((l - phase[0]) / step) * step + phase[0]
        gy0 = math.floor((t - phase[1]) / step) * step + phase[1]
        pad_l, pad_t = l - gx0, t - gy0
        src = Image.new("RGBA", (int(math.ceil(w + pad_l + step)), int(math.ceil(h + pad_t + step))), (0, 0, 0, 0))
        src.alpha_composite(c["img"], (int(round(pad_l)), int(round(pad_t))))
        small = sample(src, step)
        small, cst = cleanup(small, alpha_threshold=p["alpha_threshold"], min_speck=p["min_speck"], bg_colors=bg_colors,
                             fringe_tolerance=p["fringe_tolerance"], fill_holes=p["fill_holes"])
        # place cell-relative on a fixed per-cell canvas (keeps the model's own placement inside the cell)
        ox = int(round((gx0 - c["cell_origin"][0]) / step)) + 1
        oy = int(round((gy0 - c["cell_origin"][1]) / step)) + 1
        frame = Image.new("RGBA", (max(canvas_w, ox + small.width), max(canvas_h, oy + small.height)), (0, 0, 0, 0))
        frame.alpha_composite(small, (max(0, ox), max(0, oy)))
        out.append(frame)
        frecs.append({"index": i, "sheet_rect": c["rect"], "cleanup": cst, "source_height": c["height"]})
    # common canvas size for all frames
    mw, mh = max(f.width for f in out), max(f.height for f in out)
    out = [f if f.size == (mw, mh) else _pad_to(f, mw, mh) for f in out]
    pal = p["palette"]
    if pal:
        out = [apply_palette(f, pal, 128) for f in out]
    rec["palette"] = pal
    rec["frames"] = frecs
    # size drift: a frame far smaller / larger than the sheet median is usually a different scale or a cropped pose
    for i, h in enumerate(heights):
        if h < med * 0.6 or h > med * 1.6:
            issues.append({"code": "size_drift", "severity": "error", "cell": i,
                           "msg": f"frame {i + 1} height {int(h)} px vs median {int(med)} px"})
    errors = [x for x in issues if x["severity"] == "error"]
    rec["qa"] = {"status": "retry" if errors else "pass", "issues": issues}
    return out, rec


def _pad_to(f: Image.Image, w: int, h: int) -> Image.Image:
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c.alpha_composite(f, (0, 0))
    return c


class SheetRejected(StudioError):
    """The sheet cannot be cut into the expected frames (caller may regenerate)."""

    def __init__(self, msg: str, record: dict):
        super().__init__(msg, code="sheet_rejected")
        self.record = record
