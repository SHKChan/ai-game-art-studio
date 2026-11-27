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
from .presets import ATTACK, DESCRIPTIONS, PRESETS

BOW = "Bow_Attack"
CAST = "Cast_Spell"
RISE = "Summon_Rise"
ALL_ACTIONS = ACTIONS + [BOW, CAST, RISE]


def outfit_for(preset: str, sex: str | None = None):
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {list(PRESETS)}")
    default_sex, outfit = PRESETS[preset]
    return (sex if sex in SEXES else default_sex), outfit


def render(preset: str, action: str, sex: str | None = None, dirs=None):
    """→ ({direction: [ {group: RGBA image} per frame ]}, {direction: [ms per frame]})."""
    from . import bow, cast, costume
    sex, outfit = outfit_for(preset, sex)
    dirs = list(dirs) if dirs else list(DIRS)
    if action.lower() == "sword_attack" and ATTACK.get(preset) == CAST:
        action = CAST                       # casters attack with a spell, not a staff swing
    if action == RISE:
        from . import cast as _cast, skeleton
        idle, _ = render(preset, "Sword_Idle" if (outfit or {}).get("weapon") != "none" else "Unarmed_Idle", sex, dirs)
        frames, ms = {}, None
        for d, seq in idle.items():
            frames[d], ms = skeleton.rise(seq, _cast.magic_colour(outfit) if outfit and outfit.get("magic") else "necro")
        return frames, {d: list(ms) for d in frames}
    if action == CAST:
        frames, ms = cast.cast(sex, outfit, dirs)
        return frames, {d: list(ms) for d in frames}
    if action == BOW:
        frames, ms = bow.shoot(sex, outfit, dirs)
        return frames, {d: list(ms) for d in frames}
    canon = next((a for a in ACTIONS if a.lower() == action.lower()), None)
    if canon is None:
        raise ValueError(f"action must be one of {ALL_ACTIONS}")
    frames = costume.compose(sex, canon, outfit, dirs)
    ms = {d: list(durations(sex, canon, d)) for d in frames}
    if (outfit or {}).get("stiff"):
        if canon in STIFF_POSES:
            frames, ms = _repose(frames, STIFF_POSES[canon])
        else:
            frames, ms = stiffen(frames, ms, outfit["stiff"])
    return frames, ms


# Undead attacks: a short, telegraphed chop instead of the base's full wind-up → overhead → follow-through swing.
# (base frame, ms): rest, small raise, long hold (the tell), quick strike, stuck in the strike, slow recover.
STIFF_POSES = {"Sword_Attack": [(0, 200), (1, 380), (6, 120), (6, 280), (7, 300)]}


def _repose(frames, poses):
    out_f, out_ms = {}, {}
    for d, seq in frames.items():
        out_f[d] = [seq[min(i, len(seq) - 1)] for i, _ in poses]
        out_ms[d] = [t for _, t in poses]
    return out_f, out_ms


def stiffen(frames, ms, slow=1.35):
    """Jerky, slow motion (undead): drop every other in-between frame, holding the kept pose for both, and play the
    whole action slower. The first and last frames are always kept, so poses still line up with other actions."""
    out_f, out_ms = {}, {}
    for d, seq in frames.items():
        keep = [i for i in range(len(seq)) if i % 2 == 0 or i == len(seq) - 1]
        f, t = [], []
        for j, i in enumerate(keep):
            nxt = keep[j + 1] if j + 1 < len(keep) else len(seq)
            f.append(seq[i])
            t.append(int(round(sum(ms[d][i:nxt]) * float(slow))))
        out_f[d], out_ms[d] = f, t
    return out_f, out_ms


def is_loop(action: str) -> bool:
    return action in LOOPING


__all__ = [
    "ACTIONS",
    "ALL_ACTIONS",
    "BOW",
    "CAST",
    "RISE",
    "STIFF_POSES",
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
