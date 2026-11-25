"""Animation production: templates, creation from frames, and non-destructive frame editing."""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from PIL import Image

from .processing.frames import NormalizeParams, normalize_group
from .util import StudioError, new_id, safe_join
from .workspace import Workspace

# Default action templates. phases map frame ranges to animation-principle phases;
# `poses` describe key poses for prompt construction / review. Durations in ms.
TEMPLATES: dict[str, dict] = {
    "idle": {"frames": 6, "durations": [160, 120, 120, 160, 120, 120], "loop": True,
             "poses": ["neutral stance", "inhale, chest rises 1px", "peak", "neutral", "exhale, slight settle", "low point"],
             "phases": [{"name": "breath", "from": 0, "to": 5}], "events": []},
    "walk": {"frames": 8, "durations": [100] * 8, "loop": True,
             "poses": ["contact (right foot forward)", "down", "passing", "up", "contact (left foot forward)", "down", "passing", "up"],
             "phases": [{"name": "contact", "from": 0, "to": 0}, {"name": "down", "from": 1, "to": 1}, {"name": "passing", "from": 2, "to": 2}, {"name": "up", "from": 3, "to": 3},
                        {"name": "contact", "from": 4, "to": 4}, {"name": "down", "from": 5, "to": 5}, {"name": "passing", "from": 6, "to": 6}, {"name": "up", "from": 7, "to": 7}],
             "events": [{"frame": 0, "type": "footstep"}, {"frame": 4, "type": "footstep"}]},
    "run": {"frames": 8, "durations": [80] * 8, "loop": True,
            "poses": ["contact", "push-off", "flight", "reach", "contact (other leg)", "push-off", "flight", "reach"],
            "phases": [], "events": [{"frame": 0, "type": "footstep"}, {"frame": 4, "type": "footstep"}]},
    "attack": {"frames": 8, "durations": [100, 120, 60, 40, 60, 90, 110, 140], "loop": False,
               "poses": ["ready", "anticipation wind-up", "anticipation peak", "action swing", "impact", "follow-through", "recovery", "return to ready"],
               "phases": [{"name": "anticipation", "from": 1, "to": 2}, {"name": "action", "from": 3, "to": 3}, {"name": "impact", "from": 4, "to": 4},
                          {"name": "follow_through", "from": 5, "to": 5}, {"name": "recovery", "from": 6, "to": 7}],
               "events": [{"frame": 4, "type": "hit"}]},
    "combo_attack": {"frames": 12, "durations": [90, 90, 50, 50, 80, 90, 80, 50, 50, 90, 110, 140], "loop": False,
                     "poses": ["ready", "wind-up 1", "swing 1", "impact 1", "follow 1", "re-chamber", "wind-up 2", "swing 2", "impact 2", "follow 2", "recovery", "ready"],
                     "phases": [{"name": "anticipation", "from": 1, "to": 1}, {"name": "impact", "from": 3, "to": 3}, {"name": "anticipation", "from": 6, "to": 6},
                                {"name": "impact", "from": 8, "to": 8}, {"name": "recovery", "from": 10, "to": 11}],
                     "events": [{"frame": 3, "type": "hit"}, {"frame": 5, "type": "combo_window"}, {"frame": 8, "type": "hit"}]},
    "cast": {"frames": 8, "durations": [100, 120, 140, 160, 60, 100, 120, 140], "loop": False,
             "poses": ["ready", "raise focus", "gather energy", "charge peak", "release", "follow-through", "settle", "ready"],
             "phases": [{"name": "anticipation", "from": 1, "to": 3}, {"name": "action", "from": 4, "to": 4}, {"name": "recovery", "from": 5, "to": 7}],
             "events": [{"frame": 4, "type": "release"}]},
    "dodge": {"frames": 6, "durations": [60, 60, 80, 80, 100, 120], "loop": False, "poses": ["crouch", "lean", "roll/dive", "roll", "land", "recover"],
              "phases": [], "events": [{"frame": 1, "type": "iframes_start"}, {"frame": 4, "type": "iframes_end"}]},
    "dash": {"frames": 6, "durations": [80, 50, 50, 60, 90, 120], "loop": False, "poses": ["crouch", "push", "burst", "glide", "brake", "recover"],
             "phases": [], "events": []},
    "jump": {"frames": 8, "durations": [90, 70, 80, 120, 120, 80, 90, 120], "loop": False,
             "poses": ["crouch anticipation", "take-off", "rise", "apex", "fall", "pre-land", "land squash", "recover"],
             "phases": [{"name": "anticipation", "from": 0, "to": 0}, {"name": "airborne", "from": 2, "to": 5}, {"name": "landing", "from": 6, "to": 7}],
             "events": [{"frame": 1, "type": "takeoff"}, {"frame": 6, "type": "land"}], "airborne": [2, 3, 4, 5]},
    "hit": {"frames": 4, "durations": [60, 80, 100, 120], "loop": False, "poses": ["impact recoil", "stagger", "absorb", "recover"], "phases": [], "events": []},
    "death": {"frames": 8, "durations": [80, 80, 90, 100, 110, 140, 200, 400], "loop": False,
              "poses": ["hit", "lose balance", "knees buckle", "fall", "hit ground", "bounce", "settle", "rest"], "phases": [], "events": [{"frame": 4, "type": "body_fall"}],
              "hold_last": True},
    "interact": {"frames": 6, "durations": [100, 100, 120, 160, 120, 100], "loop": False, "poses": ["ready", "reach", "grab", "use", "release", "ready"],
                 "phases": [], "events": [{"frame": 3, "type": "interact"}]},
}


