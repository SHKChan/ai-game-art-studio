"""Shrine of Heroes — 96x96 environment prop: stone temple with pediment, pillars, a hero statue raising a
sword, red banners, mossy stone and two braziers whose flames loop (4 frames)."""
from __future__ import annotations

import math

from .raster import DocBuilder, Grid, bayer4, hash01

DESCRIPTION = "Shrine of Heroes: stone temple with a sword-raising hero statue, banners and animated braziers."
LOOP = True
ASSET_TYPE = "environment"
PARAMS = {"frames": {"type": "int", "default": 4, "max": 8}, "banner": {"type": "string", "default": "red", "enum": ["red", "blue", "green"]}}

BANNERS = {"red": ["#5e1220", "#a8242f", "#d8434a"], "blue": ["#14225e", "#2a46a8", "#4a78d8"], "green": ["#123e1e", "#226a32", "#3e9a4a"]}
PAL = ["#18131f",                                   # 0 outline
       "#33364a", "#545a72", "#7d849e", "#aab0c6", "#d6dae8",   # 1-5 stone ramp
       "#20212f", "#2c2e40",                        # 6-7 interior
       "#8e93a8", "#bcc1d2", "#e9ecf5",             # 8-10 marble statue
       "#7a5212", "#c89224", "#f2cf5a", "#fff4b8",  # 11-14 gold
       "#3c6a32", "#6a9e3e",                        # 15-16 moss
       "#c8361e", "#f47a22", "#ffc444", "#fff6d0"]  # 17-20 flame
O, S1, S2, S3, S4, S5, I0, I1, M0, M1, M2, G0, G1, G2, G3, MO0, MO1, F0, F1, F2, F3 = range(21)


