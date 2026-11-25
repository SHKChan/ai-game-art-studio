"""Shared helpers: safe paths, ids, atomic JSON, image codecs."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

from PIL import Image

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class StudioError(ValueError):
    """User-facing validation or processing error. `code` selects a translated message (artstudio.i18n)."""

    def __init__(self, message: str, code: str | None = None, **params):
        super().__init__(message)
        self.code = code
        self.params = params


def new_id(prefix: str = "") -> str:
    return (prefix + "-" if prefix else "") + uuid.uuid4().hex[:12]


def check_id(value: str, what: str = "id") -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise StudioError(f"Invalid {what}: {value!r}")
    return value


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return (s or "item")[:40]


def safe_join(root: Path, *parts: str) -> Path:
    """Join untrusted relative parts under root; refuse absolute paths and traversal."""
    root = Path(root).resolve()
    for p in parts:
        if not isinstance(p, str) or not p or os.path.isabs(p) or p.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", p):
            raise StudioError(f"Unsafe path component: {p!r}")
    path = root.joinpath(*parts).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise StudioError("Path escapes its root directory") from None
    return path


def write_json(path: Path, data) -> None:
    """Atomic JSON write (temp file + replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now() -> float:
    return round(time.time(), 3)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_data_url(value: str, max_bytes: int = 64 * 1024 * 1024) -> bytes:
    if not isinstance(value, str) or not value:
        raise StudioError("Empty upload")
    raw = base64.b64decode(value.split(",", 1)[-1], validate=True)
    if len(raw) > max_bytes:
        raise StudioError("Upload too large")
    return raw


def open_image_bytes(raw: bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        return im
    except (OSError, Image.DecompressionBombError) as e:
        raise StudioError(f"Unreadable image: {e}") from None


def load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return im.convert("RGBA")


def png_bytes(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()
