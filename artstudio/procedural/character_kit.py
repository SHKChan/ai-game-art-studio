"""Character kit (角色套装): the Craftpix 4-direction base character, plain or dressed as one of five fantasy classes
(knight, mage, ranger, priest, berserker), in any of its 13 actions plus a synthesised bow attack, one facing per
document. Layers: shadow, back (cape, back hair, far-side weapon), body, gear (armour, head, hair, headgear),
front (near-side weapon over the face, swing trail), flash (hurt tint).

Needs the Craftpix base packs on this machine (not shipped: their licence forbids redistribution) — see
artstudio/charkit/base.py or run scripts/setup_character_base.py."""
from __future__ import annotations

from ..charkit import ALL_ACTIONS, FEET, PRESETS, is_loop, render
from ..charkit.costume import GROUPS, flatten
from ._ui import emit

DESCRIPTION = ("4-direction base character (Craftpix pack) — plain or as knight / mage / ranger / priest / berserker; "
               "13 actions + bow attack. Needs the local base pack.")
ASSET_TYPE = "animation"
GROUP = "Characters"
FACINGS = {"front": "front", "left": "side_left", "right": "side_right", "rear": "back"}
PARAMS = {"preset": {"type": "string", "default": "knight", "enum": list(PRESETS)},
          "base": {"type": "string", "default": "auto", "enum": ["auto", "male", "female"]},
          "action": {"type": "string", "default": "Sword_Idle", "enum": ALL_ACTIONS},
          "facing": {"type": "string", "default": "right", "enum": list(FACINGS)}}


def LOOP(action: str = "Sword_Idle", **_):
    return is_loop(action)


def pivot(**_):
    return list(FEET)


def _hex(p):
    if not p[3]:
        return None
    return "#%02x%02x%02x" % p[:3] if p[3] == 255 else "#%02x%02x%02x%02x" % p


def _grid(img):
    if img is None:
        return [[None] * 64 for _ in range(64)]
    px = img.load()
    return [[_hex(px[x, y]) for x in range(img.width)] for y in range(img.height)]


def build(preset: str = "knight", base: str = "auto", action: str = "Sword_Idle", facing: str = "right", **_):
    if facing not in FACINGS:
        raise ValueError(f"facing must be one of {list(FACINGS)}")
    d = FACINGS[facing]
    frames, ms = render(preset, action, None if base == "auto" else base, dirs=[d])
    seq, durs = [], []
    for f, t in zip(frames[d], ms[d]):        # a cape can hide the idle breathing: merge identical frames into holds
        key = flatten(f).tobytes()
        if seq and key == seq[-1][1]:
            durs[-1] += t
        else:
            seq.append((f, key)); durs.append(t)
    seq = [f for f, _ in seq]
    layers = []
    for g in GROUPS:
        grids = [_grid(f.get(g)) for f in seq]
        if any(c for grid in grids for row in grid for c in row):
            layers.append((g, grids))
    name = f"{preset}_{action.lower()}_{facing}"
    return emit(name, 64, 64, layers, durations=durs, tags=[(action.lower(), 0, len(seq) - 1)])
