"""Tool implementations (Atelier-compatible call format, studio subset) and the Engine facade.

Supported tools: doc_new, doc_info, doc_layer, doc_frame, doc_palette, doc_paint_grid, doc_draw, doc_fx,
doc_region, doc_rescale, doc_add_tag, doc_seam_report, doc_export, doc_look, list_docs, delete_doc.
Unknown tools or arguments raise EngineError (no silent no-ops).
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .document import MAX_FRAMES, MAX_LAYERS, MAX_SIDE, Document, EngineError, Store, parse_color


# ------------------------------------------------------------------ raster primitives (match Atelier semantics)
def _put(a: np.ndarray, x: int, y: int, c) -> None:
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
        a[y, x] = c


def _brush(a, cx, cy, c, size):
    if size <= 1:
        return _put(a, cx, cy, c)
    o = size // 2  # same anchoring as Atelier: square spans [c - size//2, c - size//2 + size - 1]
    y0, x0 = max(0, cy - o), max(0, cx - o)
    a[y0:max(0, cy - o + size), x0:max(0, cx - o + size)] = c


def _line(a, x0, y0, x1, y1, c, size=1):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        _brush(a, x0, y0, c, size)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _poly_fill(a, pts, c):
    if len(pts) < 3:
        return
    h, w = a.shape[:2]
    ys = [p[1] for p in pts]
    for y in range(max(0, int(np.floor(min(ys)))), min(h, int(np.ceil(max(ys))) + 1)):
        cy = y + 0.5
        xs = []
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            if (y0 <= cy < y1) or (y1 <= cy < y0):
                xs.append(x0 + (cy - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for xa, xb in zip(xs[::2], xs[1::2]):
            lo, hi = max(0, int(np.ceil(xa - 0.5))), min(w - 1, int(np.floor(xb - 0.5)))
            if lo <= hi:
                a[y, lo:hi + 1] = c


def _flood(a, x, y, c, tolerance=0):
    h, w = a.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return
    target = a[y, x].astype(int)
    diff = np.abs(a.astype(int) - target).max(-1) <= tolerance
    reach = np.zeros((h, w), bool)
    reach[y, x] = True
    while True:
        g = reach.copy()
        g[1:] |= reach[:-1]; g[:-1] |= reach[1:]; g[:, 1:] |= reach[:, :-1]; g[:, :-1] |= reach[:, 1:]
        g &= diff
        if (g == reach).all():
            break
        reach = g
    a[reach] = c


# ------------------------------------------------------------------ engine
class Engine:
    """In-process engine for one store (home directory). Use `call(tool, args)` or `run(calls)`."""

    def __init__(self, home: Path):
        self.store = Store(home)
        self.home = self.store.home
        self.calls = 0
        self._cache: dict[str, Document] = {}
        # batch mode (run / replay): documents and recipe lines are written once at the end instead of after every
        # call — a builder sends dozens of paint calls and re-saving every cel each time was O(calls × cels)
        self._batch = 0
        self._dirty: dict[str, Document] = {}
        self._recipe: dict[str, list] = {}

    # context-manager compatibility with the former subprocess client
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._cache.clear()

    def _doc(self, args) -> Document:
        did = args.get("doc_id")
        if not did:
            raise EngineError("doc_id is required")
        path = self.store.path(did)
        if path.name not in self._cache:
            self._cache[path.name] = self.store.load(path.name)
        return self._cache[path.name]

    def call(self, tool: str, args: dict) -> dict:
        fn = TOOLS.get(tool)
        if fn is None:
            raise EngineError(f"unknown tool {tool!r}; supported: {', '.join(sorted(TOOLS))}")
        if not isinstance(args, dict):
            raise EngineError("arguments must be an object")
        self.calls += 1
        if tool in DISK_TOOLS:
            self.flush()
        with self.store.lock:
            res = fn(self, copy.deepcopy(args))
            mutated = res.pop("_mutated", None)
            if mutated is not None:
                mutated.revision += 1
                rec = dict(args)
                rec["doc_id"] = mutated.id
                if self._batch:
                    self._dirty[mutated.id] = mutated
                    self._recipe.setdefault(mutated.id, []).append({"name": tool, "arguments": rec})
                else:
                    self.store.save(mutated)
                    self.store.append_recipe(mutated.id, {"name": tool, "arguments": rec})
                res.setdefault("revision", mutated.revision)
            return res

    def flush(self) -> None:
        """Write documents changed in batch mode (and their recipe lines) to disk."""
        with self.store.lock:
            dirty, recipe = self._dirty, self._recipe
            self._dirty, self._recipe = {}, {}
            for did, d in dirty.items():
                self.store.save(d)
            for did, lines in recipe.items():
                self.store.append_recipe_lines(did, lines)

    @contextmanager
    def batch(self):
        self._batch += 1
        try:
            yield self
        finally:
            self._batch -= 1
            if not self._batch:
                self.flush()

    def run(self, calls: list[dict], doc_id: str | None = None, progress=None, cancel=None) -> str | None:
        """Execute calls; "$DOC" is replaced by the doc created by the first doc_new (or doc_id)."""
        with self.batch():
            return self._run(calls, doc_id, progress, cancel)

    def _run(self, calls, doc_id, progress, cancel):
        n = len(calls)
        for i, c in enumerate(calls):
            if cancel:
                cancel()
            if not isinstance(c, dict) or "name" not in c:
                raise EngineError(f"call {i}: expected {{name, arguments}}")
            args = json.loads(json.dumps(c.get("arguments", {})).replace('"$DOC"', json.dumps(doc_id or "")))
            res = self.call(c["name"], args)
            if c["name"] == "doc_new":
                doc_id = res["doc_id"]
            if progress and (i % 10 == 0 or i == n - 1):
                progress((i + 1) / n, f"{c['name']} {i + 1}/{n}")
        return doc_id

    def replay(self, recipe: Path) -> str:
        """Rebuild a document from a recipe file (new doc id; old ids are remapped)."""
        with self.batch():
            return self._replay(recipe)

    def _replay(self, recipe: Path) -> str:
        ids: dict[str, str] = {}
        last = None
        for ln, line in enumerate(Path(recipe).read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            c = json.loads(line)
            args = dict(c.get("arguments", {}))
            if c["name"] == "doc_new":
                old = args.pop("doc_id", None)
                res = self.call("doc_new", args)
                ids[old or res["doc_id"]] = res["doc_id"]
                last = res["doc_id"]
                continue
            if "doc_id" in args:
                args["doc_id"] = ids.get(args["doc_id"], args["doc_id"])
            self.call(c["name"], args)
        if not last:
            raise EngineError("recipe has no doc_new")
        return last

    def doc_dir(self, doc_id: str) -> Path:
        self.flush()
        return self.store.path(doc_id)

    def export_frames(self, doc_id: str, out_dir: Path | None = None, tag: str | None = None):
        d = self._doc({"doc_id": doc_id})
        rng = range(len(d.frames))
        if tag:
            t = next((t for t in d.tags if t["name"] == tag), None)
            if not t:
                raise EngineError(f"unknown tag {tag}")
            rng = range(t["from"], t["to"] + 1)
        frames = [d.render_image(i) for i in rng]
        durs = [int(d.frames[i]["duration_ms"]) for i in rng]
        return frames, durs, {"meta": {"app": "artstudio-engine", "size": {"w": d.w, "h": d.h}, "frameTags": d.tags}}


def _int(args, k, default=None, lo=None, hi=None):
    v = args.get(k, default)
    if v is None:
        raise EngineError(f"{k} is required")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise EngineError(f"{k} must be a number")
    v = int(round(v))
    if lo is not None and v < lo or hi is not None and v > hi:
        raise EngineError(f"{k}={v} out of range")
    return v


def _frames(d: Document, args) -> range:
    f0 = _int(args, "frame", 0)
    f1 = args.get("frame_to")
    f1 = f0 if f1 is None else _int(args, "frame_to")
    if not 0 <= f0 <= f1 < len(d.frames):
        raise EngineError(f"frame range {f0}..{f1} invalid")
    return range(f0, f1 + 1)


def _color(d, args, key="color"):
    if args.get("erase"):
        return (0, 0, 0, 0)
    if key not in args:
        raise EngineError(f"{key} is required")
    return parse_color(args[key], d.palette)


# ------------------------------------------------------------------ tools
def t_doc_new(e: Engine, a):
    w, h = _int(a, "width", lo=1, hi=MAX_SIDE), _int(a, "height", lo=1, hi=MAX_SIDE)
    name = str(a.get("name") or "untitled")[:120]
    d = Document(e.store.new_id(), name, w, h)
    d.revision = 0
    e._cache[d.id] = d
    return {"_mutated": d, **{k: v for k, v in d.meta().items()}}


def t_doc_info(e, a):
    return e._doc(a).meta()


def t_list_docs(e, a):
    return {"docs": e.store.list()}


def t_delete_doc(e, a):
    d = e._doc(a)
    e._cache.pop(d.id, None)
    e.store.delete(d.id)
    return {"deleted": d.id}


def t_doc_layer(e, a):
    d = e._doc(a)
    op = a.get("op")
    n = len(d.layers)
    if op == "add":
        if n >= MAX_LAYERS:
            raise EngineError("too many layers")
        d.layers.append({"name": str(a.get("name") or f"Layer {n + 1}"), "visible": True, "opacity": 255, "blend": "normal"})
        return {"_mutated": d, "layer": n, "layers": n + 1}
    i = _int(a, "index", lo=0, hi=n - 1)
    if op == "rename":
        d.layers[i]["name"] = str(a.get("name") or d.layers[i]["name"])
    elif op == "set":
        if "visible" in a:
            d.layers[i]["visible"] = bool(a["visible"])
        if "opacity" in a:
            d.layers[i]["opacity"] = _int(a, "opacity", lo=0, hi=255)
        if "name" in a:
            d.layers[i]["name"] = str(a["name"])
    elif op == "delete":
        if n == 1:
            raise EngineError("cannot delete the last layer")
        d.layers.pop(i)
        d.cels = {(l - (l > i), f): v for (l, f), v in d.cels.items() if l != i}
    elif op == "duplicate":
        d.layers.insert(i + 1, dict(d.layers[i], name=d.layers[i]["name"] + " copy"))
        d.cels = {(l + (l > i), f): v for (l, f), v in d.cels.items()}
        for (l, f), v in list(d.cels.items()):
            if l == i:
                d.cels[(i + 1, f)] = v.copy()
    elif op == "move":
        to = _int(a, "to_index", lo=0, hi=n - 1)
        order = list(range(n))
        order.insert(to, order.pop(i))
        remap = {old: new for new, old in enumerate(order)}
        d.layers = [d.layers[k] for k in order]
        d.cels = {(remap[l], f): v for (l, f), v in d.cels.items()}
    else:
        raise EngineError("doc_layer op must be add|rename|set|delete|duplicate|move")
    return {"_mutated": d, "layers": len(d.layers)}


def t_doc_frame(e, a):
    d = e._doc(a)
    op = a.get("op")
    n = len(d.frames)
    dur = _int(a, "duration_ms", 100, lo=1, hi=60000)
    if op == "add":
        count = _int(a, "count", 1, lo=1, hi=256)
        if n + count > MAX_FRAMES:
            raise EngineError("too many frames")
        src = a.get("copy_from")
        if src is not None:
            src = _int(a, "copy_from", lo=0, hi=n - 1)
        for k in range(count):
            d.frames.append({"duration_ms": dur})
            if src is not None:
                for (l, f), v in list(d.cels.items()):
                    if f == src:
                        d.cels[(l, n + k)] = v.copy()
        return {"_mutated": d, "added_frame": n, "frames": len(d.frames)}
    if op == "duration":
        f0 = _int(a, "frame", lo=0, hi=n - 1)
        for f in range(f0, min(n, f0 + _int(a, "count", 1, lo=1))):
            d.frames[f]["duration_ms"] = dur
        return {"_mutated": d}
    i = _int(a, "frame", lo=0, hi=n - 1)
    if op == "delete":
        if n == 1:
            raise EngineError("cannot delete the last frame")
        d.frames.pop(i)
        d.cels = {(l, f - (f > i)): v for (l, f), v in d.cels.items() if f != i}
        d.tags = [t for t in d.tags if t["to"] < len(d.frames)]
    elif op in ("duplicate", "insert"):
        d.frames.insert(i + 1 if op == "duplicate" else i, dict(d.frames[i]) if op == "duplicate" else {"duration_ms": dur})
        pos = i + 1 if op == "duplicate" else i
        d.cels = {(l, f + (f >= pos)): v for (l, f), v in d.cels.items()}
        if op == "duplicate":
            for (l, f), v in list(d.cels.items()):
                if f == i:
                    d.cels[(l, i + 1)] = v.copy()
    elif op == "move":
        to = _int(a, "to_index", lo=0, hi=n - 1)
        order = list(range(n))
        order.insert(to, order.pop(i))
        remap = {old: new for new, old in enumerate(order)}
        d.frames = [d.frames[k] for k in order]
        d.cels = {(l, remap[f]): v for (l, f), v in d.cels.items()}
    else:
        raise EngineError("doc_frame op must be add|duration|delete|insert|duplicate|move")
    return {"_mutated": d, "frames": len(d.frames)}


def t_doc_palette(e, a):
    d = e._doc(a)
    op = a.get("op", "report")
    if op == "set":
        cols = a.get("colors")
        if not isinstance(cols, list) or not 1 <= len(cols) <= 256:
            raise EngineError("colors must be a list of 1..256 colours")
        d.palette = [parse_color(c) for c in cols]
        return {"_mutated": d, "palette_len": len(d.palette)}
    if op == "report":
        used = set()
        for f in range(len(d.frames)):
            px = d.render(f).reshape(-1, 4)
            used.update(map(tuple, px[px[:, 3] > 0].tolist()))
        pal = set(d.palette)
        return {"palette_len": len(d.palette), "colours_used": len(used),
                "off_palette": sorted("#%02x%02x%02x%02x" % c for c in used - pal)[:64] if pal else []}
    raise EngineError("doc_palette op must be set|report")


def t_doc_paint_grid(e, a):
    d = e._doc(a)
    layer = _int(a, "layer", lo=0)
    legend = a.get("legend")
    rows = a.get("rows")
    if not isinstance(legend, dict) or not isinstance(rows, list) or not all(isinstance(r, str) for r in rows):
        raise EngineError("legend (object) and rows (list of strings) are required")
    lut = {}
    for k, v in legend.items():
        if len(k) != 1 or k in ". ":
            raise EngineError(f"legend key {k!r} must be one character other than '.' and ' '")
        lut[k] = np.array(parse_color(v, d.palette), np.uint8)
    for ry, row in enumerate(rows):
        for rx, ch in enumerate(row):
            if ch not in ". " and ch not in lut:
                raise EngineError(f"row {ry} col {rx}: character {ch!r} is not in the legend")
    ox, oy = _int(a, "x", 0), _int(a, "y", 0)
    width = max((len(r) for r in rows), default=0)
    painted = 0
    for f in _frames(d, a):
        cel = d.cel(layer, f)
        if a.get("replace"):
            cel[max(0, oy):max(0, oy + len(rows)), max(0, ox):max(0, ox + width)] = 0
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch in ". ":
                    continue
                x, y = ox + rx, oy + ry
                if 0 <= x < d.w and 0 <= y < d.h:
                    cel[y, x] = lut[ch]
                    painted += 1
    return {"_mutated": d, "pixels_painted": painted}


def _pts(a, key="points"):
    p = a.get(key)
    if not isinstance(p, list) or not p or not all(isinstance(q, (list, tuple)) and len(q) >= 2 for q in p):
        raise EngineError(f"{key} must be a list of [x, y]")
    return [(float(q[0]), float(q[1])) for q in p]


def t_doc_draw(e, a):
    d = e._doc(a)
    op = a.get("op")
    layer = _int(a, "layer", 0, lo=0)
    size = _int(a, "size", _int(a, "width", 1), lo=1, hi=64) if ("size" in a or "width" in a) else 1
    for f in _frames(d, a):
        cel = d.cel(layer, f)
        if op == "clear_cel":
            cel[:] = 0
            continue
        c = np.array(_color(d, a), np.uint8)
        if op == "fill_cel":
            cel[:] = c
        elif op == "pencil":
            for x, y in _pts(a):
                _brush(cel, int(round(x)), int(round(y)), c, size)
        elif op == "line":
            _line(cel, _int(a, "x0"), _int(a, "y0"), _int(a, "x1"), _int(a, "y1"), c, size)
        elif op in ("polyline", "polygon", "stroke"):
            pts = [(int(round(x)), int(round(y))) for x, y in _pts(a)]
            if op == "polygon" and a.get("fill", True):
                _poly_fill(cel, [(x, y) for x, y in _pts(a)], c)
            for p, q in zip(pts, pts[1:] + ([pts[0]] if (op == "polygon" or a.get("closed")) else [])):
                _line(cel, p[0], p[1], q[0], q[1], c, size)
        elif op == "rect":
            x0, y0, x1, y1 = (_int(a, k) for k in ("x0", "y0", "x1", "y1"))
            ax, bx, ay, by = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
            if a.get("fill", False):
                cel[max(0, ay):min(d.h, by + 1), max(0, ax):min(d.w, bx + 1)] = c
            else:
                for p, q in (((ax, ay), (bx, ay)), ((ax, by), (bx, by)), ((ax, ay), (ax, by)), ((bx, ay), (bx, by))):
                    _line(cel, p[0], p[1], q[0], q[1], c, size)
        elif op == "ellipse":
            cx, cy = _int(a, "cx"), _int(a, "cy")
            rx, ry = max(1, _int(a, "rx")), max(1, _int(a, "ry"))
            A, B = rx + 0.5, ry + 0.5
            yy, xx = np.mgrid[-ry:ry + 1, -rx:rx + 1]

            def inside(x, y):
                return (x / A) ** 2 + (y / B) ** 2 <= 1.0
            m = inside(xx, yy)
            if not a.get("fill", False):
                m &= ~(inside(xx - 1, yy) & inside(xx + 1, yy) & inside(xx, yy - 1) & inside(xx, yy + 1))
            for y, x in zip(*np.nonzero(m)):
                _put(cel, cx + x - rx, cy + y - ry, c)
        elif op == "fill":
            _flood(cel, _int(a, "x"), _int(a, "y"), c, _int(a, "tolerance", 0, lo=0, hi=255))
        else:
            raise EngineError("doc_draw op must be pencil|line|rect|ellipse|polyline|polygon|stroke|fill|fill_cel|clear_cel")
    return {"_mutated": d, "op": op}


def t_doc_fx(e, a):
    d = e._doc(a)
    op = a.get("op")
    layer = _int(a, "layer", 0, lo=0)
    for f in _frames(d, a):
        cel = d.cel(layer, f)
        if op == "outline":
            c = np.array(_color(d, a), np.uint8)
            on = cel[..., 3] > 0
            g = np.zeros_like(on)
            g[1:] |= on[:-1]; g[:-1] |= on[1:]; g[:, 1:] |= on[:, :-1]; g[:, :-1] |= on[:, 1:]
            cel[g & ~on] = c
        elif op == "flip":
            cel[:] = cel[:, ::-1] if a.get("horizontal", True) else cel[::-1]
        elif op == "shift":
            dx, dy = _int(a, "dx", 0), _int(a, "dy", 0)
            src = cel.copy()
            cel[:] = 0
            H, W = cel.shape[:2]
            ys, xs = slice(max(0, dy), min(H, H + dy)), slice(max(0, dx), min(W, W + dx))
            yo, xo = slice(max(0, -dy), min(H, H - dy)), slice(max(0, -dx), min(W, W - dx))
            cel[ys, xs] = src[yo, xo]
        elif op == "replace_color":
            frm, to = np.array(parse_color(a["from"], d.palette)), np.array(parse_color(a["to"], d.palette))
            cel[(cel == frm).all(-1)] = to
        else:
            raise EngineError("doc_fx op must be outline|flip|shift|replace_color")
    return {"_mutated": d, "op": op}


def t_doc_region(e, a):
    d = e._doc(a)
    r = a.get("rect")
    if not (isinstance(r, list) and len(r) == 4):
        raise EngineError("rect must be [x0, y0, x1, y1] (inclusive corners, as in Atelier)")
    x0, y0, x1, y1 = (int(v) for v in r)
    x, y = min(x0, x1), min(y0, y1)
    w, h = abs(x1 - x0) + 1, abs(y1 - y0) + 1
    layer = _int(a, "layer", 0, lo=0)
    for f in _frames(d, a):
        cel = d.cel(layer, f)
        part = cel[max(0, y):max(0, y + h), max(0, x):max(0, x + w)].copy()
        cel[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = 0
        if a.get("op") == "move":
            off = a.get("offset") or [0, 0]
            nx, ny = max(0, x) + int(off[0]), max(0, y) + int(off[1])
            for yy in range(part.shape[0]):
                for xx in range(part.shape[1]):
                    if part[yy, xx, 3]:
                        _put(cel, nx + xx, ny + yy, part[yy, xx])
        elif a.get("op") != "clear":
            raise EngineError("doc_region op must be clear|move")
    return {"_mutated": d}


def t_doc_rescale(e, a):
    d = e._doc(a)
    k = _int(a, "factor", lo=2, hi=16)
    if d.w * k > MAX_SIDE or d.h * k > MAX_SIDE:
        raise EngineError("result too large")
    d.w, d.h = d.w * k, d.h * k
    d.cels = {key: np.repeat(np.repeat(v, k, 0), k, 1) for key, v in d.cels.items()}
    return {"_mutated": d, "w": d.w, "h": d.h}


def t_doc_add_tag(e, a):
    d = e._doc(a)
    f0, f1 = _int(a, "from", lo=0), _int(a, "to", lo=0)
    if not f0 <= f1 < len(d.frames):
        raise EngineError("tag range invalid")
    d.tags = [t for t in d.tags if t["name"] != a.get("name")] + [{"name": str(a.get("name")), "from": f0, "to": f1,
                                                                    "direction": a.get("direction", "forward")}]
    return {"_mutated": d, "tags": d.tags}


def t_doc_look(e, a):
    d = e._doc(a)
    f = _int(a, "frame", 0, lo=0, hi=len(d.frames) - 1)
    im = d.render_image(f)
    if a.get("tile"):
        t3 = Image.new("RGBA", (d.w * 3, d.h * 3))
        for ty in range(3):
            for tx in range(3):
                t3.paste(im, (tx * d.w, ty * d.h))
        im = t3
    s = _int(a, "scale", 1, lo=1, hi=32)
    if s > 1:
        im = im.resize((im.width * s, im.height * s), Image.Resampling.NEAREST)
    out = a.get("out_path")
    if out:
        im.save(out)
    bb = im.getbbox()
    return {"frame": f, "out_path": out, "bbox": list(bb) if bb else None, "w": d.w, "h": d.h}


def t_doc_seam_report(e, a):
    """Tiling check: compares opposite edges (left/right columns, top/bottom rows) of a rendered frame."""
    d = e._doc(a)
    f = _int(a, "frame", 0, lo=0, hi=len(d.frames) - 1)
    im = d.render(f).astype(int)
    h_mis = int((np.abs(im[:, 0] - im[:, -1]).max(-1) > _int(a, "tolerance", 0, lo=0)).sum())
    v_mis = int((np.abs(im[0] - im[-1]).max(-1) > _int(a, "tolerance", 0, lo=0)).sum())
    return {"frame": f, "horizontal_mismatch": h_mis, "vertical_mismatch": v_mis, "rows": d.h, "cols": d.w,
            "note": "0 = edges match exactly; also inspect doc_look tile=true for visible repetition"}


def t_doc_export(e, a):
    d = e._doc(a)
    out = Path(a.get("out_path") or "")
    if not a.get("out_path"):
        raise EngineError("out_path is required")
    s = _int(a, "scale", 1, lo=1, hi=32)
    frames = [d.render_image(i) for i in range(len(d.frames))]
    if s > 1:
        frames = [f.resize((d.w * s, d.h * s), Image.Resampling.NEAREST) for f in frames]
    durs = [int(fr["duration_ms"]) for fr in d.frames]
    if a.get("op") == "sheet":
        sheet = Image.new("RGBA", (d.w * s * len(frames), d.h * s), (0, 0, 0, 0))
        meta = {"frames": {}, "meta": {"app": "artstudio-engine", "image": out.name, "size": {"w": sheet.width, "h": sheet.height},
                                       "scale": "1", "frameTags": d.tags}}
        for i, f in enumerate(frames):
            sheet.paste(f, (i * d.w * s, 0))
            meta["frames"][f"{d.name} {i}"] = {"frame": {"x": i * d.w * s, "y": 0, "w": d.w * s, "h": d.h * s}, "duration": durs[i],
                                               "rotated": False, "trimmed": False, "sourceSize": {"w": d.w * s, "h": d.h * s},
                                               "spriteSourceSize": {"x": 0, "y": 0, "w": d.w * s, "h": d.h * s}}
        sheet.save(out)
        out.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return {"path": str(out), "meta_path": str(out.with_suffix(".json")), "count": len(frames)}
    if a.get("op") == "anim":
        from ..export import write_apng, write_gif
        (write_apng if a.get("format") == "apng" else write_gif)(frames, durs, out, loop=True, scale=1)
        return {"path": str(out), "count": len(frames)}
    raise EngineError("doc_export op must be sheet|anim")


DISK_TOOLS = {"list_docs", "delete_doc"}   # read or change the store on disk: flush batched changes first
TOOLS = {n[2:]: f for n, f in globals().items() if n.startswith("t_") and callable(f)}
