"""Synthesised spell cast for the Craftpix base (which has no magic animation). Casters keep the staff upright instead
of swinging it like a sword: ready → channel (a rune circle opens under the feet, motes gather at the staff head) →
raise the staff (head glows) → release (burst, a bolt flies forward in the side views) → follow-through → recover.

The body uses Sword_Attack poses that read as casting (rest, wind-up, staff raised overhead, staff thrust forward,
recover); the staff is re-drawn from the hand (the sword hilt) each frame. Characters without a staff cast from the
open hand. Mage and priest use this for their attack (see presets.ATTACK)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from . import costume, doll, equip
from .base import DIRS, FEET

OUT = equip.OUT
# name, base frame, ms, circle (0…1), gather (motes 0…1, -1 = none), glow (staff head 0…2), tilt (0 upright, 1 forward), burst
PHASES = [("ready", 0, 140, 0.0, -1, 0, 0.0, 0), ("channel", 1, 120, 0.5, 0.0, 1, 0.0, 0),
          ("channel2", 1, 120, 1.0, 0.5, 1, 0.0, 0), ("raise", 5, 170, 1.0, 1.0, 2, 0.0, 0),
          ("release", 6, 100, 1.0, -1, 2, 1.0, 1), ("follow", 6, 130, 0.5, -1, 1, 1.0, 2),
          ("recover", 7, 160, 0.0, -1, 0, 0.0, 0)]
FRONT_BACK_POSES = [0, 1, 1, 5, 5, 5, 7]     # front / back: release with the staff held high (the thrust reads badly)


def ramp(name):
    return [equip.hx(c) for c in equip.RAMPS[name]]


def _put(img, pts, col):
    """Plot points, keeping a 1-px margin: effects never touch the canvas edge (QA treats that as a crop)."""
    p = img.load()
    for x, y in pts:
        x, y = int(round(x)), int(round(y))
        if 1 <= x < img.width - 1 and 1 <= y < img.height - 1:
            p[x, y] = col


def hand_from_sword(sf, sb, body):
    """(hilt point, layer index 0 = front / 1 = back) from the pack's sword layers; None if there is no sword."""
    pts = []
    for img in (sf, sb):
        if img is None:
            continue
        a = np.asarray(img)
        ys, xs = np.nonzero(a[..., 3])
        pts += list(zip(xs, ys))
    if len(pts) < 6:
        return None
    P = np.array(pts, float)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c)
    t = (P - c) @ vt[0]
    bb = body.getbbox()
    bc = np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]) if bb else c
    e1, e2 = c + vt[0] * t.min(), c + vt[0] * t.max()
    hilt = e1 if np.linalg.norm(e1 - bc) < np.linalg.norm(e2 - bc) else e2
    hilt = hilt + (bc - hilt) / (np.linalg.norm(bc - hilt) or 1) * 1.5     # the fist sits a little inside the guard
    layer = 0 if (sf is not None and sf.getbbox()) else 1
    return (float(hilt[0]), float(hilt[1])), layer