def _stone(g: Grid, x0, y0, x1, y1, brick_w=8, brick_h=4, light_left=True):
    """Stone blocks with mortar lines and a lit left/top edge."""
    for y in range(y0, y1 + 1):
        row = (y - y0) // brick_h
        for x in range(x0, x1 + 1):
            off = (brick_w // 2) if row % 2 else 0
            bx = (x - x0 + off) % brick_w
            by = (y - y0) % brick_h
            if by == brick_h - 1 or bx == brick_w - 1:
                c = S1
            elif by == 0 or (bx == 0 and light_left):
                c = S4
            else:
                c = S3 if hash01(x // 2, y // 2, 3) > 0.25 else S2
            g.set(x, y, c)


def build(frames: int = 4, banner: str = "red", **_):
    W = H = 96
    pal = list(PAL)
    pal[17:17] = []  # keep indices stable
    bn = BANNERS[banner]
    pal = PAL + bn
    B0, B1, B2 = 21, 22, 23
    d = DocBuilder("shrine-of-heroes", W, H)
    d.palette(pal)
    l_back, l_struct, l_statue, l_decor, l_braz, l_fire = (d.layer(n) for n in
                                                          ("interior", "structure", "statue", "decor", "braziers", "flames"))

    # ---- interior back wall (dark, so the statue reads)
    back = Grid(W, H)
    back.rect(27, 27, 68, 69, I1)
    for y in range(27, 70):
        for x in range(27, 69):
            if (x - 27) % 10 == 9 or (y - 27) % 6 == 5:
                back.set(x, y, I0)
    # soft light pool behind the statue (dithered)
    for y in range(30, 66):
        for x in range(32, 64):
            dist = math.hypot((x - 48) / 14, (y - 44) / 18)
            if dist < 1 and bayer4(x, y) < (1 - dist) * 0.9:
                back.set(x, y, S1)

    # ---- structure: steps, platform, pillars, entablature, pediment
    st = Grid(W, H)
    for i, (x0, x1, y0, y1) in enumerate([(10, 85, 89, 92), (14, 81, 85, 88), (18, 77, 81, 84)]):
        st.rect(x0, y0, x1, y1, S3)
        st.rect(x0, y0, x1, y0, S5)
        st.rect(x0, y1, x1, y1, S1)
        for x in range(x0 + 6, x1, 12):
            st.set(x, y0 + 1, S2)
    _stone(st, 18, 70, 77, 80, brick_w=10, brick_h=4)
    st.rect(18, 70, 77, 70, S5)
    for px in (19, 68):  # pillars
        st.rect(px - 1, 66, px + 9, 69, S4)          # base
        st.rect(px - 1, 69, px + 9, 69, S2)
        st.rect(px, 30, px + 8, 65, S3)               # shaft
        for x in range(px, px + 9):                   # fluting + roundness shading
            t = (x - px) / 8
            c = S5 if t < 0.2 else (S4 if t < 0.45 else (S3 if t < 0.75 else S2))
            if (x - px) in (3, 6):
                c = S2
            st.rect(x, 30, x, 65, c)
        st.rect(px - 1, 26, px + 9, 29, S4)           # capital
        st.rect(px - 2, 26, px + 10, 26, S5)
        st.rect(px - 1, 29, px + 9, 29, S2)
    st.rect(12, 20, 83, 25, S3)                       # entablature
    st.rect(12, 20, 83, 20, S5)
    st.rect(12, 25, 83, 25, S1)
    for x in range(14, 83, 6):                        # dentils
        st.rect(x, 23, x + 2, 24, S2)
    st.polygon([(10, 20), (48, 4), (86, 20)], S3)      # pediment
    st.polygon([(16, 19), (48, 8), (80, 19)], S2)
    st.line(10, 20, 48, 4, S5)
    st.line(48, 4, 86, 20, S1)
    # gold sun emblem in the pediment
    for r_ in range(0, 4):
        st.ellipse(48, 14, 3.5 - r_ * 0.6, 3.5 - r_ * 0.6, [G0, G1, G2, G3][r_])
    for ang in range(0, 360, 45):
        st.set(48 + 5 * math.cos(math.radians(ang)), 14 + 4 * math.sin(math.radians(ang)), G1)

    # ---- statue on a pedestal: hero raising a sword
    sta = Grid(W, H)
    sta.rect(40, 60, 56, 69, S4)                      # pedestal
    sta.rect(40, 60, 56, 60, S5)
    sta.rect(41, 69, 55, 69, S2)
    sta.rect(44, 63, 52, 66, G1)                      # plaque
    sta.rect(45, 64, 51, 65, G2)
    sta.rect(44, 66, 52, 66, G0)
    # cape (behind)
    sta.polygon([(42, 37), (54, 37), (57, 56), (39, 56)], S2)   # cape: darker stone so the figure reads
    sta.line(39, 56, 57, 56, S1)
    sta.line(42, 37, 39, 56, S3)
    # legs
    sta.rect(44, 50, 46, 59, M1)
    sta.rect(50, 50, 52, 59, M1)
    sta.rect(47, 51, 49, 57, S2)                       # gap between the legs (cape behind)
    sta.rect(44, 50, 44, 57, M2)
    sta.rect(43, 58, 47, 59, M0)
    sta.rect(49, 58, 53, 59, M0)
    # torso + belt
    sta.polygon([(44, 37), (52, 37), (53, 50), (43, 50)], M1)
    sta.rect(44, 38, 45, 49, M2)
    sta.rect(43, 47, 53, 48, M0)
    # head
    sta.ellipse(48, 33, 3, 3, M1)
    sta.rect(45, 30, 51, 31, M0)                       # hair / helm band
    sta.rect(46, 32, 47, 33, M2)
    sta.set(50, 34, M0)                                # face shading
    # raised sword arm (right side of the image) and resting arm
    sta.line(52, 38, 56, 31, M1)
    sta.line(53, 38, 57, 32, M0)
    sta.rect(55, 29, 58, 31, M0)                       # fist + crossguard
    sta.rect(53, 28, 60, 28, G1)
    sta.line(56, 27, 56, 12 + 16, M2)                  # blade upward
    sta.rect(56, 15, 57, 27, M2)
    sta.rect(57, 15, 57, 27, M1)
    sta.set(56, 14, M2)
    sta.line(43, 39, 41, 47, M1)                       # left arm down
    sta.set(41, 48, M0)
    # selective outline only where the statue meets the dark interior
    ol = sta.copy()
    ol.outline(O)
    for y in range(H):
        for x in range(W):
            if ol.px[y][x] == O and sta.px[y][x] is None and back.get(x, y) is not None and y < 60:
                sta.set(x, y, O)

    # ---- decor: banners between pillars and statue, moss on stone
    dec = Grid(W, H)
    for bx in (30, 61):
        dec.rect(bx, 27, bx + 5, 47, B1)
        dec.rect(bx, 27, bx, 47, B2)
        dec.rect(bx + 5, 27, bx + 5, 47, B0)
        dec.polygon([(bx, 47), (bx + 5.9, 47), (bx + 3, 51)], B1)
        dec.rect(bx, 27, bx + 5, 28, G1)               # gold rod
        dec.rect(bx + 2, 34, bx + 3, 37, G2)           # emblem
        dec.set(bx + 1, 35, G1); dec.set(bx + 4, 35, G1)
    for (mx, my, n) in [(19, 62, 6), (75, 50, 5), (24, 80, 7), (66, 79, 6), (13, 90, 5), (80, 87, 4), (70, 64, 4)]:
        for k in range(n):
            x = mx + int((hash01(mx, k, 5) - 0.5) * 6)
            y = my + int((hash01(my, k, 6) - 0.3) * 4)
            if st.get(x, y) is not None:
                dec.set(x, y, MO1 if hash01(x, y, 8) > 0.5 else MO0)

    # ---- braziers on the platform corners
    br = Grid(W, H)
    for cx in (11, 85):
        br.rect(cx - 1, 74, cx + 1, 88, S1)            # stand
        br.rect(cx - 3, 87, cx + 3, 88, S2)
        br.polygon([(cx - 6, 68), (cx + 6, 68), (cx + 3, 74), (cx - 3, 74)], G1)  # bowl
        br.rect(cx - 6, 68, cx + 6, 68, G3)
        br.rect(cx + 1, 69, cx + 3, 73, G0)
    br_ol = br.copy()
    br_ol.outline(O)
    for y in range(H):
        for x in range(W):
            if br_ol.px[y][x] == O and br.px[y][x] is None and st.get(x, y) is None:
                br.set(x, y, O)

    # outline around the structure silhouette (outer edge only)
    sil = Grid(W, H)
    for g in (st, back):
        sil.merge(g)
    so = sil.copy()
    so.outline(O)
    for y in range(H):
        for x in range(W):
            if so.px[y][x] == O and sil.px[y][x] is None:
                st.set(x, y, O)

    d.paint(back, l_back, 0)
    d.paint(st, l_struct, 0)
    d.paint(sta, l_statue, 0)
    d.paint(dec, l_decor, 0)
    d.paint(br, l_braz, 0)
    if frames > 1:
        d.add_frames(frames - 1, 120, copy_from=0)

    # ---- flames: looping flicker per frame
    for fi in range(frames):
        fl = Grid(W, H)
        ph = 2 * math.pi * fi / frames
        for k, cx in enumerate((11, 85)):
            for y in range(52, 68):
                h = (67 - y) / 15.0                     # 0 at bowl, 1 at tip
                sway = 1.4 * math.sin(ph + h * 3 + k * 1.7) * h
                width = 5.2 * (1 - h) ** 0.8 + 0.6 * math.sin(ph * 2 + y + k)
                for x in range(cx - 7, cx + 8):
                    dx = abs(x + 0.5 - (cx + 0.5 + sway))
                    if dx > width:
                        continue
                    heat = (1 - dx / max(width, 0.1)) * (1 - h * 0.7)
                    heat += (hash01(x, y, fi + 10 * k) - 0.5) * 0.25
                    c = F3 if heat > 0.75 else F2 if heat > 0.5 else F1 if heat > 0.25 else F0
                    if h > 0.85 and hash01(x, y, fi, 3) > 0.5:
                        continue
                    fl.set(x, y, c)
            for e in range(3):                          # rising embers
                t = ((fi / frames) + e / 3 + k * 0.2) % 1.0
                ex = cx + int(3 * math.sin(e * 2.1 + ph))
                fl.set(ex, 50 - int(t * 12), F2 if t < 0.5 else F1)
        d.paint(fl, l_fire, fi)
        d.duration(fi, 120)
    d.tag("burn", 0, frames - 1)
    return d.calls
