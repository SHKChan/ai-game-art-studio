"""Sample data and pipeline helpers (all local — no upstream checkout needed).

  * `samples/knight` — whole-character knight sample from Pixel Atelier (see samples/knight/NOTICE.md):
    genuine AI-generated art (Codex built-in imagegen, processed by Pixel Atelier), demonstration use.
  * `artstudio.pipeline.spritepipe` — whole-character build/check pipeline (derived from Pixel Atelier).
  * `artstudio.prompts_zh_sheet` — the 8-action Chinese sheet prompt (derived from Pixel Atelier).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

from .config import APP_ROOT
from .util import StudioError

KNIGHT = APP_ROOT / "samples" / "knight"


def available() -> bool:
    return (KNIGHT / "manifest.json").is_file()


def spritepipe():
    from .pipeline import spritepipe as core
    return core


def sheet_steps() -> dict:
    """8 ordered actions with Chinese motion briefs, default durations and loop flags."""
    from .prompts_zh_sheet import STEPS
    return {k: {"label": v[0], "motion": v[1], "durations": v[2], "loop": v[3]} for k, v in STEPS.items()}


def sheet_prompt_zh(name: str, action: str, identity: str = "", weapon: str = "", style: str = "", note: str = "") -> str:
    from .prompts_zh_sheet import generation_prompt
    return generation_prompt({"name": name, "spec": {"identity": identity, "weapon": weapon, "style": style}}, action, note)


# backwards-compatible names
pixel_atelier_steps = sheet_steps
pixel_atelier_prompt = sheet_prompt_zh


def knight_actions() -> list[dict]:
    m = KNIGHT / "manifest.json"
    if not m.exists():
        raise StudioError("samples/knight is missing", code="sample_missing")
    data = json.loads(m.read_text(encoding="utf-8"))
    for a in data:
        a["atlas_path"] = str(KNIGHT / a["id"] / "atlas.png")
    return data


def knight_frames(action: str) -> tuple[list[Image.Image], list[int], dict]:
    """Slice a knight sample atlas using its manifest rects (exact)."""
    meta = next((a for a in knight_actions() if a["id"] == action), None)
    if not meta:
        raise StudioError(f"Unknown knight action {action}")
    with Image.open(meta["atlas_path"]) as im:
        atlas = im.convert("RGBA")
    frames, durs = [], []
    for f in meta["frames"]:
        x, y, w, h = f["rect"]
        frames.append(atlas.crop((x, y, x + w, y + h)))
        durs.append(int(f["duration_ms"]))
    return frames, durs, meta


def spritepipe_verify(frames: list[Image.Image], durations: list[int], pivot, workdir: Path, action: str = "anim",
                      palette: list[str] | None = None) -> dict:
    """Run the whole-character spritepipe build+check on pixel-mode frames. Returns its QA report."""
    core = spritepipe()
    workdir = Path(workdir)
    if workdir.exists():
        raise StudioError("spritepipe workdir must not exist")
    (workdir / "source").mkdir(parents=True)
    w, h = frames[0].size
    cols = 4
    rows = math.ceil(len(frames) / cols)
    pad = 2  # source poses must not touch their cell edge (pipeline rule)
    cw, ch = w + 2 * pad, h + 2 * pad
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, ((i % cols) * cw + pad, (i // cols) * ch + pad))
    sheet.save(workdir / "source" / f"{action}.png")
    if palette is None:
        cols_ = set()
        for f in frames:
            cols_.update(p[:3] for p in f.getdata() if p[3] >= 220)
        if len(cols_) > 255:
            raise StudioError("spritepipe needs <=255 colours; quantize the animation first (pixel mode palette)")
        palette = ["#%02x%02x%02x" % c for c in sorted(cols_)]
    durs = [max(10, int(round(d / 10.0)) * 10) for d in durations]
    profile = {"schema_version": "0.1", "id": action, "character_revision": "artstudio", "weapon_revision": "artstudio",
               "route": "whole_character", "palette": {"status": "frozen", "colors": palette},
               "actions": {action: {"source": f"source/{action}.png", "grid": [cols, rows], "source_scale": 1,
                                    "frame_size": [cw, ch], "pivot": [pivot[0] + pad, pivot[1] + pad],
                                    "offsets": [[0, 0]] * len(frames), "durations_ms": durs, "alpha_threshold": 220,
                                    "preview_scale": 2, "safety_margin_px": 1, "loop_preview": True, "loop_runtime": True,
                                    "boundary_equal": False, "events": {}}}}
    (workdir / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    try:
        return core.build_project(str(workdir))
    except core.PipelineError as e:
        return {"status": "FAIL", "error": str(e), "scope": "spritepipe build refused the input"}
