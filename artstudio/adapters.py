"""Adapters to Pixel Atelier (upstream/pixel-atelier, used unmodified):

  * spritepipe (portable whole-frame build + technical checker) — `spritepipe_verify()` builds a
    Pixel Atelier profile from one of our pixel-mode animations and runs upstream build/check,
    returning its TECHNICAL_VERIFIED / FAIL report.
  * bridge/production.py — the 8-action character workflow (STEPS, durations, prompt structure);
    `pixel_atelier_steps()` and `pixel_atelier_prompt()` expose them for Engine B.
  * examples/knight — genuine AI-generated (Codex imagegen, per upstream README) whole-character
    animation set used as real Engine B input when no generator is available offline.
"""
from __future__ import annotations

import json
import math
import sys
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

from .config import UPSTREAM
from .util import StudioError

PA = UPSTREAM / "pixel-atelier"


@contextmanager
def _upstream_path(*parts):
    p = str(PA.joinpath(*parts))
    sys.path.insert(0, p)
    try:
        yield
    finally:
        try:
            sys.path.remove(p)
        except ValueError:
            pass


def available() -> bool:
    return (PA / "spritepipe" / "core.py").exists()


def spritepipe():
    with _upstream_path():
        import spritepipe.core as core  # type: ignore
    return core


def pixel_atelier_steps() -> dict:
    """Upstream action order, motion briefs (zh), default durations and loop flags."""
    with _upstream_path("bridge"):
        import production  # type: ignore
    return {k: {"label": v[0], "motion": v[1], "durations": v[2], "loop": v[3]} for k, v in production.STEPS.items()}


def pixel_atelier_prompt(name: str, action: str, identity: str = "", weapon: str = "", style: str = "", note: str = "") -> str:
    """Upstream prompt (Chinese) for a 4x2 whole-character pose sheet, unmodified wording."""
    with _upstream_path("bridge"):
        import production  # type: ignore
    project = {"name": name, "spec": {"identity": identity, "weapon": weapon, "style": style}}
    return production.generation_prompt(project, action, note)


def knight_actions() -> list[dict]:
    m = PA / "examples" / "knight" / "manifest.json"
    if not m.exists():
        raise StudioError("upstream/pixel-atelier/examples/knight missing")
    data = json.loads(m.read_text(encoding="utf-8"))
    for a in data:
        a["atlas_path"] = str(PA / "examples" / "knight" / a["id"] / "atlas.png")
    return data


def knight_frames(action: str) -> tuple[list[Image.Image], list[int], dict]:
    """Slice an upstream knight atlas using its manifest rects (exact)."""
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
    """Run Pixel Atelier's spritepipe build+check on pixel-mode frames. Returns the upstream QA report."""
    core = spritepipe()
    workdir = Path(workdir)
    if workdir.exists():
        raise StudioError("spritepipe workdir must not exist")
    (workdir / "source").mkdir(parents=True)
    w, h = frames[0].size
    cols = 4
    rows = math.ceil(len(frames) / cols)
    pad = 2  # source poses must not touch their cell edge (upstream rule)
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
