"""Status icons (状态图标), 16×16 round badges for buffs, debuffs and ailments: ATK/DEF/SPD/MAG up & down (green
up / red down arrow), poison, burn, freeze, paralysis, sleep, petrify, curse, silence, blind, stun, regen, charm."""
from __future__ import annotations

from ._icon import OUTLINE, RAMPS
from .raster import DocBuilder, Grid

DESCRIPTION = "16×16 status badge: stat up/down (ATK, DEF, SPD, MAG) and ailments (poison, burn, freeze, sleep, …)."
ASSET_TYPE = "icon"
FULL_BLEED = True
GROUP = "Skill icons"

SYM = {
    "sword": [".......WW", "......WWW", ".....WWW.", "....WWW..", ".S.WWW...", "..SWW....", "..SSS....", ".S...S...", "S........"],
    "shield": [".WWWWWWWW.", ".WSSSSSSW.", ".WSWWWWSW.", ".WSWWWWSW.", ".WSWWWWSW.", ".WSSWWSSW.", "..WSSSSW..", "..WWSSWW..", "...WWWW...", "....WW...."],
    "boot": ["...WWW....", "...WSW....", "...WSW....", "SS.WSW....", ".SSWSW....", "SS.WSWW...", ".SSWSSWWW.", "...WSSSSSW", "...WWWWWWW", ".........."],
    "star": ["....WW....", "....WW....", "...WSSW...", "WWWWSSWWWW", ".WWSSSSWW.", "..WSSSSW..", "..WSWWSW..", ".WSW..WSW.", ".WW....WW.", ".........."],
    "drop": ["....WW....", "...WSSW...", "...WSSW...", "..WSSSSW..", ".WSSSSSSW.", ".WSWSSSSW.", ".WSWSSSSW.", ".WSSSSSSW.", "..WSSSSW..", "...WWWW..."],
    "flame": ["....W.....", "...WW..W..", "...WSW.WW.", "..WSSWWSW.", ".WSSSSSSW.", ".WSSWWSSW.", ".WSWWWWSW.", ".WSWWWWSW.", "..WSWWSW..", "...WWWW..."],
    "snow": ["....W....", ".W..W..W.", "..W.W.W..", "...WSW...", "WWWSSSWWW", "...WSW...", "..W.W.W..", ".W..W..W.", "....W...."],
    "bolt": [".....WWW..", "....WSSW..", "...WSSW...", "..WSSWWWW.", ".WSSSSSSW.", ".WWWWSSW..", "...WSSW...", "..WSSW....", "..WSW.....", "..WW......"],
    "zz": [".....WWWWW", "........W.", ".......W..", "WWWWW.WWWW", "...W......", "..W.......", ".W........", "WWWWW.....", ".........."],
    "stone": ["...SSSS...", "..SWSSSSS.", ".SWSdSSSSS", ".SSSdSSSSS", "SSSSSdSSSS", "SSSSdSdSSS", "SSSSSdSSS.", ".SSSSdSSS.", "..SSSSSS.."],
    "skull": ["..WWWWWW..", ".WWWWWWWW.", "WWWWWWWWWW", "WWddWWddWW", "WWddWWddWW", "WWWWddWWWW", ".WWWWWWWW.", "..WdWdWd..", "..WWWWWW.."],
    "mute": [".WWWWWWWW.", "WWSWWWWSWW", "WWWSWWSWWW", "WWWWSSWWWW", "WWWWSSWWWW", "WWWSWWSWWW", "WWSWWWWSWW", ".WWWWWWWW.", "..WW......", ".WW......."],
    "eye": [".........S", "...WWWW.S.", ".WWddWWSW.", "WWdddWSdWW", "WWdddSddWW", ".WWdSWWWW.", "...SWWW...", "..S.......", ".S........"],
    "stars": [".W......W.", "WWW....WWW", ".W..W...W.", "...WWW....", "....W.....", ".W.....W..", "WWW...WWW.", ".W.....W.."],
    "heart_plus": [".SS...SS.", "SSSS.SSSS", "SSSSWSSSS", "SSSWWWSSS", ".SSSWSSS.", "..SSSSS..", "...SSS...", "....S...."],
    "heart": [".SS...SS.", "SWSS.SSSS", "SWSSSSSSS", "SSSSSSSSS", ".SSSSSSS.", "..SSSSS..", "...SSS...", "....S...."],
}
ARROW = ["..G..", ".GGG.", "GGGGG", ".GGG.", ".GGG."]
# kind → (symbol, badge ramp, W colour, S colour, arrow: +1 up / -1 down / 0)
KINDS = {
    "atk_up": ("sword", "red", "#f4f4f8", "#c89a3a", 1), "atk_down": ("sword", "red", "#f4f4f8", "#c89a3a", -1),
    "def_up": ("shield", "blue", "#e8eef8", "#5a8ad8", 1), "def_down": ("shield", "blue", "#e8eef8", "#5a8ad8", -1),
    "spd_up": ("boot", "green", "#f4f4f0", "#c8a060", 1), "spd_down": ("boot", "green", "#f4f4f0", "#c8a060", -1),
    "mag_up": ("star", "purple", "#fff4b8", "#f0b030", 1), "mag_down": ("star", "purple", "#fff4b8", "#f0b030", -1),
    "poison": ("drop", "purple", "#2a0e40", "#b860f0", 0), "burn": ("flame", "red", "#ffd860", "#ff7a1a", 0),
    "freeze": ("snow", "blue", "#e8f8ff", "#7ad0ff", 0), "paralysis": ("bolt", "topaz", "#3a2a06", "#fff27a", 0),
    "sleep": ("zz", "blue", "#e8f0ff", "#e8f0ff", 0), "petrify": ("stone", "stone", "#e4e0ec", "#aaa6b4", 0),
    "curse": ("skull", "dark", "#ece4f4", "#ece4f4", 0), "silence": ("mute", "white", "#f8f8fc", "#d83a3a", 0),
    "blind": ("eye", "black", "#e8e8f0", "#ff5a5a", 0), "stun": ("stars", "topaz", "#fff6c0", "#fff6c0", 0),
    "regen": ("heart_plus", "green", "#ffffff", "#ff5a6a", 0), "charm": ("heart", "purple", "#ffffff", "#ff7ac8", 0),
}
PARAMS = {"status": {"type": "string", "default": "atk_up", "enum": list(KINDS)}}


