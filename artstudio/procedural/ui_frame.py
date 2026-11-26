"""UI frames (头像框与格子): portrait frame, inventory / equipment slot and skill-bar slot in four themes. Slots have
frames normal / selected / locked (tags); the portrait frame has an ornate crest and a transparent window."""
from __future__ import annotations

import math

from . import _ui
from ._ui import THEMES, blank, frame, greyed, mix, overlay
from ._icon import OUTLINE

DESCRIPTION = "JRPG UI frame: portrait frame, item slot or skill slot in 4 themes; slots = normal / selected / locked."
ASSET_TYPE = "ui"
GROUP = "UI"
FULL_BLEED = True
KINDS = ["portrait", "slot", "skill_slot"]
PARAMS = {"kind": {"type": "string", "default": "slot", "enum": KINDS},
          "theme": {"type": "string", "default": "classic_blue", "enum": list(THEMES)},
          "size": {"type": "int", "default": 40, "min": 24, "max": 128, "step": 4}}


def _lock(g, cx, cy, s):
    """Padlock centred at (cx, cy); s = half width of the body."""
    body, shack, hi = "#9a9fae", "#6a6f7e", "#dfe3ee"
    top = cy - s - 1
    for y in range(top - s, top + 1):                                  # shackle: inverted U
        for x in range(cx - s + 1, cx + s):
            edge = x in (cx - s + 1, cx + s - 1) or y == top - s
            inner = x in (cx - s + 2, cx + s - 2) or y == top - s + 1
            if edge:
                g[y][x] = OUTLINE
            elif inner and not (x in (cx - s + 2, cx + s - 2) and y == top - s + 1 and False):
                if x in (cx - s + 2, cx + s - 2) or y == top - s + 1:
                    if not (cx - s + 3 <= x <= cx + s - 3 and y > top - s + 1):
                        g[y][x] = shack
    for y in range(top, cy + s + 1):
        for x in range(cx - s, cx + s + 1):
            g[y][x] = OUTLINE if (y in (top, cy + s) or abs(x - cx) == s) else (hi if y == top + 1 else body)
    g[cy][cx] = OUTLINE
    g[cy + 1][cx] = OUTLINE


def build(kind: str = "slot", theme: str = "classic_blue", size: int = 40, **_):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {list(THEMES)}")
    n = int(size)
    T = THEMES[theme]
    if kind == "portrait":
        n = max(n, 48)
        g = frame(theme, n, n, bw=T["bw"] + 1)
        win = T["bw"] + 3
        for y in range(win, n - win):                                  # transparent window for the face
            for x in range(win, n - win):
                g[y][x] = None
        for x in range(win - 1, n - win + 1):
            g[win - 1][x] = OUTLINE; g[n - win][x] = T["border"][2]
        for y in range(win - 1, n - win + 1):
            g[y][win - 1] = OUTLINE; g[y][n - win] = T["border"][2]
        ad, am, al = T["accent"]
        cx = n // 2                                                    # crest gem on the top edge
        for y in range(0, 7):
            for x in range(cx - 4, cx + 5):
                d = abs(x - cx) + abs(y - 3)
                if d <= 4:
                    g[y][x] = OUTLINE if d == 4 else (al if d <= 1 and y <= 3 else (am if x <= cx else ad))
        return _ui.emit(f"ui-portrait-{theme}", n, n, [("frame", [g])])
    frames = []
    for state in ("normal", "selected", "locked"):
        g = frame(theme, n, n, bw=2, radius=3, inset=True, ornaments=False, tone=-0.3,
                  highlight=state == "selected")
        if kind == "skill_slot":                                       # bevelled diamond notches at the corners
            for (x, y) in ((3, 3), (n - 4, 3), (3, n - 4), (n - 4, n - 4)):
                g[y][x] = T["accent"][1]
        if state == "selected":                                        # glowing corner brackets outside the bevel
            al = T["accent"][2]
            L = max(4, n // 5)
            for (cx, cy, sx, sy) in ((0, 0, 1, 1), (n - 1, 0, -1, 1), (0, n - 1, 1, -1), (n - 1, n - 1, -1, -1)):
                for i in range(L):
                    g[cy][cx + sx * i] = al
                    g[cy + sy * i][cx] = al
                    g[cy + sy][cx + sx * i] = "#ffffff" if i < L - 1 else al
                    g[cy + sy * i][cx + sx] = "#ffffff" if i < L - 1 else al
        if state == "locked":
            g = greyed(g)
            _lock(g, n // 2, n // 2, max(3, n // 9))
        frames.append(g)
    return _ui.emit(f"ui-{kind.replace('_', '-')}-{theme}", n, n, [("slot", frames)], durations=[300] * 3,
                    tags=[("normal", 0, 0), ("selected", 1, 1), ("locked", 2, 2)])
