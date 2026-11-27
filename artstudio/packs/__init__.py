"""Local asset packs: third-party art the owner installed under ``assets_local/packs/`` (git-ignored).

Each pack module describes its files as *items* (one animation, tileset or scene each) with English search tags,
and loads an item as frames that keep the pack's own cell layout (canvas, pivot, timing, soft alpha). The studio
turns items into normal assets with ``Studio.import_pack``; nothing is generated or redrawn.

Install packs with ``python scripts/setup_asset_packs.py <zip> …`` (or set ``ARTSTUDIO_PACKS_DIR``)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from ..tagging import normalize_tags
from ..util import StudioError
from . import dungeon, pvfx, tiny_rpg

PACKS = {m.ID: m for m in (tiny_rpg, dungeon, pvfx)}


def packs_dir() -> Path:
    env = os.environ.get("ARTSTUDIO_PACKS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "assets_local" / "packs"


def pack_root(pack_id: str) -> Path:
    return packs_dir() / PACKS[pack_id].DIRNAME


def get_pack(pack_id: str):
    if pack_id not in PACKS:
        raise StudioError(f"Unknown asset pack {pack_id}. Known: {sorted(PACKS)}")
    return PACKS[pack_id]


def default_options(pack_id: str) -> dict:
    return {k: v["default"] for k, v in get_pack(pack_id).OPTIONS.items()}


def _opts(pack_id: str, options: dict | None) -> dict:
    o = default_options(pack_id)
    for k, v in (options or {}).items():
        spec = get_pack(pack_id).OPTIONS.get(k)
        if spec is None:
            raise StudioError(f"Unknown option {k} for pack {pack_id}")
        if "enum" in spec and v not in spec["enum"]:
            raise StudioError(f"Option {k} must be one of {spec['enum']}")
        o[k] = bool(v) if spec.get("type") == "boolean" else v
    return o


@lru_cache(maxsize=16)
def _items_cached(pack_id: str, root: str, opts_key: tuple, mtime: float) -> tuple:
    m = PACKS[pack_id]
    out = []
    for it in m.items(Path(root), dict(opts_key)):
        it = dict(it)
        it["pack"] = pack_id
        it["tags"] = normalize_tags(it.get("tags", []) + ["pack", pack_id])
        out.append(it)
    return tuple(out)


def list_packs() -> list[dict]:
    out = []
    for pid, m in PACKS.items():
        root = pack_root(pid)
        ok = m.available(root)
        out.append({"id": pid, "title": m.TITLE, "description": m.DESCRIPTION, "available": ok, "path": str(root),
                    "license": m.LICENSE_NOTE, "redistributable": m.REDISTRIBUTABLE, "options": m.OPTIONS,
                    "count": len(items(pid)) if ok else 0})
    return out


def items(pack_id: str, options: dict | None = None, tags=None, query: str | None = None) -> list[dict]:
    """Items of an installed pack, optionally filtered: every tag in `tags` must match; `query` is a substring."""
    m = get_pack(pack_id)
    root = pack_root(pack_id)
    if not m.available(root):
        return []
    o = _opts(pack_id, options)
    lst = list(_items_cached(pack_id, str(root), tuple(sorted(o.items())), root.stat().st_mtime))
    want = normalize_tags(tags or [])
    if want:
        lst = [i for i in lst if all(t in i["tags"] for t in want)]
    if query:
        q = query.lower()
        lst = [i for i in lst if q in (i["name"] + " " + i["id"] + " " + " ".join(i["tags"])).lower()]
    return lst


def find_item(pack_id: str, item_id: str, options: dict | None = None) -> dict:
    for it in items(pack_id, options):
        if it["id"] == item_id:
            return it
    raise StudioError(f"Unknown item {item_id} in pack {pack_id} (is the pack installed?)")


def load(item: dict, options: dict | None = None) -> dict:
    """Frames + placement for one item: {frames: [(RGBA, ms)], canvas, pivot, loop, source_file, ...}."""
    pid = item["pack"]
    m = get_pack(pid)
    root = pack_root(pid)
    if not m.available(root):
        raise StudioError(f"Asset pack {pid} is not installed. Run: python scripts/setup_asset_packs.py <zip>",
                          code="pack_missing")
    return m.load(item, root, _opts(pid, options))


def tag_counts(lst: list[dict]) -> list[tuple[str, int]]:
    from collections import Counter
    c = Counter(t for i in lst for t in i["tags"])
    return c.most_common()
