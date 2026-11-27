"""Fantasy RPG costume pieces drawn per frame on top of the Craftpix base (Tiny RPG look: chunky shapes, steel
helmets with a rim, cloth tabards, leather belts, capes, robes, wizard hats, hoods) — all positioned from that
frame's own head / body layers, so they follow every animation and facing."""
import math

from PIL import Image

from . import doll

RAMPS = dict(doll.RAMPS)
RAMPS.update({
    "steel": ["#1a1e2a", "#3c4656", "#5a6878", "#7c8c9c", "#a4b4c2", "#d8e2ea"],
    "leather": ["#1e1008", "#3e2412", "#5e3a1c", "#7e5228", "#a06c38", "#c48c50"],
    "fur": ["#2a1a10", "#4e3424", "#6e4c34", "#8e6a4a", "#b08c66", "#d4b48c"],
    "bone": ["#3a3024", "#6e6046", "#9e8e6e", "#c8b894", "#e6dabc", "#fffaf0"],
    "darkgreen": ["#0a1a0e", "#14301a", "#1e4626", "#2a5c32", "#3c7a40", "#5c9a52"],
    "crimson": ["#1e0608", "#420c12", "#6e141e", "#9a1e28", "#c4303a", "#e8605a"],
})
OUT = (16, 10, 18, 255)
EYE = doll.EYE

def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)

def head_info(head):
    hp = head.load()
    mask = {(x, y) for y in range(head.height) for x in range(head.width) if hp[x, y][3]}
    if not mask:
        return None
    xs = [p[0] for p in mask]; ys = [p[1] for p in mask]
    eyes = [(x, y) for (x, y) in mask if hp[x, y][:3] in EYE]
    info = {"mask": mask, "x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)}
    if eyes:
        info["et"] = min(e[1] for e in eyes)
        info["eb"] = max(e[1] for e in eyes)
        info["ex0"] = min(e[0] for e in eyes); info["ex1"] = max(e[0] for e in eyes)
    return info

def body_info(body):
    bb = body.getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    px = body.load()
    H = y1 - y0
    waist = y0 + int(H * 0.5)
    row = [x for x in range(body.width) if px[x, waist][3]]
    cx = (min(row) + max(row)) / 2 if row else (x0 + x1) / 2
    tw = (max(row) - min(row)) / 2 if row else 3
    mask = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if px[x, y][3]}
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "waist": waist, "cx": cx, "tw": tw, "feet": y1 - 2, "mask": mask}

def paint(img, pts, ramp, base=None, light=(-1, -1), outline=True, flat=None, keep=None):
    """Shade a point set: tone from position (lit top-left), 1-px dark outline on its edge."""
    R = [hx(c) for c in RAMPS[ramp]]
    p = img.load()
    if not pts:
        return
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for (x, y) in pts:
        if not (0 <= x < img.width and 0 <= y < img.height):
            continue
        edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge and outline:
            p[x, y] = OUT if outline is True else R[0]
            continue
        if flat is not None:
            p[x, y] = R[flat]
            continue
        u = (x - x0) / max(1, x1 - x0)
        v = (y - y0) / max(1, y1 - y0)
        lit = 1 - (0.45 * u + 0.55 * v)
        right_edge = (x + 1, y) not in pts or (x, y + 1) not in pts
        t = 4 if lit > 0.72 else (3 if lit > 0.45 else 2)
        if (x - 1, y) not in pts or (x, y - 1) not in pts:
            t = min(5, t + 1)
        p[x, y] = R[t]

def grow(pts, n=1, cond=None):
    out = set(pts)
    for _ in range(n):
        add = set()
        for (x, y) in out:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in out and (cond is None or cond(q)):
                    add.add(q)
        out |= add
    return out

