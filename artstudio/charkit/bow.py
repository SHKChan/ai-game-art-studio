"""Synthesised bow attack for the Craftpix base (which has no bow animation). The body follows the Sword_Attack poses
(wind-up → lunge → recover) and a bow, string and arrow are drawn per frame: ready → nock → draw → full draw →
release → follow-through → recover, in all four facings.

Right-handed archer, bow in the left hand: facing right the bow is on the far side (behind the body) with the string
and arrow in front; facing left the bow is in front; from the back everything is behind the body (no arms visible);
from the front the bow faces the viewer in the screen-right hand, arrowhead pointing out of the screen."""
from __future__ import annotations

import math

from PIL import Image

from . import costume, doll, equip
from .base import DIRS

OUT = (16, 10, 18, 255)
WOOD = [(70, 40, 18, 255), (128, 82, 40, 255), (176, 122, 62, 255)]
STRING = (226, 226, 236, 255)
SHAFT = (150, 108, 64, 255)
TIP = (205, 215, 228, 255)
FLETCH = (205, 60, 56, 255)
SKIN = (225, 178, 110, 255)
def line(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    return {(int(round(x0 + (x1 - x0) * i / max(1, n - 1))), int(round(y0 + (y1 - y0) * i / max(1, n - 1)))) for i in range(n)}

def put(img, pts, col, outline=False):
    p = img.load()
    if outline:
        for (x, y) in pts:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in pts and 0 <= q[0] < 64 and 0 <= q[1] < 64 and p[q][3] == 0:
                    p[q] = OUT
    for (x, y) in pts:
        if 0 <= x < 64 and 0 <= y < 64:
            p[x, y] = col

def bow_arc(cx, cy, h, bulge, rot=0.0):
    """Arc of a bow: list of points top→bottom, bulging towards +x before rotation."""
    pts = []
    for i in range(h + 1):
        t = i / h * 2 - 1                       # −1 top … 1 bottom
        x = bulge * (1 - t * t) - (0.8 if abs(t) > 0.85 else 0) * bulge * 0.3
        y = t * h / 2
        if rot:
            x, y = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        pts.append((cx + x, cy + y))
    return pts

POSE_PHASES = [  # name, base frame, ms, draw, arrow, snap   (draw = how far the string is pulled, 0 … 1)
    ("ready", 0, 140, 0.0, False, 0), ("nock", 1, 110, 0.15, True, 0), ("draw", 2, 110, 0.6, True, 0),
    ("full", 2, 280, 1.0, True, 0), ("release", 2, 90, 0.0, False, 1), ("follow", 2, 130, 0.0, False, 2),
    ("recover", 7, 160, 0.0, False, 0)]
FRONT_BACK_POSES = [0, 1, 2, 2, 3, 6, 7]   # base frames for the front / back views (original arms kept)
TORSO = 3                    # half width of the torso column in the side view; arm pixels outside it are re-drawn


def skin_tones(body):
    """(outline, shade, light) of the base skin, from the frame's most common body colours."""
    cnt = {}
    for p in doll._pixels(body):
        if p[3]:
            cnt[p] = cnt.get(p, 0) + 1
    top = sorted(sorted(cnt, key=cnt.get, reverse=True)[:5], key=doll.lum)
    if len(top) < 3:
        return OUT, SKIN, SKIN
    return top[0], top[-2], top[-1]


def thick(p0, p1):
    """2-px wide limb between two points."""
    pts = line(p0, p1)
    horiz = abs(p1[0] - p0[0]) >= abs(p1[1] - p0[1])
    return pts | {(x, y + 1) if horiz else (x + 1, y) for x, y in pts}


def strip_arms(body, bi, top=2):
    """Remove the pose's own arms (everything outside the torso column above the hips) from a dressed body layer."""
    out = body.copy()
    p = out.load()
    cx = bi["cx"]
    for y in range(bi["y0"], bi["waist"] + top):
        for x in range(64):
            if p[x, y][3] and abs(x + .5 - cx) > TORSO + .5:
                p[x, y] = (0, 0, 0, 0)
    return out


def arm(img, pts, tones, hand):
    """Paint a limb (outlined, lit on top) with a 2×2 hand at its end."""
    o, sh, li = tones
    put(img, pts, sh, outline=True)
    ys = {}
    for x, y in pts:
        ys[x] = min(ys.get(x, 99), y)
    put(img, {(x, y) for x, y in ys.items()}, li)
    put(img, {hand, (hand[0], hand[1] + 1)}, li)
    put(img, {(hand[0] + 1, hand[1] + 1)}, sh)


def lerp(a, b, t):
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t))