def template_info() -> dict:
    return copy.deepcopy(TEMPLATES)


def _canon_frames(frames):
    out = []
    for f in frames:
        if isinstance(f, tuple):
            out.append((f[0].convert("RGBA"), int(f[1])))
        else:
            out.append((f.convert("RGBA"), 100))
    return out


def create_animation_asset(ws: Workspace, pid: str, name: str, frames, *, anim_name: str = "custom",
                           direction: str = "none", mode: str = "pixel", params: dict | None = None,
                           provider: dict | None = None, character_id: str | None = None,
                           template: str | None = None, source_file: Path | None = None,
                           source_rects: list | None = None, origin: str = "imported", asset_type: str = "animation",
                           loop: bool | None = None, events: list | None = None, durations: list | None = None,
                           prompt: dict | None = None, processing_note: dict | None = None, tags=None) -> dict:
    frames = _canon_frames(frames)
    if not frames:
        raise StudioError("No frames")
    tpl = TEMPLATES.get(template or "") or {}
    params = dict(params or {})
    params.setdefault("mode", mode)
    if tpl.get("airborne") and "airborne" not in params:
        params["airborne"] = [i for i in tpl["airborne"] if i < len(frames)]
    provider = provider or {"id": "external", "kind": "import"}
    a = ws.new_asset(pid, asset_type, name, mode, provider, character_id=character_id, prompt=prompt, tags=tags or [],
                     processing={"normalize": {}, **(processing_note or {})})
    d = ws.asset_dir(pid, a["id"])
    (d / "frames_src").mkdir(exist_ok=True)
    if source_file:
        dst = d / "source" / ("original" + Path(source_file).suffix.lower())
        shutil.copyfile(source_file, dst)
        ws.add_file(a, dst, "source", "original", origin) if dst.suffix in (".png", ".gif", ".webp", ".jpg", ".jpeg", ".apng") else \
            a["source_files"].append({"path": dst.relative_to(d).as_posix(), "role": "original", "origin": origin})
    src_paths = []
    for i, (im, _) in enumerate(frames):
        fid = f"f{i:03d}-{new_id()[:4]}"
        p = d / "frames_src" / f"{fid}.png"
        im.save(p)
        src_paths.append((fid, p))
    processed, rec = normalize_group([im for im, _ in frames], params)
    durs = durations or [dur for _, dur in frames]
    if tpl and not durations and len(tpl["durations"]) == len(frames) and all(dd == 100 for _, dd in frames):
        durs = list(tpl["durations"])
    fr = []
    for i, ((fid, sp), im, r) in enumerate(zip(src_paths, processed, rec["frames"])):
        out = d / "frames" / f"{fid}.png"
        im.save(out)
        fr.append({"id": fid, "file": f"frames/{fid}.png", "source_file": f"frames_src/{fid}.png", "duration_ms": int(durs[i]),
                   "offset": r["offset"], "source_rect": (source_rects[i] if source_rects else None), "source_size": r["source_size"],
                   "trimmed_rect": r["trimmed_rect"], "origin": origin, "status": "ok", "phase": _phase_for(tpl, i),
                   "airborne": r["airborne"], "generation": None})
    a["processing"]["normalize"] = rec
    a["animation"] = {"name": _anim_slug(anim_name), "template": template, "direction": direction, "mirror_of": None,
                      "canvas": rec["canvas"], "pivot": rec["pivot"],
                      "anchor": {"kind": rec["params"]["anchor"], "ground_y": rec["pivot"][1]},
                      "loop": {"enabled": bool(tpl.get("loop", True) if loop is None else loop), "ping_pong": False, "hold_last": bool(tpl.get("hold_last", False))},
                      "frames": fr, "events": [e for e in (events if events is not None else tpl.get("events", [])) if e["frame"] < len(fr)],
                      "layers": [], "phases": [ph for ph in tpl.get("phases", []) if ph["to"] < len(fr)]}
    a["status"] = "candidate"
    return ws.save_asset(a, snapshot_note="created")


