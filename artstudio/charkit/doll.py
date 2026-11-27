"""Paper-doll prototype on the Craftpix base: recolour body regions into clothes, draw hair from the head layer,
re-material / re-shape the sword. Every frame uses that frame's own layers, so overlays follow the animation."""
from __future__ import annotations

from PIL import Image

from .base import layer_sheets  # noqa: F401  (re-exported)

SKIN_RANK = None
EYE = {(63, 106, 212), (55, 74, 143), (210, 221, 232), (17, 11, 0), (37, 170, 83), (34, 125, 86), (0, 0, 0)}
RAMPS = {  # 6 tones dark → light (outline first)
    "blue": ["#141a3a", "#22306e", "#2e4aa8", "#3e6ad0", "#5a92ec", "#8cc0ff"],
    "red": ["#2a0a10", "#5a1420", "#8e1e2a", "#c22e34", "#e85a4a", "#ff9a7a"],
    "green": ["#0c2410", "#164a1e", "#22702a", "#36983a", "#5cc050", "#9ae07a"],
    "white": ["#2a2a3a", "#6a6a80", "#9a9cb0", "#c4c6d4", "#e6e8f0", "#ffffff"],
    "black": ["#08080c", "#16141e", "#24202e", "#363044", "#4a4460", "#6a6280"],
    "grey": ["#1c1e26", "#3a3e4c", "#5a6070", "#7c8496", "#a4acbc", "#cfd6e2"],
    "brown": ["#1e1008", "#3e2414", "#5e3a20", "#82542e", "#a87240", "#d09a5e"],
    "purple": ["#1a0a2a", "#36165a", "#54248a", "#7838b8", "#a060e0", "#cc9aff"],
    "gold": ["#3a2404", "#6e4a0a", "#a87414", "#dca42a", "#f8d050", "#fff4b0"],
    "dark": ["#0e0816", "#24143a", "#3e2460", "#5e3a8a", "#8a5ac0", "#c8a2f0"],
    "pink": ["#3a0c24", "#6e1a44", "#a82a6a", "#da4a8e", "#f47ab4", "#ffc0dc"],
    "blonde": ["#3a2408", "#7a5414", "#b08420", "#dcb03a", "#f4d460", "#fff2a8"],
    "silver": ["#2a2e3a", "#525868", "#7c8496", "#a8b0c0", "#d0d6e2", "#ffffff"],
}

def _pixels(img):
    return img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)

def lum(p):
    return 0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]

def skin_rank(body_img):
    cols = {}
    for p in _pixels(body_img):
        if p[3]:
            cols[p] = cols.get(p, 0) + 1
    tones = sorted(cols, key=lum)
    return {c: i for i, c in enumerate(tones)}

def recolor_body(img, rank, outfit, dirn):
    """Shirt / pants / boots by region; luminance rank → clothing ramp tone (keeps the original shading)."""
    w, h = img.size
    px = img.load()
    bb = img.getbbox()
    if not bb:
        return img
    x0, y0, x1, y1 = bb
    out = img.copy()
    po = out.load()
    H = y1 - y0
    waist = y0 + int(H * 0.5)
    feet = y1 - 2
    # torso half width at the waist row
    row = [x for x in range(w) if px[x, waist][3]]
    cx = (min(row) + max(row)) / 2 if row else (x0 + x1) / 2
    tw = (max(row) - min(row)) / 2 + 1 if row else 4
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = px[x, y]
            if not p[3] or p[:3] + (255,) not in rank:
                continue
            r = rank[p[:3] + (255,)]
            region = None
            if y >= feet:
                region = outfit.get("boots")
            elif y >= waist:
                region = outfit.get("pants")
            elif abs(x + .5 - cx) <= tw + (0 if dirn in ("front", "back") else 1):
                region = outfit.get("shirt")
            if region:
                po[x, y] = hx(RAMPS[region][min(5, r)])
    return out

