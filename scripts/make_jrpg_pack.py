"""Render the JRPG asset pack from Pixel Forge builders (offline, deterministic).

    python scripts/make_jrpg_pack.py --out deliverables/jrpg_pack [--scale 4]

Writes
  icons/<set>/<name>.png       1× icons (32×32; status badges 16×16)
  effects/<name>/strip.png     1× horizontal sprite strip, plus meta.json (frame size, durations, tags, pivot, loop)
  effects/<name>/preview.gif   upscaled animated preview on transparent background
  preview/*.png                upscaled contact sheets for review
Every file comes from a builder + params recorded in pack.json, so it can be re-made or tweaked in Pixel Forge."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from artstudio.engine import Engine  # noqa: E402
from artstudio.procedural import BUILDERS  # noqa: E402

ICON_SETS = {
    "weapons": ("weapon_icon", "kind", "material"),
    "armor": ("armor_icon", "kind", "material"),
    "consumables": ("consumable_icon", "kind", "grade"),
    "materials": ("material_icon", "kind", "color"),
    "skills": ("skill_icon", "skill", None),
    "status": ("status_icon", "status", None),
    "ui": ("ui_icon", "kind", "style"),
}
UI_THEMES = ["classic_blue", "wood_gold", "stone_iron", "parchment"]
UI_SPECS = [  # (file stem, builder, params)
    ("window", "ui_panel", {"kind": "window", "width": 128, "height": 80}),
    ("dialog", "ui_panel", {"kind": "dialog", "width": 192, "height": 64}),
    ("tooltip", "ui_panel", {"kind": "tooltip", "width": 96, "height": 40}),
    ("title", "ui_panel", {"kind": "title", "width": 128, "height": 28}),
    ("tab", "ui_panel", {"kind": "tab", "width": 48, "height": 18}),
    ("button", "ui_button", {"shape": "rect", "width": 96, "height": 32}),
    ("button-square", "ui_button", {"shape": "square", "height": 40}),
    ("button-round", "ui_button", {"shape": "round", "height": 40}),
    ("bar-hp", "ui_bar", {"kind": "hp", "width": 96, "height": 12}),
    ("bar-mp", "ui_bar", {"kind": "mp", "width": 96, "height": 12}),
    ("bar-exp", "ui_bar", {"kind": "exp", "width": 96, "height": 8, "fill": 0.45}),
    ("bar-frame", "ui_bar", {"kind": "hp", "width": 96, "height": 12, "part": "frame"}),
    ("bar-fill-hp", "ui_bar", {"kind": "hp", "width": 96, "height": 12, "part": "fill", "fill": 1.0}),
    ("portrait", "ui_frame", {"kind": "portrait", "size": 64}),
    ("slot", "ui_frame", {"kind": "slot", "size": 40}),
    ("skill-slot", "ui_frame", {"kind": "skill_slot", "size": 40}),
]
EFFECTS = ["lava_burn", "meteor", "fire_pillar", "earth_spike", "whirlpool", "gale", "ice_field", "holy_judgment",
           "dark_vortex", "life_drain"]


def render(builder: str, params: dict):
    eng = Engine(Path(tempfile.mkdtemp(prefix="pack-")))
    doc_id = eng.run(BUILDERS[builder].build(**params))
    d = eng.store.load(doc_id)
    return [d.render_image(i) for i in range(len(d.frames))], [f["duration_ms"] for f in d.frames], d.tags


def sheet(images, cols, scale, bg=((44, 42, 54), (54, 52, 66)), label=None, pad=4):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    top = 14 if label else 0
    out = Image.new("RGBA", (cols * (w * scale + pad) + pad, top + rows * (h * scale + pad) + pad), (24, 22, 30, 255))
    if label:
        ImageDraw.Draw(out).text((pad, 2), label, fill=(220, 220, 230, 255))
    for i, im in enumerate(images):
        cell = Image.new("RGBA", im.size, bg[(i // cols + i % cols) % 2] + (255,))
        cell.alpha_composite(im)
        out.paste(cell.resize((w * scale, h * scale), Image.NEAREST), (pad + (i % cols) * (w * scale + pad), top + pad + (i // cols) * (h * scale + pad)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "deliverables" / "jrpg_pack"))
    ap.add_argument("--scale", type=int, default=4)
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "preview").mkdir(parents=True, exist_ok=True)
    manifest = {"icons": [], "effects": []}
    for set_name, (b, key, axis) in ICON_SETS.items():
        kinds = BUILDERS[b].PARAMS[key]["enum"]
        variants = [v for v in BUILDERS[b].PARAMS[axis]["enum"] if v != "auto"] if axis else [None]
        ims = []
        for v in variants:
            for k in kinds:
                p = {key: k, **({axis: v} if axis else {})}
                im = render(b, p)[0][0]
                name = f"{v}-{k}" if v else k
                path = out / "icons" / set_name / f"{name.replace('_', '-')}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                im.save(path)
                ims.append(im)
                manifest["icons"].append({"file": path.relative_to(out).as_posix(), "builder": b, "params": p})
        sheet(ims, len(kinds), a.scale if ims[0].width > 16 else a.scale * 2, label=f"{set_name} ({b})").save(out / "preview" / f"icons-{set_name}.png")
        print(f"icons/{set_name}: {len(ims)}")
    for theme in UI_THEMES:                                         # UI kit: PNG per frame/state + sheet per theme
        ims = []
        for stem, b, p in UI_SPECS:
            p = {**p, "theme": theme}
            frames, durs, tags = render(b, p)
            d = out / "ui" / theme
            d.mkdir(parents=True, exist_ok=True)
            names = [t["name"] for t in tags] if len(tags) == len(frames) else [str(i) for i in range(len(frames))]
            for i, f in enumerate(frames):
                fn = f"{stem}.png" if len(frames) == 1 else f"{stem}-{names[i]}.png"
                f.save(d / fn)
                manifest["icons"].append({"file": (d / fn).relative_to(out).as_posix(), "builder": b, "params": p, "frame": i})
            ims.append(frames)
        W = max(sum(f.width * 3 + 6 for f in fr) for fr in ims)
        H = sum(max(f.height for f in fr) * 3 + 6 for fr in ims) + 14
        sh = Image.new("RGBA", (W, H), (52, 60, 52, 255))
        ImageDraw.Draw(sh).text((4, 2), f"ui / {theme} (9-slice margin {__import__('artstudio.procedural._ui', fromlist=['x']).slice_margin(theme)} px)", fill=(230, 230, 230, 255))
        y = 14
        for fr in ims:
            x = 4
            for f in fr:
                sh.alpha_composite(f.resize((f.width * 3, f.height * 3), Image.NEAREST), (x, y)); x += f.width * 3 + 6
            y += max(f.height for f in fr) * 3 + 6
        sh.save(out / "preview" / f"ui-{theme}.png")
        print(f"ui/{theme}: {len(UI_SPECS)} pieces")
    for b in EFFECTS:
        colors = BUILDERS[b].PARAMS["color"]["enum"]
        tiles = [BUILDERS[b].PARAMS["tiles"]["default"]] + ([1] if BUILDERS[b].PARAMS["tiles"]["default"] == 3 else [])
        rows = []
        for t in tiles:
            for c in (colors if t == tiles[0] else colors[:1]):
                p = {"color": c, "tiles": t}
                frames, durs, tags = render(b, p)
                name = f"{b.replace('_', '-')}-{c}-{t}t"
                d = out / "effects" / name
                d.mkdir(parents=True, exist_ok=True)
                w, h = frames[0].size
                strip = Image.new("RGBA", (w * len(frames), h))
                for i, f in enumerate(frames):
                    strip.paste(f, (i * w, 0))
                strip.save(d / "strip.png")
                big = [f.resize((w * 3, h * 3), Image.NEAREST) for f in frames]
                big[0].save(d / "preview.gif", save_all=True, append_images=big[1:], duration=durs, loop=0, disposal=2)
                meta = {"builder": b, "params": p, "frame_size": [w, h], "frames": len(frames), "durations_ms": durs,
                        "tags": tags, "pivot": BUILDERS[b].pivot(**p), "loop": bool(getattr(BUILDERS[b], "LOOP", False)),
                        "grid": {"tile": 32, "cells": t, "ground_rect": [0, h - w, w, h]}}
                (d / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
                manifest["effects"].append({"dir": d.relative_to(out).as_posix(), **meta})
                rows.append(sheet(frames, len(frames), 2 if w > 64 else 3, bg=((74, 110, 58), (68, 102, 54)), label=name))
        W = max(r.width for r in rows)
        full = Image.new("RGBA", (W, sum(r.height for r in rows)), (24, 22, 30, 255))
        y = 0
        for r in rows:
            full.paste(r, (0, y)); y += r.height
        full.save(out / "preview" / f"effect-{b.replace('_', '-')}.png")
        print(f"effects/{b}: {len(rows)} variants")
    (out / "pack.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
