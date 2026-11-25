"""Layered, animated pixel document + on-disk store (atomic, UTF-8 JSON)."""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

SCHEMA = 1
MAX_SIDE = 4096
MAX_FRAMES = 512
MAX_LAYERS = 64
HEX = re.compile(r"^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")


class EngineError(ValueError):
    pass


def parse_color(c, palette=None) -> tuple[int, int, int, int]:
    """'#rrggbb(aa)' | [r,g,b(,a)] | palette index (int)."""
    if isinstance(c, bool):
        raise EngineError("invalid colour")
    if isinstance(c, int):
        if palette is None or not 0 <= c < len(palette):
            raise EngineError(f"palette index {c} out of range (palette has {len(palette or [])} colours)")
        return tuple(palette[c])
    if isinstance(c, str):
        m = HEX.match(c.strip())
        if not m:
            raise EngineError(f"invalid colour {c!r}")
        v = m.group(1) + (m.group(2) or "ff")
        return tuple(int(v[i:i + 2], 16) for i in range(0, 8, 2))
    if isinstance(c, (list, tuple)) and len(c) in (3, 4) and all(isinstance(x, int) and 0 <= x <= 255 for x in c):
        return tuple(list(c) + [255] * (4 - len(c)))
    raise EngineError(f"invalid colour {c!r}")


class Document:
    def __init__(self, doc_id: str, name: str, w: int, h: int):
        self.id, self.name, self.w, self.h = doc_id, name, w, h
        self.layers = [{"name": "Layer 1", "visible": True, "opacity": 255, "blend": "normal"}]
        self.frames = [{"duration_ms": 100}]
        self.palette: list[tuple[int, int, int, int]] = []
        self.tags: list[dict] = []
        self.revision = 1
        self.cels: dict[tuple[int, int], np.ndarray] = {}

    # ---- cels
    def cel(self, layer: int, frame: int, create: bool = True) -> np.ndarray | None:
        self.check_lf(layer, frame)
        key = (layer, frame)
        if key not in self.cels and create:
            self.cels[key] = np.zeros((self.h, self.w, 4), np.uint8)
        return self.cels.get(key)

    def check_lf(self, layer, frame):
        if not isinstance(layer, int) or not 0 <= layer < len(self.layers):
            raise EngineError(f"layer {layer} out of range (0..{len(self.layers) - 1})")
        if not isinstance(frame, int) or not 0 <= frame < len(self.frames):
            raise EngineError(f"frame {frame} out of range (0..{len(self.frames) - 1})")

    # ---- render
    def render(self, frame: int) -> np.ndarray:
        """Composite visible layers bottom→top (source-over with layer opacity)."""
        out = np.zeros((self.h, self.w, 4), np.float32)
        for li, layer in enumerate(self.layers):
            if not layer["visible"]:
                continue
            c = self.cels.get((li, frame))
            if c is None:
                continue
            src = c.astype(np.float32) / 255.0
            a = src[..., 3:4] * (layer["opacity"] / 255.0)
            da = out[..., 3:4]
            oa = a + da * (1 - a)
            rgb = np.where(oa > 0, (src[..., :3] * a + out[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6), 0)
            out = np.concatenate([rgb, oa], axis=-1)
        return np.clip(np.round(out * 255), 0, 255).astype(np.uint8)

    def render_image(self, frame: int) -> Image.Image:
        return Image.fromarray(self.render(frame), "RGBA")

    # ---- serialisation
    def meta(self) -> dict:
        return {"schema": SCHEMA, "doc_id": self.id, "name": self.name, "w": self.w, "h": self.h, "revision": self.revision,
                "layers": [{"index": i, **l} for i, l in enumerate(self.layers)],
                "frames": [{"index": i, **f} for i, f in enumerate(self.frames)],
                "palette": ["#%02x%02x%02x%02x" % c for c in self.palette], "palette_len": len(self.palette),
                "tags": self.tags, "cels": [f"L{l}_F{f}" for (l, f) in sorted(self.cels)]}


class Store:
    """Directory-backed document store. One lock per store; writes are atomic per document."""

    def __init__(self, home: Path):
        self.home = Path(home)
        self.docs = self.home / "documents"
        self.docs.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def path(self, doc_id: str) -> Path:
        if not isinstance(doc_id, str) or not re.fullmatch(r"[0-9a-f-]{8,36}", doc_id):
            raise EngineError(f"invalid doc_id {doc_id!r}")
        if len(doc_id) < 36:  # unique-prefix lookup, like Atelier's short ids
            hits = [p.name for p in self.docs.glob(doc_id + "*")]
            if len(hits) != 1:
                raise EngineError(f"doc_id prefix {doc_id!r} matches {len(hits)} documents")
            doc_id = hits[0]
        return self.docs / doc_id

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def exists(self, doc_id: str) -> bool:
        try:
            return (self.path(doc_id) / "doc.json").is_file()
        except EngineError:
            return False

    def load(self, doc_id: str) -> Document:
        p = self.path(doc_id)
        f = p / "doc.json"
        if not f.is_file():
            raise EngineError(f"document {doc_id} not found")
        m = json.loads(f.read_text(encoding="utf-8"))
        if m.get("schema") != SCHEMA:
            raise EngineError(f"document schema {m.get('schema')} unsupported")
        d = Document(m["doc_id"], m["name"], m["w"], m["h"])
        d.layers = [{k: v for k, v in l.items() if k != "index"} for l in m["layers"]]
        d.frames = [{k: v for k, v in fr.items() if k != "index"} for fr in m["frames"]]
        d.palette = [parse_color(c) for c in m["palette"]]
        d.tags, d.revision = m["tags"], m["revision"]
        for name in m["cels"]:
            l, fr = (int(x[1:]) for x in name.split("_"))
            with Image.open(p / "cels" / f"{name}.png") as im:
                d.cels[(l, fr)] = np.array(im.convert("RGBA"), np.uint8)
        return d

    def save(self, d: Document) -> None:
        p = self.docs / d.id
        p.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=".cels-", dir=p))
        try:
            for (l, f), arr in d.cels.items():
                if arr.any():
                    Image.fromarray(arr, "RGBA").save(tmp / f"L{l}_F{f}.png")
            meta = d.meta()
            meta["cels"] = sorted(n[:-4] for n in os.listdir(tmp))
            old = p / "cels"
            if old.exists():
                shutil.rmtree(old)
            tmp.rename(old)
            fd, t = tempfile.mkstemp(prefix=".doc-", dir=p)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=1)
            os.replace(t, p / "doc.json")
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)

    def append_recipe(self, doc_id: str, call: dict) -> None:
        with open(self.docs / doc_id / "doc.recipe", "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(call, ensure_ascii=False, sort_keys=True) + "\n")

    def list(self) -> list[dict]:
        out = []
        for f in sorted(self.docs.glob("*/doc.json")):
            m = json.loads(f.read_text(encoding="utf-8"))
            out.append({"doc_id": m["doc_id"], "name": m["name"], "w": m["w"], "h": m["h"], "frames": len(m["frames"]), "layers": len(m["layers"])})
        return out

    def delete(self, doc_id: str) -> None:
        shutil.rmtree(self.path(doc_id))