def _anim_slug(s: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9_-]+", "_", s.lower()).strip("_") or "anim"
    return s if s[0].isalpha() else "a_" + s


def _phase_for(tpl, i):
    for ph in tpl.get("phases", []):
        if ph["from"] <= i <= ph["to"]:
            return ph["name"]
    return None


def frame_path(ws: Workspace, a: dict, frame: dict, source: bool = False) -> Path:
    return safe_join(ws.asset_dir(a["project_id"], a["id"]), frame["source_file"] if source and frame.get("source_file") else frame["file"])


def load_frames(ws: Workspace, a: dict, include_rejected: bool = False) -> list[tuple[dict, Image.Image]]:
    out = []
    for f in a["animation"]["frames"]:
        if f.get("status") == "rejected" and not include_rejected:
            continue
        with Image.open(frame_path(ws, a, f)) as im:
            out.append((f, im.convert("RGBA")))
    return out


def reprocess(ws: Workspace, a: dict, params: dict) -> dict:
    """Re-run normalisation from preserved source frames (reproducible, reversible via versions)."""
    anim = a["animation"]
    base = dict(a["processing"].get("normalize", {}).get("params", {}))
    base.update(params or {})
    srcs = []
    for f in anim["frames"]:
        with Image.open(frame_path(ws, a, f, source=True)) as im:
            srcs.append(im.convert("RGBA"))
    ws._snapshot(a, ws.asset_dir(a["project_id"], a["id"]), "before reprocess")
    processed, rec = normalize_group(srcs, base)
    d = ws.asset_dir(a["project_id"], a["id"])
    for f, im, r in zip(anim["frames"], processed, rec["frames"]):
        im.save(safe_join(d, f["file"]))
        f.update(offset=r["offset"], trimmed_rect=r["trimmed_rect"], airborne=r["airborne"], source_size=r["source_size"])
    anim["canvas"], anim["pivot"] = rec["canvas"], rec["pivot"]
    anim["anchor"] = {"kind": rec["params"]["anchor"], "ground_y": rec["pivot"][1]}
    a["processing"]["normalize"] = rec
    a["art_style"] = rec["params"]["mode"]
    return ws.save_asset(a)


def edit_frames(ws: Workspace, a: dict, op: str, **kw) -> dict:
    """Frame operations: reorder, duplicate, delete, duration, durations, reject, restore, loop, pivot, events, phase."""
    anim = a["animation"]
    fr = anim["frames"]
    d = ws.asset_dir(a["project_id"], a["id"])

    def idx(name="index"):
        i = int(kw[name])
        if not 0 <= i < len(fr):
            raise StudioError("Frame index out of range")
        return i

    note = op
    if op == "reorder":
        order = [int(x) for x in kw["order"]]
        if sorted(order) != list(range(len(fr))):
            raise StudioError("order must be a permutation of frame indices")
        remap = {old: new for new, old in enumerate(order)}
        anim["frames"] = [fr[i] for i in order]
        for e in anim.get("events", []):
            e["frame"] = remap[e["frame"]]
    elif op == "move":
        i, to = idx(), int(kw["to"])
        order = list(range(len(fr)))
        order.insert(max(0, min(len(fr) - 1, to)), order.pop(i))
        return edit_frames(ws, a, "reorder", order=order)
    elif op == "duplicate":
        i = idx()
        nf = copy.deepcopy(fr[i])
        nf["id"] = f"f{len(fr):03d}-{new_id()[:4]}"
        for key in ("file", "source_file"):
            if nf.get(key):
                src = safe_join(d, nf[key])
                newp = src.with_name(nf["id"] + ".png")
                shutil.copyfile(src, newp)
                nf[key] = newp.relative_to(d).as_posix()
        fr.insert(i + 1, nf)
        for e in anim.get("events", []):
            if e["frame"] > i:
                e["frame"] += 1
    elif op == "delete":
        i = idx()
        if len(fr) <= 1:
            raise StudioError("An animation needs at least one frame")
        fr.pop(i)  # files are kept in versions/ via the snapshot below
        anim["events"] = [dict(e, frame=e["frame"] - (1 if e["frame"] > i else 0)) for e in anim.get("events", []) if e["frame"] != i]
    elif op == "duration":
        i = idx()
        v = int(kw["duration_ms"])
        if not 1 <= v <= 60000:
            raise StudioError("duration_ms must be 1..60000")
        fr[i]["duration_ms"] = v
    elif op == "durations":
        vals = [int(v) for v in kw["durations"]]
        if len(vals) != len(fr) or any(not 1 <= v <= 60000 for v in vals):
            raise StudioError("durations must match frame count, each 1..60000")
        for f, v in zip(fr, vals):
            f["duration_ms"] = v
    elif op == "fps":
        fps = float(kw["fps"])
        if not 0.5 <= fps <= 120:
            raise StudioError("fps must be 0.5..120")
        for f in fr:
            f["duration_ms"] = round(1000 / fps)
    elif op in ("reject", "restore"):
        i = idx()
        fr[i]["status"] = "rejected" if op == "reject" else "ok"
    elif op == "loop":
        anim["loop"].update({k: bool(v) for k, v in kw.items() if k in ("enabled", "ping_pong", "hold_last")})
    elif op == "pivot":
        x, y = int(kw["x"]), int(kw["y"])
        if not (0 <= x < anim["canvas"][0] and 0 <= y < anim["canvas"][1]):
            raise StudioError("pivot must lie inside the canvas")
        anim["pivot"] = [x, y]
        anim["anchor"]["kind"] = "custom"
    elif op == "nudge":
        # Integer whole-frame shift (manual alignment); recorded as manual offset and reprocessed.
        i = idx()
        dx, dy = int(kw.get("dx", 0)), int(kw.get("dy", 0))
        mo = dict(a["processing"]["normalize"]["params"].get("manual_offsets", {}))
        cur = mo.get(str(i), [0, 0])
        mo[str(i)] = [cur[0] + dx, cur[1] + dy]
        return reprocess(ws, a, {"manual_offsets": mo, "canvas": anim["canvas"], "pivot": anim["pivot"]})
    elif op == "events":
        evs = kw["events"]
        for e in evs:
            if not 0 <= int(e["frame"]) < len(fr):
                raise StudioError("event frame out of range")
        anim["events"] = [{"frame": int(e["frame"]), "type": str(e["type"]), **({"name": e["name"]} if e.get("name") else {}),
                           **({"data": e["data"]} if isinstance(e.get("data"), dict) else {})} for e in evs]
    elif op == "phase":
        i = idx()
        fr[i]["phase"] = kw.get("phase") or None
    elif op == "airborne":
        i = idx()
        fr[i]["airborne"] = bool(kw.get("value", True))
    else:
        raise StudioError(f"Unknown frame op {op}")
    return ws.save_asset(a, snapshot_note=note)