def hair_layers(head, outfit, dirn, behind_body):
    """Return (front_hair, back_hair) images for one 64×64 frame from the head layer."""
    style, ramp = outfit.get("hair", ("short", "brown"))
    R = RAMPS[ramp]
    w, h = head.size
    hp = head.load()
    mask = {(x, y) for y in range(h) for x in range(w) if hp[x, y][3]}
    front = Image.new("RGBA", (w, h)); back = Image.new("RGBA", (w, h))
    if not mask:
        return front, back
    xs = [p[0] for p in mask]; ys = [p[1] for p in mask]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    eyes = [(x, y) for (x, y) in mask if hp[x, y][:3] in EYE]
    hw, hh = x1 - x0 + 1, y1 - y0 + 1
    hair = set()
    if eyes and dirn != "back":
        et = min(e[1] for e in eyes)
        ex0, ex1 = min(e[0] for e in eyes), max(e[0] for e in eyes)
        hl = et - 2
        for (x, y) in mask:
            if y < hl:
                hair.add((x, y))
            if dirn == "front" and (x <= x0 + 1 or x >= x1 - 1) and y < et + 3:
                hair.add((x, y))                                     # sideburns
            if dirn == "side_left" and x > ex1 + 2 and y < y1 - 2:
                hair.add((x, y))
            if dirn == "side_right" and x < ex0 - 2 and y < y1 - 2:
                hair.add((x, y))
        if dirn == "front":                                          # fringe tips
            for x in range(x0 + 2, x1 - 1, 3):
                hair.add((x, hl)); 
    else:
        for (x, y) in mask:
            if y < y1 - 1:
                hair.add((x, y))
    # volume: grow 1 px up / out around the top of the head
    vol = set()
    for (x, y) in hair:
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (-1, -1), (1, -1)):
            q = (x + dx, y + dy)
            if q not in mask and q[1] < y0 + hh * 0.6:
                vol.add(q)
    hair |= vol
    extra_front, extra_back = set(), set()
    cxh = (x0 + x1) / 2
    if style == "spiky":
        top = {}
        for (x, y) in hair:
            top[x] = min(top.get(x, 99), y)
        xs_ = sorted(top)
        for k, x in enumerate(xs_[1:-1:2]):
            hgt = 2 if k % 2 == 0 else 1
            lean = -1 if x < cxh - 1 else (1 if x > cxh + 1 else 0)
            for j in range(1, hgt + 1):
                extra_front.add((x + (lean if j == 2 else 0), top[x] - j))
                if j == 1:
                    extra_front.add((x + lean, top[x] - j))
    elif style == "long":
        if dirn == "front":
            for x in list(range(x0 - 1, x0 + 2)) + list(range(x1 - 1, x1 + 2)):
                for y in range(y0 + hh // 3, y1 + 8):
                    extra_back.add((x, y))
        elif dirn == "back":
            for x in range(x0, x1 + 1):
                for y in range(y1 - 2, y1 + 7 - (1 if x in (x0, x1) else 0)):
                    extra_front.add((x, y))
        else:
            bx = x1 if dirn == "side_left" else x0
            sgn = 1 if dirn == "side_left" else -1
            for y in range(y0 + 3, y1 + 7):
                for k in range(3):
                    extra_back.add((bx + sgn * (k - 1), y))
    elif style == "ponytail":
        if dirn in ("side_left", "side_right"):
            sgn = 1 if dirn == "side_left" else -1
            bx = x1 if dirn == "side_left" else x0
            for i in range(7):                                       # tail: out, then down, tapering
                x = bx + sgn * (1 + min(i, 3))
                wdt = 3 if i < 4 else 2
                for y in range(y0 + 3 + i, y0 + 3 + i + wdt):
                    extra_back.add((x, y)); extra_back.add((x - sgn, y))
            extra_back.add((bx + sgn, y0 + 3)); extra_back.add((bx + sgn, y0 + 2))
        elif dirn == "back":
            for y in range(y0 + 3, y1 + 7):
                wdt = 1 if y > y1 + 3 else 2
                for x in range(int(cxh) - wdt, int(cxh) + wdt + (1 if wdt == 2 else 1)):
                    extra_front.add((x, y))
        else:
            for y in range(y0 + 3, y0 + 8):
                extra_back.add((x0 - 1, y)); extra_back.add((x1 + 1, y)); extra_back.add((x1 + 2, y + 1))
    def paint(img, pts):
        p = img.load()
        for (x, y) in pts:
            if not (0 <= x < w and 0 <= y < h):
                continue
            edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                t = 0
            else:
                lit = ((x - x0) / max(1, hw)) * 0.5 + ((y - y0) / max(1, hh + 8)) * 0.8
                t = 4 if lit < 0.25 else (3 if lit < 0.5 else 2)
                if (x + y // 3) % 4 == 0 and t > 2:
                    t -= 1                                           # strands
            p[x, y] = hx(R[t])
    paint(front, hair | extra_front)
    paint(back, extra_back)
    return front, back

def recolor_weapon(img, outfit):
    mat = outfit.get("weapon", "steel")
    if mat == "steel":
        return img
    out = img.copy()
    po, pi = out.load(), img.load()
    blade = [p for p in set(_pixels(img)) if p[3] and p[2] > p[0]]
    order = sorted(blade, key=lum)
    rank = {c: i for i, c in enumerate(order)}
    R = RAMPS[mat]
    for y in range(img.height):
        for x in range(img.width):
            p = pi[x, y]
            if p[3] and p in rank:
                po[x, y] = hx(R[min(5, int(rank[p] * 6 / max(1, len(order))) + (0 if rank[p] else 0))])
    return out

def axe_from_sword(front, back, body):
    """Replace the sword with an axe: find the sword axis (PCA), keep a wooden haft, add a head near the tip."""
    import numpy as np
    pts = []
    for img in (front, back):
        a = np.asarray(img)
        ys, xs = np.nonzero(a[..., 3])
        pts += list(zip(xs, ys))
    if len(pts) < 6:
        return front, back
    P = np.array(pts, float)
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    ax = vt[0]
    t = (P - c) @ ax
    bb = body.getbbox()
    bc = np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]) if bb else c
    e1, e2 = c + ax * t.min(), c + ax * t.max()
    tip, hilt = (e1, e2) if np.linalg.norm(e1 - bc) > np.linalg.norm(e2 - bc) else (e2, e1)
    wood = [hx(x) for x in RAMPS["brown"]]
    steel = [hx(x) for x in RAMPS["grey"]]
    outs = []
    for img in (front, back):
        o = img.copy(); po = o.load(); pi = img.load()
        for y in range(img.height):
            for x in range(img.width):
                p = pi[x, y]
                if p[3] and p[2] > p[0]:                          # blade pixels → haft
                    po[x, y] = wood[2 if (x + y) % 2 else 3]
        outs.append(o)
    # head on whichever layer owns the tip
    d = tip - hilt
    L = np.linalg.norm(d) or 1
    d /= L
    n = np.array([-d[1], d[0]])
    if np.dot(n, tip - bc) < 0:
        n = -n
    hc = tip - d * 2.5
    poly = [hc - d * 2.5, hc + d * 1.5, hc + d * 2.5 + n * 5, hc - d * 4.5 + n * 5]
    tgt = outs[0] if any(front.getpixel((min(63, max(0, int(tip[0]))), min(63, max(0, int(tip[1])))))[3] for _ in [0]) else outs[1]
    from PIL import ImageDraw
    dr = ImageDraw.Draw(tgt)
    dr.polygon([tuple(p) for p in poly], fill=steel[3], outline=steel[0])
    ex = [hc - d * 4 + n * 5, hc + d * 2 + n * 5]
    dr.line([tuple(ex[0]), tuple(ex[1])], fill=steel[5])
    return outs[0], outs[1]
