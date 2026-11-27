"""Skeleton soldier on the base body: the skin is re-materialled as bone (keeping the pack's shading), the torso gets
ribs and a spine, the head becomes a skull (dark sockets with a glowing pupil, nasal hole, teeth) — frame by frame,
so it plays every base animation. Plus Summon_Rise: the character climbs out of the ground inside a necromantic
circle (what a necromancer's summon looks like from the skeleton's side)."""
from __future__ import annotations

import math

from PIL import Image

from . import costume, doll, equip
from .base import DIRS, FEET

BONE = doll.RAMPS["bone"]
GAP = (34, 26, 22, 255)
TORSO = 2                                   # half width of the ribcage column                     # shadow between bones / inside the sockets
IRIS = {(63, 106, 212), (55, 74, 143), (37, 170, 83), (34, 125, 86)}
PUPIL = {(63, 106, 212), (37, 170, 83)}     # the lit part of the iris becomes the glowing pupil, the rest a dark socket


def shadow_face(head):
    """Face in the shadow of a hood: skin darkened to a cold grey-violet, eyes (already glowing) kept."""
    out = head.copy()
    p = out.load()
    R = [doll.hx(c) for c in ("#0e0a14", "#1c1626", "#2a2236", "#3a3048")]
    tones = sorted({p[x, y] for y in range(64) for x in range(64) if p[x, y][3] and p[x, y][:3] not in doll.EYE
                    and p[x, y][:3] not in {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in doll.RAMPS["necro"]}},
                   key=doll.lum)
    rank = {c: i for i, c in enumerate(tones)}
    for y in range(64):
        for x in range(64):
            c = p[x, y]
            if c in rank:
                p[x, y] = R[min(3, rank[c] * 4 // max(1, len(tones)))]
    return out


def glowing_eyes(head, glow):
    """Recolour the iris (e.g. a necromancer's green eyes); everything else unchanged."""
    out = head.copy()
    p = out.load()
    R = doll.RAMPS[glow]
    for y in range(64):
        for x in range(64):
            c = p[x, y]
            if c[3] and c[:3] in IRIS:
                p[x, y] = doll.hx(R[4] if c[:3] in PUPIL else R[2])
    return out


def _bone(rank_index, n):
    """Map a skin tone (rank among n tones, dark → light) to the bone ramp; the darkest stays the outline."""
    if rank_index == 0:
        return doll.hx("#2a2018")
    return doll.hx(BONE[min(5, 1 + round(rank_index * 4 / max(1, n - 1)))])


def bone_body(dressed, raw, dirn, head=None):
    """Turn a body frame into a see-through skeleton: skin → bone, the torso rebuilt as ribs with open gaps between
    them, a spine crossing an empty belly and a pelvis, and every limb thinned to a single bone with an outline."""
    out = dressed.copy()
    po, pr = out.load(), raw.load()
    tones = sorted({pr[x, y] for y in range(64) for x in range(64) if pr[x, y][3]}, key=doll.lum)
    rank = {c: i for i, c in enumerate(tones)}
    for y in range(64):
        for x in range(64):
            p = pr[x, y]
            if p[3] and po[x, y] == p:                               # untouched skin (clothes were recoloured)
                po[x, y] = _bone(rank[p], len(tones))
    bi = equip.body_info(raw)
    if not bi:
        return out
    # torso centre: under the middle of the head's lowest rows (the chin) — arms raised over the shoulders would
    # throw off anything measured on the body itself
    hi = equip.head_info(head) if head is not None else None
    if hi:
        chin = [x for (x, y) in hi["mask"] if y >= hi["y1"] - 1]
        cx = (min(chin) + max(chin)) // 2
    else:
        neck = [x for x in range(64) if pr[x, bi["y0"]][3]]
        cx = (min(neck) + max(neck)) // 2 if neck else int(round(bi["cx"] - .5))
    side = dirn in ("side_left", "side_right")
    spine = cx if not side else cx + (1 if dirn == "side_left" else -1)   # from the side the spine is at the back
    top = (hi["y1"] + 1) if hi else bi["y0"] + 3                      # ribs start under the chin
    waist = top + 3
    hollow, pel = waist + 1, waist + 2
    half = TORSO if not side else TORSO - 1
    light, mid, dark = doll.hx(BONE[4]), doll.hx(BONE[3]), doll.hx(BONE[1])
    OUTL = doll.hx("#2a2018")
    clear = (0, 0, 0, 0)
    in_torso = lambda x, y: top - 1 <= y <= pel and abs(x - cx) <= half + 1
    bone = lambda q: po[q][3] and doll.lum(po[q]) > 110

    # 1. limbs: keep the middle pixel of each limb cross-section (across the thinner direction) as the bone
    limb = {(x, y) for y in range(64) for x in range(64)
            if po[x, y][3] and not in_torso(x, y) and y >= top - 1 and dressed.getpixel((x, y)) == raw.getpixel((x, y))}
    def run(x, y, dx, dy):
        n0 = n1 = 0
        while (x - dx * (n0 + 1), y - dy * (n0 + 1)) in limb and bone((x - dx * (n0 + 1), y - dy * (n0 + 1))):
            n0 += 1
        while (x + dx * (n1 + 1), y + dy * (n1 + 1)) in limb and bone((x + dx * (n1 + 1), y + dy * (n1 + 1))):
            n1 += 1
        return n0, n1
    core = set()
    feet = bi["y1"] - 2
    for (x, y) in limb:
        if not bone((x, y)):
            continue
        if y >= feet:                                                # feet stay as they are: they hold the ground
            core.add((x, y)); continue
        l, r = run(x, y, 1, 0)
        u, d = run(x, y, 0, 1)
        if l + r <= u + d:
            keep = l == (l + r) // 2                                 # centre of the horizontal cross-section
        else:
            keep = u == (u + d) // 2
        if keep:
            core.add((x, y))
    cols = {q: po[q] for q in core}
    for q in limb:
        po[q] = clear
    for q, c in cols.items():
        po[q] = light if doll.lum(c) > 150 else mid
    for (x, y) in core:                                             # outline the thin bones
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + a, y + b)
            if q in limb and q not in core:
                po[q] = OUTL

    # 2. torso: just a pole — the spine (vertebrae), with a collarbone bar the arms hang from and a pelvis bar the
    #    legs hang from; everything else in the torso is empty
    for y in range(top - 1, pel + 1):
        for x in range(cx - half - 1, cx + half + 2):
            po[x, y] = clear
    sx = spine
    for y in range(top - 1, pel + 1):
        po[sx, y] = light if (y - top) % 2 else mid                  # vertebrae
        for x in (sx - 1, sx + 1):
            po[x, y] = OUTL
    def bar(y, x0, x1):
        for x in range(x0, x1 + 1):
            po[x, y] = light
            if not po[x, y - 1][3]:
                po[x, y - 1] = OUTL
            if not po[x, y + 1][3]:
                po[x, y + 1] = OUTL
        po[x0 - 1, y] = OUTL; po[x1 + 1, y] = OUTL
    def reach(y, sgn):                                               # nearest limb pixel left / right of the spine
        for k in range(1, 8):
            x = sx + sgn * k
            for yy in (y - 1, y, y + 1):
                if (x, yy) in core:
                    return x
        return sx + sgn * half
    if not side:
        bar(top, reach(top, -1), reach(top, 1))                      # collarbone
        bar(pel, reach(pel + 1, -1), reach(pel + 1, 1))              # pelvis
    else:
        bar(pel, sx - 1, sx + 1)
    for (x, y) in core:                                              # the bars must not cover the bones they meet
        if po[x, y] == OUTL:
            po[x, y] = cols.get((x, y), light)
    return out


def _shape_skull(img, hi, dirn, eyes):
    """Skull silhouette: pinch the temples, narrow the jaw (cheekbones stand out), then re-outline."""
    p = img.load()
    y0, y1 = hi["y0"], hi["y1"]
    hh = y1 - y0 + 1
    if eyes and dirn != "back":
        eb = max(e[1] for e in eyes)
        temple, jaw = min(e[1] for e in eyes) - 3, eb + 2
    else:
        temple, jaw = y0 + int(hh * 0.55), y0 + int(hh * 0.75)
    sgn = {"side_right": 1, "side_left": -1}.get(dirn, 0)
    for y in range(temple, y1 + 1):
        xs = [x for x in range(64) if p[x, y][3]]
        if not xs:
            continue
        k = 1 if y < jaw else 2
        if y == jaw:
            k = 3 if not sgn else 2                                  # notch under the cheekbone
        if sgn == 0:
            cut = list(range(min(xs), min(xs) + k)) + list(range(max(xs) - k + 1, max(xs) + 1))
        elif y >= jaw:                                               # side: the back of the jaw / nape goes
            cut = list(range(max(xs) - k - 1, max(xs) + 1)) if sgn < 0 else list(range(min(xs), min(xs) + k + 2))
        else:
            cut = [max(xs)] if sgn < 0 else [min(xs)]
        for x in cut:
            p[x, y] = (0, 0, 0, 0)
    OUTL = doll.hx("#2a2018")
    glow = {p[x, y] for (x, y) in eyes} if eyes else set()
    edge = [(x, y) for y in range(64) for x in range(64) if p[x, y][3] and p[x, y] not in glow and any(
        not (0 <= x + a < 64 and 0 <= y + b < 64) or not p[x + a, y + b][3] for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for q in edge:
        p[q] = OUTL


def skull(head, dirn, glow="necro"):
    """Bone head with dark sockets, a glowing pupil per eye, nasal hole and teeth."""
    out = head.copy()
    p = out.load()
    tones = sorted({p[x, y] for y in range(64) for x in range(64) if p[x, y][3] and p[x, y][:3] not in doll.EYE},
                   key=doll.lum)
    rank = {c: i for i, c in enumerate(tones)}
    G = doll.hx(doll.RAMPS[glow][4])
    eyes = []
    for y in range(64):
        for x in range(64):
            c = p[x, y]
            if not c[3]:
                continue
            if c[:3] in doll.EYE:
                eyes.append((x, y))
                p[x, y] = G if c[:3] in PUPIL else GAP
            else:
                p[x, y] = _bone(rank[c], len(tones))
    hi = equip.head_info(head)
    mask = hi["mask"] if hi else set()
    edge = {(x, y) for (x, y) in mask if any((x + a, y + b) not in mask for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    if eyes and dirn != "back":
        eb = max(e[1] for e in eyes)
        ex0, ex1 = min(e[0] for e in eyes), max(e[0] for e in eyes)
        y1 = hi["y1"]
        eyeset = set(eyes)
        for (x, y) in eyes:                                          # widen the sockets by a pixel all round
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + a, y + b)
                if q in mask and q not in edge and q not in eyeset and p[q] != G:
                    p[q] = GAP
        def dark(q):
            if q in mask and q not in edge:
                p[q] = GAP
        if dirn == "front":
            nx = (ex0 + ex1) // 2
            for q in ((nx, eb + 2), (nx + 1, eb + 2), (nx, eb + 3)):   # nasal cavity: little upside-down heart
                dark(q)
            ty = min(y1 - 1, eb + 5)
            for x in range(nx - 3, nx + 5):                          # mouth slit with teeth over it
                dark((x, ty))
                if (x - nx) % 2 == 0 and (x, ty - 1) in mask and (x, ty - 1) not in edge:
                    p[x, ty - 1] = doll.hx(BONE[5])
        else:
            sgn = 1 if dirn == "side_right" else -1
            fx = ex1 if sgn > 0 else ex0
            dark((fx, eb + 2)); dark((fx - sgn, eb + 2))
            ty = min(y1 - 1, eb + 5)
            for k in range(4):
                x = fx - sgn * k
                dark((x, ty))
                if k % 2 == 0 and (x, ty - 1) in mask and (x, ty - 1) not in edge:
                    p[x, ty - 1] = doll.hx(BONE[5])
            for k in range(3):                                       # cheekbone / jaw hinge
                dark((fx - sgn * (5 + k // 2), ty - 2 + k))
    if hi:                                                           # a crack across the cranium
        x0, y0 = hi["x0"], hi["y0"]
        cx = x0 + (hi["x1"] - x0) // 3 if dirn != "side_left" else hi["x1"] - (hi["x1"] - x0) // 3
        for k, (dx, dy) in enumerate(((0, 1), (1, 2), (1, 3))):
            q = (cx + dx, y0 + dy)
            if q in mask and q not in edge:
                p[q] = GAP
    if hi:
        _shape_skull(out, hi, dirn, eyes)
    return out


# ------------------------------------------------------------------ Summon_Rise
RISE = [(30, 120), (24, 110), (18, 110), (12, 110), (7, 110), (3, 120), (0, 140), (0, 220)]   # (depth px, ms)
DIRT = [doll.hx(c) for c in ("#3e2414", "#5e3a20", "#82542e")]


def _shift(img, dy, ground):
    if img is None:
        return None
    out = Image.new("RGBA", img.size)
    out.alpha_composite(img, (0, dy))
    p = out.load()
    for y in range(ground, out.height):
        for x in range(out.width):
            p[x, y] = (0, 0, 0, 0)
    return out


def rise(frames_idle, colour):
    """frames_idle: [{group: image}] of one facing → Summon_Rise frames (the body climbs out of the ground)."""
    from .cast import rune_circle, ramp
    C = ramp(colour)
    ground = FEET[1] + 1
    out = []
    for i, (depth, _ms) in enumerate(RISE):
        src = frames_idle[i % len(frames_idle)]
        g = {k: _shift(v, depth, ground) for k, v in src.items() if k != "shadow"}
        g["flash"] = None
        level = 1.0 if i < 6 else 0.5
        shadow = src.get("shadow") if depth == 0 else None
        fx = Image.new("RGBA", (64, 64))
        q = fx.load()
        fxx, fy = FEET
        if depth > 0:                                                  # the crack in the ground and dirt thrown up
            w = 3 + (30 - depth) // 5
            for x in range(fxx - w, fxx + w + 1):
                q[x, fy] = GAP
                q[x, fy - 1] = DIRT[1] if (x + i) % 3 else DIRT[2]
            for k in range(6):
                dx = (k - 2.5) * (2 + i * 0.6)
                dy = -(2 + (i * 3 + k * 5) % 7)
                x, y = int(fxx + dx), int(fy - 1 + dy)
                if 0 <= x < 64 and 0 <= y < 64:
                    q[x, y] = DIRT[k % 3]
        for k in range(4 if i < 7 else 0):                             # wisps rising from the circle
            x = fxx - 9 + k * 6 + (i % 2)
            y = fy - 2 - ((i * 2 + k * 3) % 9)
            if 0 <= x < 64 and 0 <= y < 64:
                q[x, y] = C[4]
                if y + 1 < 64:
                    q[x, y + 1] = C[2]
        g["shadow"] = costume.stack(rune_circle(level, colour), shadow)
        g["front"] = costume.stack(g.get("front"), fx)
        out.append(g)
    return out, [ms for _, ms in RISE]


# ------------------------------------------------------------------ shield
def shield(hand, dirn, rim="grey", wood="brown"):
    """Small round buckler on the off (left) hand: iron rim, wooden boards, iron boss, a rust spot. Its face points
    outwards from the forearm, so it is seen face-on from the front and when the arm is the near side (facing left);
    facing right it hangs behind the body and peeks out in front; from the back we see the boards' back and the strap."""
    img = Image.new("RGBA", (64, 64))
    p = img.load()
    R, W = [doll.hx(c) for c in doll.RAMPS[rim]], [doll.hx(c) for c in doll.RAMPS[wood]]
    OUTL = doll.hx("#1a1410")
    cx, cy = hand[0] + {"side_right": 2, "side_left": 0}.get(dirn, 0), hand[1] - 1
    r = 4.4
    pts = {(x, y) for y in range(cy - 5, cy + 6) for x in range(cx - 5, cx + 6)
           if (x + .5 - cx - .5) ** 2 + (y + .5 - cy - .5) ** 2 <= r * r}
    for (x, y) in pts:
        if not (1 <= x < 63 and 1 <= y < 63):
            continue
        d = math.hypot(x - cx, y - cy)
        if any((x + a, y + b) not in pts for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            p[x, y] = OUTL
        elif d > r - 1.4:                                            # thin iron band round the wooden edge
            p[x, y] = R[4] if (x - cx) + (y - cy) < 0 else R[2]
        elif dirn == "back":
            p[x, y] = W[2] if (y - cy) % 2 else W[1]                 # back of the boards
        else:
            p[x, y] = W[3] if (x - cx) % 3 else W[2]                 # boards (plank seams)
    if 1 <= cx < 63 and 1 <= cy < 63:
        if dirn == "back":
            for x in range(cx - 1, cx + 2):
                p[x, cy] = doll.hx(doll.RAMPS["leather"][1]) if "leather" in doll.RAMPS else W[0]   # strap
        else:
            p[cx, cy] = R[5]; p[cx - 1, cy] = R[3]; p[cx, cy + 1] = R[2]   # iron boss
    q = (cx + 2, cy + 1)
    if q in pts and p[q] != OUTL and 1 <= q[0] < 63 and 1 <= q[1] < 63:
        p[q] = doll.hx(doll.RAMPS["rust"][3])                        # rust spot on the rim
    return img
