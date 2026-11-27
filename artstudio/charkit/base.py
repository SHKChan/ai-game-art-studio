"""Craftpix "Free Base 4-Direction Character" packs (male / female) as the body base for the character kit.

The art is NOT part of this repository (Craftpix free licence: use in games is fine, redistribution is not).
Unzip the two packs into a local, git-ignored folder and point the kit at it:

    assets_local/craftpix-base/male/{PNG,ASEPRITE}/…      (default location, relative to the app root)
    assets_local/craftpix-base/female/{PNG,ASEPRITE}/…

or set ARTSTUDIO_CHARKIT_DIR to a folder with the same male/ and female/ sub-folders.
`python -m scripts.setup_character_base <male.zip> <female.zip>` does the unzip for you.

Sheets: 64×64 cells, rows = DIRS, one PNG per layer (<Action><n>_<layer>.png: shadow, sword_back, body,
sword_front, head, swing, red). Per-frame durations come from the matching .aseprite files."""
from __future__ import annotations

import os
import re
import struct
from functools import lru_cache
from pathlib import Path

from PIL import Image

from ..util import StudioError

CELL = 64
DIRS = ["front", "side_left", "side_right", "back"]     # sheet rows
SEXES = ["male", "female"]
FEET = (32, 44)                                          # ground point (pivot) inside the 64×64 cell
# canonical action names (the two packs spell some differently: Sword_attack / Sword_Attack …)
ACTIONS = ["Unarmed_Idle", "Unarmed_Walk", "Unarmed_Run", "Unarmed_Hurt", "Unarmed_Death",
           "Sword_Idle", "Sword_Walk", "Sword_Run", "Sword_Attack", "Sword_Walk_Attack", "Sword_Run_Attack",
           "Sword_Hurt", "Sword_Death"]
LOOPING = {"Unarmed_Idle", "Unarmed_Walk", "Unarmed_Run", "Sword_Idle", "Sword_Walk", "Sword_Run",
           "Sword_Walk_Attack", "Sword_Run_Attack"}


class BasePackMissing(StudioError):
    def __init__(self, msg):
        super().__init__(msg, code="charkit_base_missing")


def base_dir() -> Path:
    env = os.environ.get("ARTSTUDIO_CHARKIT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "assets_local" / "craftpix-base"


def pack_root(sex: str) -> Path:
    if sex not in SEXES:
        raise ValueError(f"base must be one of {SEXES}")
    root = base_dir() / sex
    if not (root / "PNG").is_dir():
        raise BasePackMissing(
            f"Craftpix base pack ({sex}) not found at {root}. Unzip 'Free Base 4-Direction {sex.title()} Character' "
            f"there (PNG/ and ASEPRITE/ folders) or set ARTSTUDIO_CHARKIT_DIR. It is not shipped with the studio "
            f"because its licence does not allow redistribution.")
    return root


def available() -> bool:
    try:
        return all((pack_root(s) / "PNG").is_dir() for s in SEXES)
    except BasePackMissing:
        return False


def _find(parent: Path, name: str) -> Path | None:
    if not parent.is_dir():
        return None
    for p in parent.iterdir():
        if p.name.lower() == name.lower():
            return p
    return None


def action_dir(sex: str, act: str) -> Path:
    return _action_dir(pack_root(sex), act)


def _action_dir(root: Path, act: str) -> Path:
    d = _find(root / "PNG", act)
    if d is None:
        raise ValueError(f"Unknown action {act}. Available: {ACTIONS}")
    return d


def ase_durations(path: Path) -> list[int]:
    """Frame durations (ms) straight from an .aseprite file: 128-byte header, then one header per frame."""
    b = Path(path).read_bytes()
    n = struct.unpack("<H", b[6:8])[0]
    off, out = 128, []
    for _ in range(n):
        size, _magic, _old, dur = struct.unpack("<IHHH", b[off:off + 10])
        out.append(dur)
        off += size
    return out


_LAYER = re.compile(r"^.*?\d+_(.+)\.png$", re.IGNORECASE)


def _sheets(sex: str, act: str) -> dict:
    return _load_sheets(pack_root(sex), act)       # the pack location is part of the cache key


@lru_cache(maxsize=64)
def _load_sheets(root: Path, act: str) -> dict:
    out = {}
    for f in sorted(_action_dir(root, act).glob("*.png")):
        if f.name.lower().endswith("_full.png"):
            continue
        m = _LAYER.match(f.name)
        if m:
            out[m.group(1).lower()] = Image.open(f).convert("RGBA")
    return out


def layer_sheets(sex: str, act: str) -> dict:
    """{layer name: full sheet} — copies, so callers may modify them."""
    return {k: v.copy() for k, v in _sheets(sex, act).items()}


def frame_count(sex: str, act: str, dirn: str) -> int:
    L = _sheets(sex, act)
    r = DIRS.index(dirn)
    n = 0
    for c in range(L["body"].width // CELL):
        box = (c * CELL, r * CELL, c * CELL + CELL, r * CELL + CELL)
        if L["body"].crop(box).getbbox() is None and L["head"].crop(box).getbbox() is None:
            break
        n += 1
    return n


def durations(sex: str, act: str, dirn: str) -> tuple:
    return _durations(pack_root(sex), sex, act, dirn)


@lru_cache(maxsize=256)
def _durations(root: Path, sex: str, act: str, dirn: str) -> tuple:
    n = frame_count(sex, act, dirn)
    ase = _find(root / "ASEPRITE", act)
    d = []
    if ase is not None:
        f = next((p for p in ase.glob("*.aseprite") if p.stem.lower().endswith(dirn)), None)
        if f is not None:
            d = ase_durations(f)
    d = (list(d) + [100] * n)[:n]
    return tuple(int(x) or 100 for x in d)
