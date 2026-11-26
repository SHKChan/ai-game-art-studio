"""UI gauges (数值条): HP / MP / EXP / stamina / ATB bars in four themes. Layers: frame, fill, gloss — export the
whole bar, or use `part` = frame / fill to get the pieces a game stretches or crops at run time."""
from __future__ import annotations

from . import _ui
from ._ui import THEMES, blank, frame, mix
from ._icon import OUTLINE
from .raster import bayer4

DESCRIPTION = "JRPG gauge: HP, MP, EXP, stamina or ATB bar in 4 themes; `fill` 0–1; part = bar / frame / fill."
ASSET_TYPE = "ui"
GROUP = "UI"
FULL_BLEED = True
FILLS = {  # dark, mid, light, gloss
    "hp": ["#7a0e1a", "#d02a34", "#ff6a5a", "#ffd0c0"],
    "mp": ["#0e2a7a", "#2a64d8", "#5aaaff", "#d0f0ff"],
    "exp": ["#7a4a06", "#d89a14", "#ffd44a", "#fff6c0"],
    "stamina": ["#145a1a", "#2ea83a", "#7ae05a", "#e0ffc8"],
    "atb": ["#5a2a7a", "#a050d8", "#e090ff", "#f8e0ff"],
}
PARAMS = {"kind": {"type": "string", "default": "hp", "enum": list(FILLS)},
          "theme": {"type": "string", "default": "classic_blue", "enum": list(THEMES)},
          "width": {"type": "int", "default": 96, "min": 32, "max": 256, "step": 8},
          "height": {"type": "int", "default": 12, "min": 8, "max": 24, "step": 1},
          "fill": {"type": "float", "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05},
          "part": {"type": "string", "default": "bar", "enum": ["bar", "frame", "fill"]}}


def build(kind: str = "hp", theme: str = "classic_blue", width: int = 96, height: int = 12, fill: float = 0.7,
          part: str = "bar", **_):
    if kind not in FILLS:
        raise ValueError(f"kind must be one of {list(FILLS)}")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {list(THEMES)}")
    w, h = int(width), int(height)
    fill = max(0.0, min(1.0, float(fill)))
    bw = 1 if h < 12 else 2
    fr = frame(theme, w, h, bw=bw, radius=2, ornaments=False, fill=False)
    trough = mix(THEMES[theme]["fill"][2], "#000000", 0.55)
    ins = bw + 2
    fl, gl = blank(w, h), blank(w, h)
    D, M, L, G = FILLS[kind]
    ih = h - 2 * ins
    for y in range(ins, h - ins):
        for x in range(ins, w - ins):
            fr[y][x] = trough if y > ins or x == ins else mix(trough, "#000000", 0.4)
    fw = int(round((w - 2 * ins) * fill))
    for y in range(ins, h - ins):
        v = (y - ins) / max(1, ih - 1)
        for x in range(ins, ins + fw):
            c = L if v < 0.3 else (M if v < 0.75 else D)
            if 0.25 <= v < 0.35 and bayer4(x, y) < 0.5:
                c = M
            if x == ins + fw - 1 and fw < w - 2 * ins:
                c = G                                               # bright leading edge
            fl[y][x] = c
        if ih >= 4:
            pass
    for x in range(ins + 1, ins + fw - 1):                          # gloss line
        if (x // 3) % 4 != 3:
            gl[ins][x] = mix(G, L, 0.3) if ih > 3 else None
    if kind == "exp" or kind == "atb":                              # segment ticks
        for k in range(1, 10):
            x = ins + (w - 2 * ins) * k // 10
            for y in range(ins, h - ins):
                if fl[y][x] is not None:
                    fl[y][x] = D
    layers = {"bar": [("frame", [fr]), ("fill", [fl]), ("gloss", [gl])],
              "frame": [("frame", [fr]), ("gloss", [blank(w, h)])],
              "fill": [("fill", [fl]), ("gloss", [gl])]}[part]
    return _ui.emit(f"ui-bar-{kind}-{theme}", w, h, layers)