def build(status: str = "atk_up", **_):
    if status not in KINDS:
        raise ValueError(f"status must be one of {list(KINDS)}")
    sym, ramp, wc, sc, arrow = KINDS[status]
    r = RAMPS[ramp]
    n = 16
    bad = [[None] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            dx, dy = x - 7.5, y - 7.5
            q = (dx * dx + dy * dy) ** 0.5
            if q > 7.6:
                continue
            if q > 6.6:
                bad[y][x] = OUTLINE
            elif q > 5.6:
                bad[y][x] = r[3] if dx + dy < -3 else (r[0] if dx + dy > 4 else r[2])
            else:
                bad[y][x] = r[1] if dx + dy < 2 else r[0]
    art = [[None] * n for _ in range(n)]
    rows = SYM[sym]
    h, w = len(rows), max(len(s) for s in rows)
    ox, oy = (n - w) // 2 - (1 if arrow else 0), (n - h) // 2 - (1 if arrow else 0)
    dark = "#4a4656" if sym == "stone" else OUTLINE
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                art[oy + j][ox + i] = {"W": wc, "S": sc, "d": dark}[ch]
    filled = {(x, y) for y in range(n) for x in range(n) if art[y][x] is not None}
    for (x, y) in filled:                                  # 1px dark outline round the symbol
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + a, y + b) not in filled and 0 <= x + a < n and 0 <= y + b < n and bad[y + b][x + a] is not None:
                art[y + b][x + a] = OUTLINE
    if arrow:
        col = ("#3ae06a", "#c8ffd4") if arrow > 0 else ("#ff3a3a", "#ffd0c8")
        ar = ARROW if arrow > 0 else ARROW[::-1]
        ax, ay = 10, 10
        cells = {(ax + i, ay + j) for j, row in enumerate(ar) for i, ch in enumerate(row) if ch == "G"}
        for (x, y) in list(cells):
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + a, y + b) not in cells and 0 <= x + a < n and 0 <= y + b < n:
                    art[y + b][x + a] = OUTLINE
        for (x, y) in cells:
            art[y][x] = col[1] if (x == ax + 2 and (y < ay + 2 if arrow > 0 else y > ay + 2)) else col[0]
    cols = []
    for g in (bad, art):
        for row in g:
            for c in row:
                if c and c not in cols:
                    cols.append(c)
    idx = {c: i for i, c in enumerate(cols)}
    d = DocBuilder(f"status-{status.replace('_', '-')}", n, n)
    d.palette(cols)
    for name, g in (("badge", bad), ("symbol", art)):
        li = d.layer(name)
        gg = Grid(n, n)
        gg.px = [[idx[c] if c else None for c in row] for row in g]
        d.paint(gg, li, 0)
    return d.calls
