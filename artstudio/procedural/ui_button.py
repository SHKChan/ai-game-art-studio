"""UI buttons (按钮): rectangular, square (icon) or round, in four themes. One document with four frames tagged
normal / hover / pressed / disabled, so the same asset drives every state. Rect buttons are 9-slice ready."""
from __future__ import annotations

import math

from . import _ui
from ._ui import THEMES, blank, frame, greyed, mix
from ._icon import OUTLINE
from .raster import bayer4

DESCRIPTION = "JRPG UI button in 4 themes (rect, square or round); frames = normal / hover / pressed / disabled."
ASSET_TYPE = "ui"
GROUP = "UI"
FULL_BLEED = True
SHAPES = ["rect", "square", "round"]
PARAMS = {"shape": {"type": "string", "default": "rect", "enum": SHAPES},
          "theme": {"type": "string", "default": "classic_blue", "enum": list(THEMES)},
          "width": {"type": "int", "default": 96, "min": 24, "max": 256, "step": 8},
          "height": {"type": "int", "default": 32, "min": 16, "max": 96, "step": 4}}


def _round(theme, d, state):
    T = THEMES[theme]
    bd, bm, bl, bh = T["border"]
    if state == "hover":
        bd, bm, bl, bh = mix(bd, T["accent"][1], 0.5), mix(bm, T["accent"][1], 0.6), mix(bl, T["accent"][2], 0.6), "#ffffff"
    g = blank(d, d)
    c = (d - 1) / 2
    R = d / 2 - 0.2
    bw = max(2, d // 12)
    for y in range(d):
        for x in range(d):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            if r > R:
                continue
            up = -(dx + dy) / (r * 1.414 + 1e-6)
            if r > R - 1:
                g[y][x] = OUTLINE
            elif r > R - 1 - bw:
                g[y][x] = (bh if up > 0.5 else bl) if up > 0 else (bd if up < -0.5 else bm)
            elif r > R - 2 - bw:
                g[y][x] = OUTLINE if up > -0.2 else bd
            else:
                q = r / (R - 2 - bw)
                lit = up * q
                tone = {"normal": 0, "hover": 0.6, "pressed": -0.7, "disabled": 0}[state]
                if state == "pressed":
                    lit = -lit
                base = _ui.fill_px(theme, x, int(y * 0.9 + (1 - lit) * 2), d, d, tone)
                g[y][x] = mix(base, "#ffffff", 0.22) if lit > 0.55 and bayer4(x, y) < 0.7 else base
    return g


def build(shape: str = "rect", theme: str = "classic_blue", width: int = 96, height: int = 32, **_):
    if shape not in SHAPES:
        raise ValueError(f"shape must be one of {SHAPES}")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {list(THEMES)}")
    w, h = int(width), int(height)
    if shape != "rect":
        w = h = max(16, h if shape == "square" else max(h, 24))
    frames = []
    for state in ("normal", "hover", "pressed", "disabled"):
        if shape == "round":
            g = _round(theme, w, state)
        else:
            bw = 2 if h < 40 else 3
            g = blank(w, h)
            if state == "pressed":                               # sunk 1 px, darker, inner shadow on top
                f = frame(theme, w, h - 1, bw=bw, tone=-0.6, ornaments=False, inset=True)
                _ui.overlay(g, f, 0, 1)
            else:
                f = frame(theme, w, h - 2, bw=bw, tone=0.5 if state == "hover" else 0.15, ornaments=shape == "rect" and h >= 28,
                          highlight=state == "hover")
                _ui.overlay(g, f, 0, 0)
                sh = mix(THEMES[theme]["border"][0], "#000000", 0.5)    # drop edge (button thickness)
                for x in range(2, w - 2):
                    g[h - 2][x] = sh
                    g[h - 1][x] = OUTLINE
                g[h - 2][1] = g[h - 2][w - 2] = OUTLINE
            if state == "hover":                                  # sheen line across the top
                for x in range(bw + 3, w - bw - 3):
                    if (x // 2) % 3 != 2:
                        g[bw + 2][x] = mix(g[bw + 2][x], "#ffffff", 0.45)
        frames.append(greyed(g) if state == "disabled" else g)
    return _ui.emit(f"ui-button-{shape}-{theme}", w, h, [("button", frames)], durations=[200] * 4,
                    tags=[("normal", 0, 0), ("hover", 1, 1), ("pressed", 2, 2), ("disabled", 3, 3)])
