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

POSE_PHASES = [  # name, base frame, ms, draw, arrow, snap
    ("ready", 0, 140, 0.0, False, 0), ("nock", 1, 110, 0.0, True, 0), ("draw", 2, 110, 0.55, True, 0),
    ("full", 2, 280, 1.0, True, 0), ("release", 3, 90, 0.0, False, 1), ("follow", 6, 130, 0.0, False, 0),
    ("recover", 7, 160, 0.0, False, 0)]

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
    frames = {}
    for r, d in enumerate(DIRS):
        if dirs and d not in dirs:
            continue
        fr = []
        for (name, k, ms, draw, arrow, snap) in POSE_PHASES:
            box = (k * 64, r * 64, k * 64 + 64, r * 64 + 64)
            body = raw["body"].crop(box)
            hi = equip.head_info(head_l.crop(box))
            bowh, drawh = hands(body, d)
            back, front = Image.new("RGBA", (64, 64)), Image.new("RGBA", (64, 64))
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
                if snap:
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
