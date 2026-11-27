"""Character kit: paper-doll costumes on the Craftpix 4-direction base (see base.py for where the art lives).

    from artstudio.charkit import render
    frames, durs = render("knight", "Sword_Attack", dirs=["side_right"])
    frames["side_right"][0]        # {"shadow", "back", "body", "gear", "front"} → 64×64 RGBA images
"""
from __future__ import annotations

from .base import (
    ACTIONS,
    DIRS,
    FEET,
    LOOPING,
    SEXES,
    BasePackMissing,
    available,
    base_dir,
    durations,
)
from .presets import DESCRIPTIONS, PRESETS

BOW = "Bow_Attack"
ALL_ACTIONS = ACTIONS + [BOW]


def outfit_for(preset: str, sex: str | None = None):
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {list(PRESETS)}")
    default_sex, outfit = PRESETS[preset]
    return (sex if sex in SEXES else default_sex), outfit


def render(preset: str, action: str, sex: str | None = None, dirs=None):
    """→ ({direction: [ {group: RGBA image} per frame ]}, {direction: [ms per frame]})."""
    from . import bow, costume
    sex, outfit = outfit_for(preset, sex)
    dirs = list(dirs) if dirs else list(DIRS)
    if action == BOW:
        frames, ms = bow.shoot(sex, outfit, dirs)
        return frames, {d: list(ms) for d in frames}
    canon = next((a for a in ACTIONS if a.lower() == action.lower()), None)
    if canon is None:
        raise ValueError(f"action must be one of {ALL_ACTIONS}")
    frames = costume.compose(sex, canon, outfit, dirs)
    return frames, {d: list(durations(sex, canon, d)) for d in frames}


def is_loop(action: str) -> bool:
    return action in LOOPING


__all__ = [
    "ACTIONS",
    "ALL_ACTIONS",
    "BOW",
    "DESCRIPTIONS",
    "DIRS",
    "FEET",
    "PRESETS",
    "SEXES",
    "BasePackMissing",
    "available",
    "base_dir",
    "is_loop",
    "outfit_for",
    "render",
]