def side_shot(g, body_raw, head_raw, d, draw, arrow, snap, tones):
    """Side view with re-drawn arms: the bow arm reaches forward to the grip at eye height and the draw hand holds the
    string — the string's pull point IS the hand, so they move together (nock → anchor at the cheek → release)."""
    sgn = 1 if d == "side_right" else -1
    bi, hi = equip.body_info(body_raw), equip.head_info(head_raw)
    cx = int(round(bi["cx"] - .5))
    ay = max(hi["y1"], bi["y0"] + 1) if hi else bi["y0"] + 1                  # arrow / anchor height: under the chin
    hcx = int(round((hi["x0"] + hi["x1"]) / 2)) if hi else cx
    sh_near, sh_far = (cx - sgn, bi["y0"] + 1), (cx + sgn, bi["y0"] + 1)
    grip = (cx + sgn * (TORSO + 7), ay)
    anchor = (hcx, ay)                                                         # under the jaw
    rest = (grip[0] - sgn, ay)
    if snap == 1:
        hand = (anchor[0] - sgn * 2, ay - 1)                                   # fingers open, hand jumps back
    elif snap == 2:
        hand = (anchor[0] - sgn * 3, ay)
    else:
        hand = lerp(rest, anchor, draw)
    back, front = Image.new("RGBA", (64, 64)), Image.new("RGBA", (64, 64))
    g = dict(g)
    g["body"] = strip_arms(g["body"], bi)
    # bow arm: straight from the far (facing right) / near (facing left) shoulder to the grip
    bow_layer = back if sgn > 0 else front
    draw_layer = front if sgn > 0 else back
    arm(bow_layer, thick(sh_far if sgn > 0 else sh_near, grip), tones, (grip[0] - (1 if sgn < 0 else 0), grip[1]))
    # draw arm: shoulder → elbow (pulled back level with the arrow at full draw) → hand on the string
    mid = ((sh_near[0] + hand[0]) // 2, max(sh_near[1], hand[1]) + 2)
    elbow = lerp(mid, (sh_near[0] - sgn * 4, ay + 1), min(1.0, draw if not snap else 1.0))
    arm(draw_layer, thick(sh_near, elbow) | thick(elbow, hand), tones, hand)
    # bow
    arc = bow_arc(grip[0], grip[1], 13, 2.6 * sgn)
    pts = {(int(round(x)), int(round(y))) for x, y in arc}
    outer = {(x + sgn, y) for x, y in pts}
    put(bow_layer, pts | outer, WOOD[1], outline=True)
    put(bow_layer, outer, WOOD[2])
    put(bow_layer, {grip, (grip[0], grip[1] + 1)}, tones[2])                   # fist over the grip
    # string: from the tips to the hand while it holds the string, straight (and quivering) once released
    pull = hand if not snap else (rest[0] - (sgn if snap == 1 else 0), ay)
    put(front, line(arc[0], pull) | line(pull, arc[-1]), STRING)
    if arrow:
        tail = (hand[0] - sgn * 2, ay)
        head = (grip[0] + sgn * 5, ay)
        put(front, line(tail, head), SHAFT)
        put(front, {head, (head[0] - sgn, head[1] - 1), (head[0] - sgn, head[1] + 1)}, TIP)
        put(front, {(tail[0], ay - 1), (tail[0] + sgn, ay - 1), (tail[0], ay + 1), (tail[0] + sgn, ay + 1)}, FLETCH)
        put(front, {hand}, tones[2])                                          # fingers over the nock
    if snap == 1:                                                              # arrow already gone: speed lines
        for k, L in ((0, 6), (-2, 3), (2, 3)):
            x0 = grip[0] + sgn * 4
            put(front, line((x0, ay + k), (x0 + sgn * L, ay + k)), (255, 250, 220, 255))
    g["back"] = costume.stack(back, g.get("back"))
    g["front"] = costume.stack(g.get("front"), front)
    return g


def hands(body, dirn):
    """(bow hand, draw hand) for a right-handed archer, from the body layer's extreme pixels at arm height."""
    bi = equip.body_info(body)
    p = body.load()
    y0, y1 = bi["y0"], bi["waist"] + 1
    pts = [(x, y) for y in range(y0, y1) for x in range(64) if p[x, y][3]]
    right = max(pts, key=lambda q: (q[0], -q[1]))
    left = min(pts, key=lambda q: (q[0], q[1]))
    if dirn == "side_right":
        return right, left          # bow forward (right), draw hand back
    if dirn == "side_left":
        return left, right
    if dirn == "front":
        return right, left          # facing us: right-handed archer holds the bow in his left hand = screen right
    return left, right              # back: character's left hand is on screen left


def shoot(sex, outfit, dirs=None):
    """Bow attack synthesised on the Sword_Attack body poses → ({direction: [ {group: image} ]}, durations)."""
    act = "Sword_Attack"
    o = dict(outfit or {}); o["weapon"] = "none"
    dressed = costume.compose(sex, act, o) if outfit else costume.compose_base(sex, act)
    if not outfit:   # plain base: hide its sword
        for d in dressed.values():
            for g in d:
                g["back"] = g["front"] = None
    raw = doll.layer_sheets(sex, act)
    head_l = raw["head"]
    tones = skin_tones(raw["body"].crop((0, 0, 64, 64)))
    frames = {}
    for r, d in enumerate(DIRS):
        if dirs and d not in dirs:
            continue
        fr = []
        for i, (name, k, ms, draw, arrow, snap) in enumerate(POSE_PHASES):
            if d in ("front", "back"):
                k = FRONT_BACK_POSES[i]
            box = (k * 64, r * 64, k * 64 + 64, r * 64 + 64)
            body = raw["body"].crop(box)
            hi = equip.head_info(head_l.crop(box))
            bowh, drawh = hands(body, d)
            back, front = Image.new("RGBA", (64, 64)), Image.new("RGBA", (64, 64))
            if d in ("side_right", "side_left") and (arrow or snap):
                fr.append(side_shot(dressed[d][k], body, head_l.crop(box), d, draw, arrow, snap, tones))
                continue
            if d in ("side_right", "side_left"):
                sgn = 1 if d == "side_right" else -1
                anchor = (int(hi["ex1"] if sgn > 0 else hi["ex0"]) - sgn * 2, hi.get("eb", bowh[1]) + 2) if hi and "ex0" in hi else drawh
                lift = 1.0 if (draw > 0 or snap) else (0.5 if arrow else 0.0)      # raise the bow to the eye line to aim
                grip = (bowh[0] + sgn * (1 + (2 if lift == 1.0 else 0)), round(bowh[1] + (anchor[1] - bowh[1]) * lift))
                arc = bow_arc(grip[0], grip[1], 13, 2.6 * sgn)
                pull0 = (grip[0] - sgn * 1, grip[1])
                pull = (round(pull0[0] + (anchor[0] - pull0[0]) * draw) + (sgn if snap else 0),
                        round(pull0[1] + (anchor[1] - pull0[1]) * draw))
                pts = {(int(round(x)), int(round(y))) for x, y in arc}
                outer = {(x + sgn, y) for x, y in pts}
                bowimg = back if d == "side_right" else front          # bow hand is the far hand when facing right
                put(bowimg, pts | outer, WOOD[1], outline=True)
                put(bowimg, outer, WOOD[2])
                if d == "side_left":
                    put(front, {grip, (grip[0], grip[1] + 1)}, SKIN)
                put(front, line(arc[0], pull) | line(pull, arc[-1]), STRING)
                if arrow:
                    tail = (pull[0] - sgn * 2, pull[1])
                    head = (grip[0] + sgn * 5, pull[1])
                    put(front, line(tail, head), SHAFT)
                    put(front, {head, (head[0] - sgn, head[1] - 1), (head[0] - sgn, head[1] + 1)}, TIP)
                    put(front, {(tail[0], tail[1] - 1), (tail[0] + sgn, tail[1] - 1), (tail[0], tail[1] + 1), (tail[0] + sgn, tail[1] + 1)}, FLETCH)
                    put(front, {pull}, SKIN)
                if snap:
                    put(front, {(grip[0] + sgn * 3, grip[1] - 1), (grip[0] + sgn * 4, grip[1]), (grip[0] + sgn * 3, grip[1] + 1)}, (255, 250, 220, 255))
            elif d == "front":
                # bow faces the viewer: limbs vertical in front of the chest, tips curling towards us,
                # arrow pointing straight out of the screen (arrowhead on the grip), string hidden behind the bow
                cxb = equip.body_info(body)["cx"]
                lift = 1.0 if (draw > 0 or snap) else (0.5 if arrow else 0.0)
                ey = (hi["y1"] + 2) if hi else bowh[1]                         # chest height, just under the chin
                gx = int(round(bowh[0] + (cxb + 6 - bowh[0]) * (0.4 + 0.6 * lift)))
                gy = int(round(bowh[1] + (ey - bowh[1]) * lift))
                limb = [(gx - (1 if abs(t) > 5 else 0), gy + t) for t in range(-7, 8)]
                pts = set(limb)
                put(front, pts | {(x - 1, y) for x, y in pts}, WOOD[1], outline=True)
                put(front, {(x - 1, y) for x, y in pts}, WOOD[2])
                for ty in (gy - 7, gy + 7):                                   # tips curl towards the viewer
                    put(front, {(gx + 1, ty)}, WOOD[2])
                put(front, {(gx, gy), (gx - 1, gy)}, SKIN)                       # grip hand
                if arrow:
                    size = 1 + int(draw * 1.5)
                    tip = {(gx - 2, gy)} | ({(gx - 2, gy - 1), (gx - 2, gy + 1), (gx - 3, gy)} if size > 1 else set())
                    put(front, tip, TIP, outline=True)
                if snap == 1:
                    put(front, {(gx - 3, gy - 2), (gx - 4, gy), (gx - 3, gy + 2), (gx - 2, gy - 3), (gx - 2, gy + 3)}, (255, 250, 220, 255))
            else:                                                       # back: everything behind the body, no arms
                grip = bowh
                arc = bow_arc(grip[0] - 1, grip[1], 14, -2.2, rot=-0.3)
                pts = {(int(round(x)), int(round(y))) for x, y in arc}
                put(back, pts | {(x - 1, y) for x, y in pts}, WOOD[1], outline=True)
                put(back, {(x - 1, y) for x, y in pts}, WOOD[2])
                pull = (round(grip[0] + 3 + draw * 5), grip[1])
                put(back, line(arc[0], pull) | line(pull, arc[-1]), STRING)
            g = dict(dressed[d][k])
            g["back"] = costume.stack(back, g.get("back"))
            g["front"] = costume.stack(g.get("front"), front)
            fr.append(g)
        frames[d] = fr
    return frames, [p[2] for p in POSE_PHASES]