def replace_frame(ws: Workspace, a: dict, index: int, image: Image.Image, origin: str = "manual",
                  generation: dict | None = None, reprocess_group: bool = True) -> dict:
    """Manual replacement / selective regeneration result. The new source frame is placed with the
    group's existing scale and anchor policy (never re-fitted on its own)."""
    fr = a["animation"]["frames"]
    if not 0 <= index < len(fr):
        raise StudioError("Frame index out of range")
    d = ws.asset_dir(a["project_id"], a["id"])
    ws._snapshot(a, d, f"replace frame {index}")
    f = fr[index]
    nid = f"f{index:03d}-{new_id()[:4]}"
    sp = d / "frames_src" / f"{nid}.png"
    image.convert("RGBA").save(sp)
    f.update(id=nid, source_file=f"frames_src/{nid}.png", file=f"frames/{nid}.png", origin=origin, status="ok", generation=generation)
    shutil.copyfile(sp, d / f["file"])
    if reprocess_group:
        return reprocess(ws, a, {"canvas": a["animation"]["canvas"], "pivot": a["animation"]["pivot"]})
    return ws.save_asset(a)


def add_layer(ws: Workspace, a: dict, layer_asset_id: str, role: str = "effect", offset=(0, 0), z: int = 1,
              start_ms: int = 0, anchor_to_event: str | None = None, name: str | None = None, event_offset_ms: int = 0) -> dict:
    """Attach an independently-timed layer (e.g. procedural effect) to a character animation."""
    other = ws.get_asset(a["project_id"], layer_asset_id)
    if "animation" not in other:
        raise StudioError("Layer asset must be an animation")
    if anchor_to_event:
        ev = next((e for e in a["animation"]["events"] if e["type"] == anchor_to_event), None)
        if not ev:
            raise StudioError(f"No event '{anchor_to_event}' to anchor to")
        # event time plus an optional lead/lag so e.g. an effect's own impact frame lands on the hit
        start_ms = max(0, sum(f["duration_ms"] for f in a["animation"]["frames"][:ev["frame"]]) + int(event_offset_ms))
    a["animation"]["layers"] = [l for l in a["animation"]["layers"] if l["asset_id"] != layer_asset_id] + [
        {"name": name or other["name"], "asset_id": layer_asset_id, "role": role, "offset": [int(offset[0]), int(offset[1])],
         "z": int(z), "start_ms": int(start_ms), "anchor_to_event": anchor_to_event, "event_offset_ms": int(event_offset_ms)}]
    return ws.save_asset(a, snapshot_note=f"layer {layer_asset_id}")


def timeline(anim: dict) -> list[int]:
    t, out = 0, []
    for f in anim["frames"]:
        out.append(t)
        t += f["duration_ms"]
    return out
