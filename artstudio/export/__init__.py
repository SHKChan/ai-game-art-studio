"""Export Studio backend: PNG frames, sprite sheets, packed atlases, GIF/APNG previews, JSON metadata,
and engine-specific descriptors (Cocos Creator 3.x TexturePacker plist; TexturePacker JSON-hash for
Phaser 3 / PixiJS; generic JSON for Godot / Unity importers).

Formats emitted are documented, widely supported ones — no invented engine formats.
"""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from .. import __version__
from ..animation import load_frames, timeline
from ..processing.frames import alpha_bbox, resample, to_np
from ..qa import check_export, summarize
from ..util import StudioError, new_id, now, write_json

FORMATS = ("frames", "sheet", "atlas", "gif", "apng", "json", "cocos", "phaser", "godot", "zip")


# ---------------------------------------------------------------- packing
def pack_shelf(sizes: list[tuple[int, int]], max_size: int = 4096, padding: int = 2, pot: bool = False):
    """Shelf packer (sorted by height). Returns (positions, (W,H)). Raises if it cannot fit."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    total = sum((w + padding) * (h + padding) for w, h in sizes)
    width = min(max_size, max(max((w for w, _ in sizes), default=1) + padding * 2, int(math.sqrt(total) * 1.15) + padding))
    if pot:
        width = 1 << (width - 1).bit_length()
    pos = [None] * len(sizes)
    x = y = padding
    shelf_h = 0
    for i in order:
        w, h = sizes[i]
        if x + w + padding > width:
            x, y = padding, y + shelf_h + padding
            shelf_h = 0
        if w + 2 * padding > width:
            raise StudioError("Frame wider than max atlas size")
        pos[i] = (x, y)
        x += w + padding
        shelf_h = max(shelf_h, h)
    height = y + shelf_h + padding
    if pot:
        height = 1 << (height - 1).bit_length()
    if height > max_size:
        raise StudioError(f"Atlas would be {width}x{height}; exceeds max {max_size}. Split the export or reduce frames.")
    return pos, (width, height)


# ---------------------------------------------------------------- previews
def _gif_palette(frames: list[Image.Image]) -> list[tuple[int, int, int]]:
    cols = set()
    for f in frames:
        a = to_np(f).reshape(-1, 4)
        cols.update(map(tuple, a[a[:, 3] >= 128][:, :3].tolist()))
        if len(cols) > 255:
            break
    if len(cols) <= 255:
        return sorted(cols)
    from ..processing.frames import median_cut_palette
    return [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in median_cut_palette(frames, 255)]


def write_gif(frames: list[Image.Image], durations: list[int], path: Path, loop: bool = True, scale: int = 1,
              mode: str = "pixel", bg=None) -> Path:
    """GIF preview. GIF has 1-bit alpha and 10ms timing: HD frames are thresholded (use the APNG for soft alpha)."""
    if scale != 1:
        frames = [resample(f, (f.width * scale, f.height * scale), "pixel" if mode == "pixel" else "hd") for f in frames]
    if bg is not None:
        flat = []
        for f in frames:
            c = Image.new("RGBA", f.size, tuple(bg) + (255,))
            c.alpha_composite(f)
            flat.append(c)
        frames = flat
    pal = _gif_palette(frames)
    lut = np.array(pal, np.int32)
    out = []
    for f in frames:
        a = to_np(f)
        flat = a.reshape(-1, 4)
        idx = np.zeros(len(flat), np.uint8)
        on = flat[:, 3] >= 128
        rgb = flat[on, :3].astype(np.int32)
        if len(rgb):
            uniq, inv = np.unique(rgb, axis=0, return_inverse=True)
            d = ((uniq[:, None, :] - lut[None]) ** 2).sum(-1).argmin(1)
            idx[on] = (d[inv.reshape(-1)] + 1).astype(np.uint8)
        p = Image.frombytes("P", f.size, idx.tobytes())
        p.putpalette([0, 0, 0] + [v for c in pal for v in c] + [0] * (768 - 3 - 3 * len(pal)))
        p.info["transparency"] = 0
        out.append(p)
    kw = dict(save_all=True, append_images=out[1:], duration=[max(20, int(round(d / 10) * 10)) for d in durations],
              transparency=0, disposal=2, optimize=False)
    if loop:
        kw["loop"] = 0
    out[0].save(path, **kw)
    return path


def write_apng(frames: list[Image.Image], durations: list[int], path: Path, loop: bool = True, scale: int = 1, mode: str = "hd") -> Path:
    if scale != 1:
        frames = [resample(f, (f.width * scale, f.height * scale), mode) for f in frames]
    frames[0].save(path, format="PNG", save_all=True, append_images=frames[1:], duration=list(durations),
                   loop=0 if loop else 1, disposal=1, blend=0)
    return path


def contact_sheet(frames: list[Image.Image], cols: int = 8, bg=(40, 44, 52), scale: int = 1, mode: str = "pixel",
                  labels: bool = True) -> Image.Image:
    from PIL import ImageDraw
    if scale != 1:
        frames = [resample(f, (f.width * scale, f.height * scale), mode) for f in frames]
    cw = max(f.width for f in frames)
    ch = max(f.height for f in frames)
    cols = min(cols, len(frames))
    rows = math.ceil(len(frames) / cols)
    pad = 4
    sheet = Image.new("RGBA", (cols * (cw + pad) + pad, rows * (ch + pad + (12 if labels else 0)) + pad), bg + (255,))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(frames):
        x = pad + (i % cols) * (cw + pad)
        y = pad + (i // cols) * (ch + pad + (12 if labels else 0))
        cell = Image.new("RGBA", (cw, ch), tuple(min(255, v + 14) for v in bg) + (255,))
        cell.alpha_composite(f, (0, 0))
        sheet.alpha_composite(cell, (x, y))
        if labels:
            d.text((x + 2, y + ch + 1), str(i), fill=(200, 200, 200, 255))
    return sheet


# ---------------------------------------------------------------- formats
def _cocos_plist(frames: dict, image_name: str, size) -> str:
    """TexturePacker 'cocos2d' plist (format 2), which Cocos Creator 3.x imports as a SpriteAtlas."""
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
             '<plist version="1.0">', "<dict>", "<key>frames</key>", "<dict>"]
    for name, f in frames.items():
        fx, fy, fw, fh = f["frame"]["x"], f["frame"]["y"], f["frame"]["w"], f["frame"]["h"]
        sx, sy = f["spriteSourceSize"]["x"], f["spriteSourceSize"]["y"]
        W, H = f["sourceSize"]["w"], f["sourceSize"]["h"]
        # Cocos offset: trimmed-rect centre relative to the source centre, Y up.
        ox = (sx + fw / 2) - W / 2
        oy = H / 2 - (sy + fh / 2)
        parts += [f"<key>{esc(name)}</key>", "<dict>",
                  "<key>frame</key>", f"<string>{{{{{fx},{fy}}},{{{fw},{fh}}}}}</string>",
                  "<key>offset</key>", f"<string>{{{ox:g},{oy:g}}}</string>",
                  "<key>rotated</key>", "<false/>",
                  "<key>sourceColorRect</key>", f"<string>{{{{{sx},{sy}}},{{{fw},{fh}}}}}</string>",
                  "<key>sourceSize</key>", f"<string>{{{W},{H}}}</string>", "</dict>"]
    parts += ["</dict>", "<key>metadata</key>", "<dict>",
              "<key>format</key>", "<integer>2</integer>",
              "<key>realTextureFileName</key>", f"<string>{esc(image_name)}</string>",
              "<key>size</key>", f"<string>{{{size[0]},{size[1]}}}</string>",
              "<key>textureFileName</key>", f"<string>{esc(image_name)}</string>",
              "</dict>", "</dict>", "</plist>", ""]
    return "\n".join(parts)


def composite_timeline(ws, a: dict) -> tuple[list[Image.Image], list[int], dict]:
    """Flatten a character animation with its independently-timed layers into preview frames.
    Breakpoints are the union of every layer's frame boundaries, so each layer keeps its own timing."""
    base = load_frames(ws, a)
    anim = a["animation"]
    layers = []
    for l in anim.get("layers", []):
        la = ws.get_asset(a["project_id"], l["asset_id"])
        layers.append((l, la, load_frames(ws, la)))
    total = sum(f["duration_ms"] for f, _ in base)
    cuts = set(timeline({"frames": [f for f, _ in base]})) | {total}
    for l, la, fr in layers:
        t = l.get("start_ms", 0)
        for f, _ in fr:
            if 0 <= t <= total:
                cuts.add(t)
            t += f["duration_ms"]
        if 0 <= t <= total:
            cuts.add(t)
    cuts = sorted(c for c in cuts if c <= total)
    px, py = anim["pivot"]
    # canvas bounds covering all layers
    L, T, R, B = 0, 0, anim["canvas"][0], anim["canvas"][1]
    for l, la, fr in layers:
        lx, ly = la["animation"]["pivot"]
        ox, oy = px - lx + l["offset"][0], py - ly + l["offset"][1]
        lw, lh = la["animation"]["canvas"]
        L, T, R, B = min(L, ox), min(T, oy), max(R, ox + lw), max(B, oy + lh)

    def frame_at(fr, t, loop):
        tot = sum(f["duration_ms"] for f, _ in fr)
        if t < 0 or (t >= tot and not loop):
            return None
        t = t % tot
        acc = 0
        for f, im in fr:
            acc += f["duration_ms"]
            if t < acc:
                return im
        return None

    out, durs = [], []
    for t0, t1 in zip(cuts, cuts[1:]):
        c = Image.new("RGBA", (R - L, B - T), (0, 0, 0, 0))
        stack = [(0, None, base, None)] + [(l["z"], l, fr, la) for l, la, fr in layers]
        for z, l, fr, la in sorted(stack, key=lambda s: s[0]):
            if l is None:
                im = frame_at(fr, t0, False)
                if im is not None:
                    c.alpha_composite(im, (-L, -T))
            else:
                im = frame_at(fr, t0 - l.get("start_ms", 0), la["animation"]["loop"]["enabled"])
                if im is not None:
                    lx, ly = la["animation"]["pivot"]
                    c.alpha_composite(im, (px - lx + l["offset"][0] - L, py - ly + l["offset"][1] - T))
        out.append(c)
        durs.append(t1 - t0)
    return out, durs, {"origin": [-L, -T], "pivot": [px - L, py - T]}


