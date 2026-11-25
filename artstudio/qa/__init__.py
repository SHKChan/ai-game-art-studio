"""Automated quality assurance.

DETERMINISTIC checks (this module) measure pixels and metadata and are reproducible.
They do NOT establish visual consistency, identity or motion quality. Probabilistic,
visual-model-assisted checks live in `visual.py` and are reported separately.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from ..animation import load_frames
from ..processing.frames import alpha_bbox, detect_background, to_np
from ..util import now

SEVERITY = {"error": 2, "warning": 1, "info": 0}


def _issue(code, severity, msg, frame=None, **extra):
    d = {"code": code, "severity": severity, "message": msg}
    if frame is not None:
        d["frame"] = frame
    d.update(extra)
    return d


def check_frames(images: list[Image.Image], durations: list[int] | None = None, *, mode: str = "pixel",
                 pivot=None, source_images: list[Image.Image] | None = None, airborne: list[int] | None = None,
                 jitter_px: float = 3.0, scale_tolerance: float = 0.18, motion_checks: bool = True) -> list[dict]:
    issues = []
    airborne = set(airborne or [])
    if not images:
        return [_issue("no_frames", "error", "Animation has no frames")]
    sizes = {im.size for im in images}
    if len(sizes) > 1:
        issues.append(_issue("inconsistent_canvas", "error", f"Frame canvases differ: {sorted(sizes)}"))
    hashes, bbs = [], []
    for i, im in enumerate(images):
        a = to_np(im)
        al = a[..., 3]
        bb = alpha_bbox(im)
        bbs.append(bb)
        if bb is None or (al > 0).sum() == 0:
            issues.append(_issue("empty_frame", "error", "Frame has no visible pixels", i))
            hashes.append(None)
            continue
        if (al == 255).all():
            issues.append(_issue("no_transparency", "error", "Frame is fully opaque (no transparent background)", i))
        bg = detect_background(im)
        if bg["kind"] in ("solid", "checker"):
            issues.append(_issue("unexpected_background", "error", f"Border looks like a {bg['kind']} background", i, background=bg))
        partial = ((al > 0) & (al < 255)).mean()
        if mode == "pixel" and partial > 0:
            issues.append(_issue("partial_alpha_in_pixel_mode", "warning", f"{partial:.2%} semi-transparent pixels in pixel-art mode", i))
        if mode == "pixel" and ((al == 0) & (a[..., :3].max(-1) > 0)).any():
            issues.append(_issue("dirty_transparent_rgb", "info", "Transparent pixels carry colour data", i))
        w, h = im.size
        if bb[0] == 0 or bb[1] == 0 or bb[2] == w or bb[3] == h:
            issues.append(_issue("clipped_sprite", "error", "Visible pixels touch the canvas edge (possible crop)", i, bbox=list(bb)))
        hashes.append(hashlib.sha1(a.tobytes()).hexdigest())
    for i in range(1, len(hashes)):
        if hashes[i] and hashes[i] == hashes[i - 1]:
            issues.append(_issue("duplicate_frame", "warning", f"Identical to frame {i - 1} (hold? use a longer duration instead)", i))
    if source_images:
        for i, s in enumerate(source_images):
            sb = alpha_bbox(s, 16)
            if sb and (sb[0] == 0 or sb[1] == 0 or sb[2] == s.width or sb[3] == s.height):
                issues.append(_issue("source_clipped", "warning", "Source frame touches its cell edge; content may have been cut in the source", i))
    valid = [(i, b) for i, b in enumerate(bbs) if b]
    if motion_checks and len(valid) >= 3:
        hs = np.array([b[3] - b[1] for _, b in valid], float)
        ws_ = np.array([b[2] - b[0] for _, b in valid], float)
        med_h = np.median(hs)
        for (i, b), hh in zip(valid, hs):
            if med_h > 0 and abs(hh - med_h) / med_h > scale_tolerance * 2.5:
                issues.append(_issue("scale_change", "warning", f"Visible height {hh:.0f}px vs median {med_h:.0f}px (weapon/effect extent or a real scale change — verify visually)", i))
        # Anchor discontinuity / jitter: bottom (ground contact) of grounded frames.
        grounded = [(i, b) for i, b in valid if i not in airborne]
        if pivot is not None and len(grounded) >= 2:
            bottoms = np.array([b[3] for _, b in grounded], float)
            if bottoms.max() - bottoms.min() > jitter_px * 2:
                issues.append(_issue("anchor_discontinuity", "warning",
                                     f"Ground-contact row varies by {bottoms.max() - bottoms.min():.0f}px across grounded frames (mark jump frames airborne if intended)"))
            dev = np.abs(bottoms - pivot[1])
            for (i, _), dv in zip(grounded, dev):
                if dv > jitter_px * 3:
                    issues.append(_issue("off_ground", "info", f"Lowest pixel is {dv:.0f}px from the ground line", i))
        cx = np.array([(b[0] + b[2]) / 2 for _, b in grounded], float) if grounded else np.array([])
        if len(cx) >= 3:
            d2 = np.abs(np.diff(cx, 2))
            for k, v in enumerate(d2):
                if v > jitter_px * 2 + 0.25 * np.median(ws_):
                    issues.append(_issue("positional_jitter", "warning", f"Horizontal centre jumps {v:.1f}px (second difference)", grounded[k + 1][0]))
    if durations is not None:
        if len(durations) != len(images):
            issues.append(_issue("duration_count", "error", "Durations do not match frame count"))
        for i, d in enumerate(durations):
            if not isinstance(d, int) or d <= 0 or d > 60000:
                issues.append(_issue("invalid_duration", "error", f"Invalid duration {d!r}", i))
            elif d % 10:
                issues.append(_issue("gif_timing_rounding", "info", "GIF stores 10ms units; preview timing will round", i))
    return issues


def summarize(issues: list[dict]) -> dict:
    worst = max((SEVERITY[i["severity"]] for i in issues), default=-1)
    status = {2: "failed", 1: "warnings", 0: "passed", -1: "passed"}[worst]
    return {"status": status, "kind": "deterministic", "checked_at": now(), "issues": issues,
            "counts": {s: sum(1 for i in issues if i["severity"] == s) for s in SEVERITY},
            "note": "Deterministic pixel/metadata validation only. Identity, anatomy, style and motion quality need visual review."}


def check_asset(ws, a: dict, save: bool = True) -> dict:
    issues = []
    if "animation" in a:
        pairs = load_frames(ws, a)
        imgs = [im for _, im in pairs]
        durs = [f["duration_ms"] for f, _ in pairs]
        srcs = []
        for f, _ in pairs:
            from ..animation import frame_path
            p = frame_path(ws, a, f, source=True)
            if p.exists():
                with Image.open(p) as s:
                    srcs.append(s.convert("RGBA"))
        anim = a["animation"]
        airborne = [i for i, (f, _) in enumerate(pairs) if f.get("airborne")]
        # Ground/scale/jitter heuristics model a character standing on a ground line; effects and props
        # (fireballs, slashes, opening chests) legitimately move and change extent, so they are skipped.
        motion = a["type"] in ("animation", "character_sprite") and bool(a.get("character_id") or anim.get("direction") not in (None, "none"))
        issues = check_frames(imgs, durs, mode=a["art_style"], pivot=anim["pivot"], source_images=srcs, airborne=airborne, motion_checks=motion)
        n = len(anim["frames"])
        for e in anim.get("events", []):
            if not 0 <= e["frame"] < n:
                issues.append(_issue("invalid_event", "error", f"Event {e['type']} references frame {e['frame']}"))
        px, py = anim["pivot"]
        if not (0 <= px < anim["canvas"][0] and 0 <= py < anim["canvas"][1]):
            issues.append(_issue("pivot_outside_canvas", "error", "Pivot lies outside the canvas"))
    else:
        d = ws.asset_dir(a["project_id"], a["id"])
        files = a["processed_files"] or a["source_files"]
        imgs = []
        for f in files:
            p = d / f["path"]
            if not p.exists():
                issues.append(_issue("missing_file", "error", f"Missing {f['path']}"))
                continue
            if p.suffix.lower() == ".png":
                with Image.open(p) as im:
                    imgs.append(im.convert("RGBA"))
        if imgs:
            issues += check_frames(imgs[:1], None, mode=a["art_style"])
    if a.get("provider", {}).get("is_test_fixture"):
        issues.append(_issue("test_fixture", "warning", "Produced by a mock/test provider; not real AI-generated artwork"))
    result = summarize(issues)
    if save:
        a["qa"]["deterministic"] = result
        ws.save_asset(a)
    return result


def check_character_directions(c: dict) -> list[dict]:
    mirrored = c["mirroring"]["pairs"] if c["mirroring"].get("enabled") else {}
    out = []
    for d in c["directions"]:
        if d not in c["masters"]:
            if mirrored.get(d) in c["masters"]:
                out.append(_issue("mirrored_direction", "info", f"{d} will be mirrored from {mirrored[d]}"))
            else:
                out.append(_issue("missing_direction", "error", f"No approved master for direction '{d}'"))
    return out


def check_animation_set(ws, pid: str, character: dict, required_anims: list[str]) -> list[dict]:
    """Missing directions per animation for a character (direction matrix check)."""
    assets = ws.list_assets(pid, character_id=character["id"])
    have = {(a["animation"]["name"], a["animation"]["direction"]) for a in assets if "animation" in a and a["status"] != "rejected"}
    mirrored = character["mirroring"]["pairs"] if character["mirroring"].get("enabled") else {}
    out = []
    for name in required_anims:
        for d in character["directions"]:
            if (name, d) not in have and (name, mirrored.get(d)) not in have:
                out.append(_issue("missing_direction", "error", f"Animation '{name}' missing direction '{d}'", animation=name, direction=d))
    return out


def check_export(folder: Path, manifest: dict) -> list[dict]:
    """Validate exported files and atlas coordinates against the export manifest."""
    folder = Path(folder)
    issues = []
    for rel in manifest.get("files", []):
        if not (folder / rel).is_file():
            issues.append(_issue("missing_export_file", "error", f"Missing export file {rel}"))
    for anim in manifest.get("animations", []):
        atlas = folder / anim["atlas"] if anim.get("atlas") else None
        if atlas and atlas.is_file():
            with Image.open(atlas) as im:
                W, H = im.size
            for i, f in enumerate(anim["frames"]):
                x, y, w, h = f["atlas"]["x"], f["atlas"]["y"], f["atlas"]["w"], f["atlas"]["h"]
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > W or y + h > H:
                    issues.append(_issue("invalid_atlas_coordinates", "error", f"{anim['name']} frame {i} rect outside atlas", i))
    return issues
