"""UI panels (界面面板): window, dialog (name plate + bobbing next-arrow), tooltip (with tail), title banner and tab
(active / inactive). Four themes. Built for 9-slice scaling: keep `slice_margin` px corners fixed, stretch the rest."""
from __future__ import annotations

from . import _ui
from ._ui import THEMES, blank, frame, mix, overlay
from ._icon import OUTLINE

DESCRIPTION = "JRPG UI panel: window, dialog, tooltip, title banner or tab in 4 themes (classic blue, wood & gold, stone & iron, parchment); 9-slice ready."
ASSET_TYPE = "ui"
GROUP = "UI"
FULL_BLEED = True
KINDS = ["window", "dialog", "tooltip", "title", "tab"]
PARAMS = {"kind": {"type": "string", "default": "window", "enum": KINDS},
          "theme": {"type": "string", "default": "classic_blue", "enum": list(THEMES)},
          "width": {"type": "int", "default": 128, "min": 32, "max": 320, "step": 8},
          "height": {"type": "int", "default": 80, "min": 24, "max": 240, "step": 8}}


def _arrow(g, x, y, c, dark):
    for j, half in enumerate((3, 2, 1, 0)):
        for i in range(-half, half + 1):
            g[y + j][x + i] = c
    for j, half in enumerate((3, 2, 1, 0)):
        for i in (-half - 1, half + 1):
            if 0 <= x + i < len(g[0]):
                g[y + j][x + i] = dark
    for i in range(-4, 5):
        g[y - 1][x + i] = dark
    g[y + 4][x] = dark


def build(kind: str = "window", theme: str = "classic_blue", width: int = 128, height: int = 80, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {list(THEMES)}")
    w, h = int(width), int(height)
    T = THEMES[theme]
    acc = T["accent"]
    name = f"ui-{kind}-{theme}"
    if kind == "window":
        return _ui.emit(name, w, h, [("panel", [frame(theme, w, h)])], tags=[("window", 0, 0)])
    if kind == "dialog":
        top = 10
        body = blank(w, h)
        overlay(body, frame(theme, w, h - top), 0, top)
        plate_w = min(64, w // 2)
        plate = frame(theme, plate_w, 16, bw=2, ornaments=False, tone=0.6)
        overlay(body, plate, 6, 1)
        arrows = []
        for fi, dy in enumerate((0, 1, 2, 1)):
            g = blank(w, h)
            _arrow(g, w - 12, h - 12 + dy, acc[1] if theme != "parchment" else acc[1], OUTLINE)
            arrows.append(g)
        return _ui.emit(name, w, h, [("panel", [body]), ("next arrow", arrows)], durations=[180, 120, 180, 120],
                        tags=[("dialog", 0, 3)])
    if kind == "tooltip":
        tail = 7
        g = blank(w, h)
        overlay(g, frame(theme, w, h - tail, bw=2, radius=3, ornaments=False), 0, 0)
        bd = THEMES[theme]["border"]
        cx = 14
        for j in range(tail):
            half = tail - 1 - j
            y = h - tail - 2 + j
            for i in range(-half - 1, half + 2):
                x = cx + i
                if abs(i) == half + 1 or j == tail - 1:
                    g[y][x] = OUTLINE
                elif abs(i) == half:
                    g[y][x] = bd[2] if i < 0 else bd[0]
                else:
                    g[y][x] = _ui.fill_px(theme, x, h - tail - 6, w, h - tail)
        return _ui.emit(name, w, h, [("panel", [g])])
    if kind == "title":
        g = blank(w, h)
        band_h = min(h, 24)
        y0 = (h - band_h) // 2
        tail = 10
        rib = THEMES["wood_gold"]["accent"] if theme != "wood_gold" else ["#5a0e14", "#a8202a", "#e85a4a"]
        for side in (0, 1):                                          # ribbon tails behind the banner
            for y in range(band_h - 6):
                for i in range(tail + 4):
                    x = i if side == 0 else w - 1 - i
                    notch = abs(y - (band_h - 6) / 2) < (tail + 4 - i) * 0.0 + (2 if i < 4 else -1)
                    if i < 4 and abs(y - (band_h - 6) / 2) < 4 - i:
                        continue
                    c = rib[0] if y in (0, band_h - 7) else (rib[1] if y < (band_h - 6) * 0.6 else rib[0])
                    if i == 0 or y in (0, band_h - 7) and False:
                        c = OUTLINE
                    g[y0 + 6 + y][x] = c
            for y in range(band_h - 6):
                for i in range(tail + 4):
                    x = i if side == 0 else w - 1 - i
                    if g[y0 + 6 + y][x] is not None and (y in (0, band_h - 7)):
                        g[y0 + 6 + y][x] = OUTLINE
        overlay(g, frame(theme, w - 2 * tail, band_h, bw=2, radius=3), tail, y0)
        return _ui.emit(name, w, h, [("banner", [g])])
    # tab: active (raised, joined to the panel below) and inactive (lower, darker)
    tabs = []
    for active in (True, False):
        g = blank(w, h)
        th = h if active else h - 3
        f = frame(theme, w, th + 4, bw=2, radius=3, ornaments=False, tone=0.5 if active else -0.6)
        f = f[:th]
        if active:
            row = [c if c is None else THEMES[theme]["fill"][0] for c in f[-1]]
            f[-1] = [OUTLINE if (i == 0 or i == w - 1) else c for i, c in enumerate(row)]
        overlay(g, f, 0, h - th)
        tabs.append(g)
    return _ui.emit(name, w, h, [("tab", tabs)], durations=[300, 300], tags=[("active", 0, 0), ("inactive", 1, 1)])