def _key(anim: dict) -> str:
    d = anim["direction"]
    return anim["name"] if d == "none" else f"{anim['name']}_{d}"


def export_assets(ws, pid: str, asset_ids: list[str], *, name: str = "export", formats=None, preview_scale: int = 2,
                  trim: bool = True, padding: int = 2, extrude: int = 0, max_atlas: int = 4096, pot: bool = False,
                  character_id: str | None = None, include_layers: bool = True) -> dict:
    """Export animation assets (with any attached layers) into one folder. Returns the export manifest."""
    formats = set(formats or FORMATS)
    unknown = formats - set(FORMATS)
    if unknown:
        raise StudioError(f"Unknown formats {sorted(unknown)}")
    assets = [ws.get_asset(pid, a) for a in asset_ids]
    if include_layers:
        seen = {a["id"] for a in assets}
        for a in list(assets):
            for l in a.get("animation", {}).get("layers", []):
                if l["asset_id"] not in seen:
                    assets.append(ws.get_asset(pid, l["asset_id"]))
                    seen.add(l["asset_id"])
    if not assets or any("animation" not in a for a in assets):
        raise StudioError("Select one or more animation assets")
    eid = new_id("exp")
    out = ws.export_dir(pid, eid)
    files: list[str] = []
    anims_meta = []
    atlas_items = []  # (frame_name, trimmed_image, meta)
    fixtures = False
    for a in assets:
        fixtures |= bool(a["provider"].get("is_test_fixture"))
        anim = a["animation"]
        key = _key(anim)
        if any(m["key"] == key for m in anims_meta):
            key = f"{key}_{a['id'][-6:]}"
        pairs = load_frames(ws, a)
        if not pairs:
            raise StudioError(f"{a['name']}: all frames rejected")
        imgs = [im for _, im in pairs]
        durs = [f["duration_ms"] for f, _ in pairs]
        starts = timeline({"frames": [f for f, _ in pairs]})
        mode = a["art_style"]
        cw, ch = anim["canvas"]
        px, py = anim["pivot"]
        keep_ids = [f["id"] for f, _ in pairs]
        idx_map = {fid: i for i, fid in enumerate(keep_ids)}
        all_ids = [f["id"] for f in anim["frames"]]
        events = []
        for e in anim.get("events", []):
            fid = all_ids[e["frame"]]
            if fid in idx_map:
                i = idx_map[fid]
                events.append({**e, "frame": i, "time_ms": starts[i]})
        fm = []
        if "frames" in formats:
            (out / "frames" / key).mkdir(parents=True, exist_ok=True)
        for i, im in enumerate(imgs):
            fname = f"{key}_{i:02d}"
            bb = alpha_bbox(im) if trim else (0, 0, cw, ch)
            bb = bb or (0, 0, 1, 1)
            if "frames" in formats:
                rel = f"frames/{key}/{i:02d}.png"
                im.save(out / rel)
                files.append(rel)
            t = im.crop(bb)
            atlas_items.append((fname, t, bb, (cw, ch)))
            fm.append({"name": fname, "index": i, "duration_ms": durs[i], "start_ms": starts[i],
                       "trim_offset": [bb[0], bb[1]], "trimmed_size": [bb[2] - bb[0], bb[3] - bb[1]],
                       "source_size": [cw, ch], "pivot_px": [px, py],
                       "pivot_norm": [round(px / cw, 6), round(1 - py / ch, 6)],  # x right, y up (Cocos/Unity convention)
                       "pivot_norm_trimmed": [round((px - bb[0]) / max(1, bb[2] - bb[0]), 6), round(1 - (py - bb[1]) / max(1, bb[3] - bb[1]), 6)],
                       "phase": pairs[i][0].get("phase"), "origin": pairs[i][0].get("origin")})
        if "sheet" in formats:
            cols = min(8, len(imgs))
            rows = math.ceil(len(imgs) / cols)
            sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
            for i, im in enumerate(imgs):
                sheet.alpha_composite(im, ((i % cols) * cw, (i // cols) * ch))
                fm[i]["sheet"] = {"x": (i % cols) * cw, "y": (i // cols) * ch, "w": cw, "h": ch}
            rel = f"sheets/{key}.png"
            (out / "sheets").mkdir(exist_ok=True)
            sheet.save(out / rel)
            files.append(rel)
        loop = anim["loop"]["enabled"]
        prev = {}
        if "gif" in formats:
            (out / "previews").mkdir(exist_ok=True)
            rel = f"previews/{key}.gif"
            write_gif(imgs, durs, out / rel, loop=loop, scale=preview_scale, mode=mode)
            files.append(rel)
            prev["gif"] = rel
        if "apng" in formats:
            (out / "previews").mkdir(exist_ok=True)
            rel = f"previews/{key}.png"
            write_apng(imgs, durs, out / rel, loop=loop, scale=preview_scale, mode=mode)
            files.append(rel)
            prev["apng"] = rel
        if anim.get("layers") and ("gif" in formats or "apng" in formats):
            cf, cd, cinfo = composite_timeline(ws, a)
            rel = f"previews/{key}_composite.gif"
            (out / "previews").mkdir(exist_ok=True)
            write_gif(cf, cd, out / rel, loop=loop, scale=preview_scale, mode=mode)
            files.append(rel)
            prev["composite_gif"] = rel
            prev["composite_note"] = "Preview only: layers stay separate in the atlas/metadata with their own timing."
        anims_meta.append({"key": key, "asset_id": a["id"], "name": anim["name"], "direction": anim["direction"],
                           "art_style": mode, "loop": anim["loop"], "canvas": [cw, ch], "pivot_px": [px, py],
                           "duration_ms": sum(durs), "frames": fm, "events": events, "phases": anim.get("phases", []),
                           "layers": [{**l, "key": None} for l in anim.get("layers", [])], "previews": prev,
                           "is_test_fixture": bool(a["provider"].get("is_test_fixture")), "provider": a["provider"]["id"],
                           "character_id": a.get("character_id"), "mirror_of": anim.get("mirror_of")})
    # resolve layer keys
    by_asset = {m["asset_id"]: m["key"] for m in anims_meta}
    for m in anims_meta:
        for l in m["layers"]:
            l["key"] = by_asset.get(l["asset_id"])
    atlas_rel = None
    if formats & {"atlas", "cocos", "phaser", "godot"}:
        sizes = [(t.width + 2 * extrude, t.height + 2 * extrude) for _, t, _, _ in atlas_items]
        pos, (W, H) = pack_shelf(sizes, max_atlas, padding, pot)
        atlas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tp_frames = {}
        for (fname, t, bb, (cw, ch)), (x, y) in zip(atlas_items, pos):
            if extrude:
                e = t.resize((t.width + 2 * extrude, t.height + 2 * extrude), Image.Resampling.NEAREST)
                e.paste(t, (extrude, extrude))
                atlas.alpha_composite(e, (x, y))
            else:
                atlas.alpha_composite(t, (x, y))
            fx, fy = x + extrude, y + extrude
            tp_frames[fname] = {"frame": {"x": fx, "y": fy, "w": t.width, "h": t.height}, "rotated": False,
                                "trimmed": (t.width, t.height) != (cw, ch),
                                "spriteSourceSize": {"x": bb[0], "y": bb[1], "w": t.width, "h": t.height},
                                "sourceSize": {"w": cw, "h": ch}}
        atlas_rel = f"{name}_atlas.png"
        atlas.save(out / atlas_rel)
        files.append(atlas_rel)
        for m in anims_meta:
            m["atlas"] = atlas_rel
            for f in m["frames"]:
                r = tp_frames[f["name"]]["frame"]
                f["atlas"] = {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"], "page": 0}
                tp_frames[f["name"]]["pivot"] = {"x": round((f["pivot_px"][0] - f["trim_offset"][0]) / r["w"], 6) if r["w"] else 0.5,
                                                  "y": round((f["pivot_px"][1] - f["trim_offset"][1]) / r["h"], 6) if r["h"] else 1.0}
        tp = {"frames": tp_frames,
              "animations": {m["key"]: [f["name"] for f in m["frames"]] for m in anims_meta},
              "meta": {"app": "ai-game-art-studio", "version": __version__, "image": atlas_rel, "format": "RGBA8888",
                       "size": {"w": W, "h": H}, "scale": "1",
                       "frameTags": [{"name": m["key"], "from": 0, "to": len(m["frames"]) - 1} for m in anims_meta]}}
        if formats & {"atlas", "phaser"}:
            write_json(out / f"{name}_atlas.json", tp)  # TexturePacker JSON-hash: Phaser 3 load.atlas / PixiJS Spritesheet
            files.append(f"{name}_atlas.json")
        if "cocos" in formats:
            (out / "cocos").mkdir(exist_ok=True)
            atlas.save(out / "cocos" / f"{name}.png")
            (out / "cocos" / f"{name}.plist").write_text(_cocos_plist(tp_frames, f"{name}.png", (W, H)), encoding="utf-8")
            files += [f"cocos/{name}.png", f"cocos/{name}.plist"]
    direction_map = {}
    for m in anims_meta:
        direction_map.setdefault(m["name"], {})[m["direction"]] = {"key": m["key"], "flip_x": False}
    # Optional horizontal mirroring declared by the character (never automatic).
    if character_id:
        c = ws.get_character(pid, character_id)
        if c["mirroring"].get("enabled"):
            for name_, dirs in direction_map.items():
                for target, src in c["mirroring"]["pairs"].items():
                    if target not in dirs and src in dirs:
                        dirs[target] = {"key": dirs[src]["key"], "flip_x": True}
    manifest = {"schema": "artstudio.export/1", "app_version": __version__, "export_id": eid, "name": name,
                "created_at": now(), "project_id": pid, "character_id": character_id,
                "contains_test_fixtures": fixtures,
                "coordinate_notes": "Pixel coords: origin top-left, y down. pivot_norm uses y-up (Cocos/Unity anchor convention).",
                "animations": anims_meta, "direction_map": direction_map, "files": files}
    if "json" in formats or "cocos" in formats or "godot" in formats:
        write_json(out / f"{name}.anim.json", manifest)
        files.append(f"{name}.anim.json")
        if "cocos" in formats:
            write_json(out / "cocos" / f"{name}.anim.json", manifest)
            files.append(f"cocos/{name}.anim.json")
    if "godot" in formats:
        (out / "godot").mkdir(exist_ok=True)
        (out / "godot" / "README.txt").write_text(
            "Godot 4: import the atlas PNG, then run examples/godot/build_sprite_frames.gd (EditorScript) pointing at\n"
            f"{name}.anim.json to build a SpriteFrames resource with AtlasTexture regions and per-frame durations.\n", encoding="utf-8")
        files.append("godot/README.txt")
    issues = check_export(out, manifest)
    manifest["qa"] = summarize(issues)
    write_json(out / "export_manifest.json", manifest)
    files.append("export_manifest.json")
    if "zip" in formats:
        with zipfile.ZipFile(out / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in out.rglob("*"):
                if f.is_file() and f.suffix != ".zip":
                    z.write(f, f.relative_to(out).as_posix())
        manifest["zip"] = f"{name}.zip"
        write_json(out / "export_manifest.json", manifest)
    for a in assets:
        if a["id"] in asset_ids:
            a["exports"].append({"id": eid, "format": ",".join(sorted(formats)), "path": f"exports/{eid}", "created_at": now()})
            ws.save_asset(a)
    manifest["path"] = str(out)
    return manifest