# ------------------------------------------------------------------ headgear
def headgear(hi, style, dirn, ramp, accent="gold"):
    """Returns list of (points, ramp, kwargs) to paint over the head (after hair)."""
    if hi is None or style is None:
        return []
    m, x0, x1, y0, y1 = hi["mask"], hi["x0"], hi["x1"], hi["y0"], hi["y1"]
    hw, hh = x1 - x0 + 1, y1 - y0 + 1
    cx = (x0 + x1) / 2
    face = "et" in hi and dirn != "back"
    et = hi.get("et", y1 - 3)
    pieces = []
    if style in ("helm", "horned"):
        cover = set()
        for (x, y) in m:
            if y < et - 1 if face else y < y1 - 1:
                cover.add((x, y))
            if face and dirn == "side_left" and x > hi["ex1"] + 2 and y < y1 - 1:
                cover.add((x, y))
            if face and dirn == "side_right" and x < hi["ex0"] - 2 and y < y1 - 1:
                cover.add((x, y))
            if face and dirn == "front" and (x <= x0 + 1 or x >= x1 - 1) and y < et + 4:
                cover.add((x, y))                                      # cheek guards
        cover = grow(cover, 1, cond=lambda q: q not in m and q[1] < y0 + hh * 0.75)
        pieces.append((cover, ramp, {}))
        rim_y = et - 1 if face else y1 - 2
        rim = {(x, rim_y) for x in range(min(p[0] for p in cover) , max(p[0] for p in cover) + 1) if (x, rim_y) in cover or (x, rim_y - 1) in cover}
        rim |= {(x, rim_y - 1) for (x, _) in rim}
        pieces.append((rim, ramp, {"flat": 1}))
        if face and dirn == "front":
            nx = int(round((hi["ex0"] + hi["ex1"]) / 2))
            pieces.append(({(nx, et - 1), (nx, et), (nx, et + 1), (nx, et + 2)}, ramp, {"flat": 3, "outline": False}))
        crest = {(int(cx), y) for y in range(y0 - 1, rim_y - 1)} if dirn in ("front", "back") else set()
        if crest:
            pieces.append((crest, ramp, {"flat": 5, "outline": False}))
        if style == "horned":
            for sgn in (-1, 1):
                bx = (min(p[0] for p in cover) - 1) if sgn < 0 else (max(p[0] for p in cover) + 1)
                by = rim_y - 3
                horn = set()
                path = [(0, 0), (1, 0), (2, -1), (3, -2), (3, -3), (3, -4), (2, -5)]
                for i, (dx, dy) in enumerate(path):
                    x, y = bx + sgn * dx, by + dy
                    horn.add((x, y))
                    if i < 4:
                        horn.add((x, y + 1))
                pieces.append((grow(horn, 1), "bone", {}))
    elif style in ("hood", "cowl"):
        cover = set()
        for (x, y) in m:
            if face:
                if dirn == "front" and hi["ex0"] - 1 <= x <= hi["ex1"] + 1 and y >= et - 1:
                    continue
                if dirn == "side_left" and x <= hi["ex1"] + 1 and y >= et - 1:
                    continue
                if dirn == "side_right" and x >= hi["ex0"] - 1 and y >= et - 1:
                    continue
            cover.add((x, y))
        cover = grow(cover, 1, cond=lambda q: q not in m)
        # drape over the shoulders
        for x in range(x0 - 1, x1 + 2):
            for y in range(y1, y1 + 3):
                if not (face and dirn == "front" and hi["ex0"] - 1 <= x <= hi["ex1"] + 1 and y < y1 + 1):
                    cover.add((x, y))
        if dirn in ("side_left", "side_right"):                       # pointed tail at the back
            sgn = 1 if dirn == "side_left" else -1
            bx = x1 + 1 if sgn > 0 else x0 - 1
            for k in range(4):
                for y in range(y0 + 2 + k, y0 + 5 + k):
                    cover.add((bx + sgn * (1 + k // 2), y))
        if dirn == "back":
            for k in range(3):
                cover.add((int(cx), y1 + 3 + k)); cover.add((int(cx) + 1, y1 + 3 + k - 1))
        pieces.append((cover, ramp, {}))
    elif style == "wizard":
        brim_y = (et - 2) if face else y0 + 3
        under = {(x, y) for (x, y) in m if y < brim_y}
        pieces.append((grow(under, 1, cond=lambda q: q not in m), ramp, {}))
        if dirn in ("front", "back"):
            brim = {(x, y) for x in range(x0 - 3, x1 + 4) for y in (brim_y, brim_y + 1)}
        else:
            sgn = 1 if dirn == "side_left" else -1
            brim = {(x, y) for x in range(x0 - 3, x1 + 4) for y in (brim_y, brim_y + 1)}
        cone = set()
        top = brim_y - 12
        lean = {"front": 1, "back": -1, "side_left": 1, "side_right": -1}[dirn]
        for k in range(12):
            y = brim_y - 1 - k
            half = (hw / 2 + 0.5) * (1 - k / 12) ** 0.9
            ccx = cx + lean * (k / 12) ** 2 * 5
            for x in range(int(ccx - half), int(ccx + half) + 1):
                cone.add((x, y))
        pieces.append((cone, ramp, {}))
        band = {(x, brim_y - 1) for x in range(x0 - 1, x1 + 2) if (x, brim_y - 1) in cone}
        band |= {(x, brim_y - 2) for (x, _) in band}
        pieces.append((band, accent, {"flat": 4, "outline": False}))
        pieces.append((brim, ramp, {}))
    elif style == "circlet":
        yb = (et - 2) if face else y0 + 4
        band = {(x, yb) for x in range(x0, x1 + 1) if (x, yb) in m or (x, yb - 1) in m}
        pieces.append((band, accent, {"flat": 4, "outline": False}))
        if face and dirn == "front":
            gx = int(round((hi["ex0"] + hi["ex1"]) / 2))
            pieces.append(({(gx, yb - 1), (gx, yb)}, "red", {"flat": 4, "outline": False}))
    return pieces

# ------------------------------------------------------------------ body pieces
def torso_pts(bi, dirn):
    pts = set()
    for (x, y) in bi["mask"]:
        if y < bi["waist"] and abs(x + .5 - bi["cx"]) <= bi["tw"] + (0 if dirn in ("front", "back") else 1):
            pts.add((x, y))
    return pts

def body_pieces(bi, outfit, dirn, fi):
    if bi is None:
        return [], [], []
    under, over, top = [], [], []      # under = behind body, over = on body, top = after head (back-view cape)
    cx, tw, y0, waist, feet = bi["cx"], bi["tw"], bi["y0"], bi["waist"], bi["feet"]
    T = torso_pts(bi, dirn)
    arm = outfit.get("armor")
    if arm in ("plate", "leather", "fur"):
        ramp = {"plate": "steel", "leather": "leather", "fur": "leather"}[arm]
        over.append((T, ramp, {"outline": "ramp"}))
        if arm in ("plate", "fur"):                                   # pauldrons
            pr = "steel" if arm == "plate" else "fur"
            ys = y0 + 1
            if dirn in ("front", "back"):
                for sx in (int(cx - tw - 1), int(cx + tw)):
                    over.append(({(sx + dx, ys + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} | {(sx, ys + 2)}, pr, {}))
            else:
                sx = int(cx)
                over.append(({(sx + dx, ys + dy) for dx in (-2, -1, 0, 1, 2) for dy in (-1, 0, 1)}, pr, {}))
    tab = outfit.get("tabard")
    if tab and dirn in ("front", "back"):
        strip = {(x, y) for x in range(int(cx) - 1, int(cx) + 2) for y in range(y0 + 2, waist + 4)}
        over.append((strip, tab, {"outline": "ramp"}))
    if outfit.get("robe"):
        robe = set()
        for (x, y) in bi["mask"]:
            if waist - 1 <= y < feet:
                robe.add((x, y))
        rows = {}
        for (x, y) in robe:
            rows.setdefault(y, []).append(x)
        for y, xs in rows.items():
            flare = 1 + (y - waist) // 3
            for x in range(min(xs) - flare, max(xs) + flare + 1):
                robe.add((x, y))
        robe |= T
        over.append((robe, outfit["robe"], {}))
        trim = outfit.get("trim", "gold")
        hem = {(x, y) for (x, y) in robe if y == feet - 1}
        over.append((hem, trim, {"flat": 4, "outline": False}))
        if dirn in ("front", "back"):
            over.append(({(int(cx), y) for y in range(y0 + 2, feet - 1)}, trim, {"flat": 3, "outline": False}))
    if outfit.get("belt", True) and (arm or outfit.get("robe")):
        belt = {(x, waist - 1) for (x, y) in (T | bi["mask"]) if y == waist - 1}
        over.append((belt, "leather", {"flat": 1, "outline": False}))
        if dirn in ("front", "back"):
            over.append(({(int(cx), waist - 1)}, "gold", {"flat": 4, "outline": False}))
    cape = outfit.get("cape")
    if cape:
        sway = (fi % 4 in (1, 2)) * 1
        pts = set()
        if dirn == "front":
            for y in range(y0, feet):
                t = (y - y0) / max(1, feet - y0)
                half = tw + 1 + t * 3
                for x in range(int(cx - half), int(cx + half) + 1):
                    pts.add((x, y))
            under.append((pts, cape, {}))
        elif dirn == "back":
            for y in range(y0, feet + 1):
                t = (y - y0) / max(1, feet - y0)
                half = tw + 1 + t * 2.5
                for x in range(int(cx - half), int(cx + half) + 1):
                    pts.add((x, y))
            top.append((pts, cape, {}))
            fold = {(int(cx - 1), y) for y in range(y0 + 3, feet - 1)} | {(int(cx + 2), y) for y in range(y0 + 5, feet - 1)}
            top.append((fold, cape, {"flat": 1, "outline": False}))
        else:
            sgn = 1 if dirn == "side_left" else -1                    # cape trails behind
            bx = cx + sgn * (tw - 1)
            for y in range(y0, feet):
                t = (y - y0) / max(1, feet - y0)
                w = 2 + t * (4 + sway)
                for k in range(int(w) + 1):
                    pts.add((int(bx + sgn * k), y))
            under.append((pts, cape, {}))
    return under, over, top

# ------------------------------------------------------------------ staff weapon
def staff_from_sword(front, back, body, wood="brown", orb="blue", head="orb"):
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
    _, _, vt = np.linalg.svd(P - c)
    ax = vt[0]
    t = (P - c) @ ax
    bb = body.getbbox()
    bc = np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]) if bb else c
    e1, e2 = c + ax * t.min(), c + ax * t.max()
    tip, hilt = (e1, e2) if np.linalg.norm(e1 - bc) > np.linalg.norm(e2 - bc) else (e2, e1)
    W = [hx(x) for x in RAMPS[wood]]
    d = (tip - hilt) / (np.linalg.norm(tip - hilt) or 1)
    if d[1] > -0.2:                                   # sword pointing down/sideways → hold the staff upright-ish
        d = np.array([d[0] * 0.5, -1.0])
        d /= np.linalg.norm(d)
    tgt = 0 if front.getbbox() else 1
    outs = [Image.new("RGBA", front.size), Image.new("RGBA", back.size)]
    o = outs[tgt]
    po = o.load()
    for k in range(-5, 15):
        q = hilt + d * k
        n = np.array([-d[1], d[0]])
        for w, tone in ((0, 3), (1, 1)):
            r = q + n * w
            if 0 <= r[0] < 64 and 0 <= r[1] < 64:
                po[int(r[0]), int(r[1])] = W[tone] if w else W[4 if k % 4 else 2]
    hc = hilt + d * 17
    G = [hx(x) for x in RAMPS[orb]]
    if head == "orb":
        for y in range(int(hc[1]) - 3, int(hc[1]) + 4):
            for x in range(int(hc[0]) - 3, int(hc[0]) + 4):
                r = math.hypot(x + .5 - hc[0], y + .5 - hc[1])
                if 0 <= x < 64 and 0 <= y < 64 and r <= 2.6:
                    po[x, y] = OUT if r > 1.9 else (G[5] if (x < hc[0] and y < hc[1]) else G[3])
    else:                                                              # holy cross head
        cxh, cyh = int(hc[0]), int(hc[1])
        for (x, y) in [(cxh, cyh + k) for k in range(-3, 3)] + [(cxh + k, cyh - 1) for k in (-2, -1, 1, 2)]:
            if 0 <= x < 64 and 0 <= y < 64:
                po[x, y] = G[4]
        for (x, y) in [(cxh, cyh - 4), (cxh - 3, cyh - 1), (cxh + 3, cyh - 1), (cxh, cyh + 3)]:
            if 0 <= x < 64 and 0 <= y < 64:
                po[x, y] = OUT
    return outs[0], outs[1]
