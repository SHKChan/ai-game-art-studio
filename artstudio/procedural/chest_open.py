"""8-frame treasure-chest opening: rattle (anticipation), crack of light, swing open with overshoot,
settle, sparkles. Built from the same 3D chest model as `chest`."""
from __future__ import annotations

import math

from .chest import PALETTE, paint_frames
from .raster import DocBuilder

DESCRIPTION = "8-frame treasure chest opening animation (anticipation, light leak, overshoot, settle, sparkle)."
ASSET_TYPE = "animation"
PARAMS = {"size": {"type": "int", "default": 64}}

FRAMES = [
    {"theta": 0.0, "ms": 220},
    {"theta": math.radians(7), "ms": 80},                       # rattle
    {"theta": 0.0, "ms": 90},                                    # settle (anticipation)
    {"theta": math.radians(28), "glow": 0.45, "ms": 80},         # crack open, light leaks
    {"theta": math.radians(70), "glow": 1.0, "ms": 70},          # swing
    {"theta": math.radians(104), "glow": 0.85, "sparkle": 0, "ms": 90},   # overshoot
    {"theta": math.radians(92), "glow": 0.5, "sparkle": 2, "ms": 110},    # settle back
    {"theta": math.radians(95), "glow": 0.25, "sparkle": 4, "ms": 240},   # rest with glints
]


def build(size: int = 64, **_):
    d = DocBuilder("treasure-chest-open", size, size)
    d.palette(PALETTE)
    paint_frames(d, FRAMES, size)
    d.tag("open", 0, len(FRAMES) - 1)
    return d.calls