def draw_skull(img, hc, glow):
    """Small skull staff head centred on hc, eye sockets glowing in the `glow` ramp."""
    p = img.load()
    G = ramp(glow)
    B = ramp("bone")
    cx, cy = int(hc[0]), int(hc[1])
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 2, cx + 3):
            if abs(x - cx) + abs(y - cy) <= 3 and (y < cy + 2 or abs(x - cx) <= 1):
                _put(img, [(x, y)], B[4] if y < cy else B[3])
    for x in range(cx - 3, cx + 4):
        for y in range(cy - 3, cy + 4):
            if 0 <= x < 64 and 0 <= y < 64 and p[x, y][3] == 0 and any(
                    0 <= x + a < 64 and 0 <= y + b < 64 and p[x + a, y + b][:3] in (B[4][:3], B[3][:3])
                    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                p[x, y] = OUT
    _put(img, [(cx - 1, cy), (cx + 1, cy)], G[4])                      # glowing eye sockets
    _put(img, [(cx, cy + 2)], B[1])


def draw_staff(img, hand, d, wood, orb, head, lit=0):
    """Staff through the hand along unit vector d (towards the head); returns the head centre."""
    W, G = ramp(wood), ramp(orb)
    n = (-d[1], d[0])
    for k in range(-5, 15):
        q = (hand[0] + d[0] * k, hand[1] + d[1] * k)
        _put(img, [q], W[4 if k % 4 else 2])
        _put(img, [(q[0] + n[0], q[1] + n[1])], W[1])
    hc = (hand[0] + d[0] * 17, hand[1] + d[1] * 17)
    p = img.load()
    if head == "orb":
        for y in range(int(hc[1]) - 3, int(hc[1]) + 4):
            for x in range(int(hc[0]) - 3, int(hc[0]) + 4):
                r = math.hypot(x + .5 - hc[0], y + .5 - hc[1])
                if 0 <= x < 64 and 0 <= y < 64 and r <= 2.6:
                    if lit:                                        # charged: the orb itself shines
                        p[x, y] = G[2] if r > 1.9 else (G[5] if r < 1.2 or lit > 1 else G[4])
                    else:
                        p[x, y] = OUT if r > 1.9 else (G[5] if (x < hc[0] and y < hc[1]) else G[3])
    elif head == "skull":
        draw_skull(img, hc, orb)
    else:                                                                  # holy cross
        cx, cy = int(hc[0]), int(hc[1])
        _put(img, [(cx, cy + k) for k in range(-3, 3)] + [(cx + k, cy - 1) for k in (-2, -1, 1, 2)], G[4])
        _put(img, [(cx, cy - 4), (cx - 3, cy - 1), (cx + 3, cy - 1), (cx, cy + 3)], OUT)
    return hc


def rune_circle(level, col):
    """Ellipse under the feet with rune ticks; level 0…1 grows it open."""
    img = Image.new("RGBA", (64, 64))
    if level <= 0:
        return img
    C = ramp(col)
    fx, fy = FEET
    rx, ry = 6 + 6 * level, 2 + 2 * level
    pts = set()
    for i in range(160):
        a = i / 160 * 2 * math.pi
        pts.add((int(round(fx + rx * math.cos(a))), int(round(fy + ry * math.sin(a)))))
    _put(img, pts, C[3])
    if level >= 1:
        inner = {(int(round(fx + (rx - 3) * math.cos(i / 80 * 2 * math.pi))),
                  int(round(fy + (ry - 1.2) * math.sin(i / 80 * 2 * math.pi)))) for i in range(80)}
        _put(img, inner, C[2])
        for k in range(6):                                                 # rune ticks between the rings
            a = k / 6 * 2 * math.pi + .3
            _put(img, [(fx + (rx - 1.5) * math.cos(a), fy + (ry - .6) * math.sin(a))], C[5])
    return img


def motes(hc, t, col, phase):
    """Particles spiralling in towards the staff head (t 0 → 1 = far → close)."""
    img = Image.new("RGBA", (64, 64))
    C = ramp(col)
    r = 9 - 5 * t
    for k in range(5):
        a = k / 5 * 2 * math.pi + phase * 0.9
        x, y = hc[0] + r * math.cos(a), hc[1] + r * 0.8 * math.sin(a)
        _put(img, [(x, y)], C[5] if k % 2 else C[4])
        if t < 1:
            _put(img, [(x - math.cos(a), y - 0.8 * math.sin(a))], C[2])
    return img


def glow(hc, level, col):
    img = Image.new("RGBA", (64, 64))
    if level <= 0:
        return img
    C = ramp(col)
    R = 3.6 if level == 1 else 4.6
    p = img.load()
    for y in range(int(hc[1] - 5), int(hc[1] + 6)):
        for x in range(int(hc[0] - 5), int(hc[0] + 6)):
            r = math.hypot(x + .5 - hc[0], y + .5 - hc[1])
            if 0 <= x < 64 and 0 <= y < 64 and 2.6 < r <= R and (x + y) % (1 if level > 1 else 2) == 0:
                p[x, y] = C[4] if r < 3.8 else C[3]
    return img


def burst(hc, kind, col, fwd):
    """Release: star burst at the staff head (+ a bolt flying forward in the side views); kind 2 = fading ring."""
    img = Image.new("RGBA", (64, 64))
    C = ramp(col)
    cx, cy = int(round(hc[0])), int(round(hc[1]))
    if kind == 1:
        for k in range(1, 5):
            _put(img, [(cx + k, cy), (cx - k, cy), (cx, cy + k), (cx, cy - k)], C[5] if k < 3 else C[4])
        for k in (1, 2):
            _put(img, [(cx + k, cy + k), (cx - k, cy - k), (cx + k, cy - k), (cx - k, cy + k)], C[4])
        if fwd:
            bx = cx + fwd * 7
            _put(img, [(bx + fwd * k, cy) for k in range(-1, 3)], C[5])
            _put(img, [(bx + fwd * k, cy + s) for k in range(-1, 2) for s in (-1, 1)], C[4])
            _put(img, [(bx - fwd * k, cy) for k in range(2, 6)], C[3])
    else:
        ring = {(int(round(cx + 5 * math.cos(a / 24 * 2 * math.pi))), int(round(cy + 5 * math.sin(a / 24 * 2 * math.pi))))
                for a in range(24)}
        _put(img, [q for i, q in enumerate(sorted(ring)) if i % 2 == 0], C[3])
        if fwd:
            bx = cx + fwd * 13
            _put(img, [(bx + fwd * k, cy) for k in range(-1, 3)], C[5])
            _put(img, [(bx + fwd * k, cy + s) for k in range(0, 2) for s in (-1, 1)], C[4])
            _put(img, [(bx - fwd * k, cy) for k in range(2, 7)], C[3])
    return img


def magic_colour(outfit) -> str:
    o = outfit or {}
    if o.get("magic"):
        return o["magic"]
    w = o.get("weapon")
    if isinstance(w, (tuple, list)) and w[0] == "staff":
        return w[2]
    return "blue"


def cast(sex, outfit, dirs=None):
    """→ ({direction: [ {group: image} ]}, durations)."""
    act = "Sword_Attack"
    w = (outfit or {}).get("weapon")
    staff = w if isinstance(w, (tuple, list)) and w[0] == "staff" else None
    col = magic_colour(outfit)
    if outfit:
        o = dict(outfit); o["weapon"] = "none"
        dressed = costume.compose(sex, act, o)
    else:
        dressed = costume.compose_base(sex, act)
        for d in dressed.values():
            for g in d:
                g["back"] = g["front"] = None
    raw = doll.layer_sheets(sex, act)
    frames = {}
    for r, d in enumerate(DIRS):
        if dirs and d not in dirs:
            continue
        fwd = {"side_right": 1, "side_left": -1}.get(d, 0)
        fr = []
        for i, (name, k, ms, circle, gather, gl, tilt, bst) in enumerate(PHASES):
            if not fwd:
                k = FRONT_BACK_POSES[i]
            box = (k * 64, r * 64, k * 64 + 64, r * 64 + 64)
            crop = {n: raw[n].crop(box) for n in ("body", "sword_front", "sword_back") if n in raw}
            found = hand_from_sword(crop.get("sword_front"), crop.get("sword_back"), crop["body"])
            g = dict(dressed[d][k])
            if found is None:
                fr.append(g); continue
            hand, layer = found
            if fwd:
                lean = 0.35 * fwd                          # head of the staff ahead of the face
            else:                                     # front / back: lean the staff outwards, clear of the hat
                bb = crop["body"].getbbox()
                side = 1 if hand[0] >= (bb[0] + bb[2]) / 2 else -1
                lean = 0.4 * side
            dx, dy = lean + fwd * tilt * 0.9, -1.0
            nrm = math.hypot(dx, dy)
            dvec = (dx / nrm, dy / nrm)
            weapon = Image.new("RGBA", (64, 64))
            if staff:
                hc = draw_staff(weapon, hand, dvec, staff[1], staff[2], staff[3], gl)
            else:
                hc = (hand[0] + dvec[0] * 2, hand[1] + dvec[1] * 2)          # open hand
                if gl:
                    _put(weapon, [hc], ramp(col)[5])
            fx = costume.stack(glow(hc, gl, col),
                               motes(hc, gather, col, i) if gather >= 0 else None,
                               burst(hc, bst, col, fwd) if bst else None)
            if layer == 0:
                g["front"] = costume.stack(g.get("front"), weapon, fx)
            else:
                g["back"] = costume.stack(weapon, g.get("back"))
                g["front"] = costume.stack(g.get("front"), fx)
            g["shadow"] = costume.stack(g.get("shadow"), rune_circle(circle, col))
            fr.append(g)
        frames[d] = fr
    return frames, [p[2] for p in PHASES]
