"""Export the character kit (Craftpix base + class costumes) as game-ready sprite sheets.

    python scripts/make_character_pack.py [--out assets_local/character_pack] [--presets knight,mage] [--scale 3]

Writes, per preset (the plain base as base_male and base_female):
  <preset>/<Action>.png      sprite sheet, 64×64 cells, rows = front, side_left, side_right, back
  <preset>/<Action>.gif      upscaled preview, the four facings side by side
  <preset>/meta.json         base, outfit, per-action frame counts / durations (ms) / loop, pivot (feet)
  lineup.png                 every preset, four facings, idle frame
The output contains Craftpix art, so it goes to a git-ignored folder by default: use it in your game, do not
redistribute it (Craftpix free licence)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from artstudio.charkit import (
    ALL_ACTIONS,
    DIRS,
    FEET,
    PRESETS,
    is_loop,
    outfit_for,
    render,
)
from artstudio.charkit.costume import flatten

BG = (58, 64, 78, 255)


def _timeline(frames, ms, tick):
    seq = []
    for f, d in zip(frames, ms):
        seq += [f] * max(1, round(d / tick))
    return seq


def gif(path: Path, rows: dict, ms: dict, scale: int, tick: int = 50):
    """Facings can differ in frame count / timing (back idle has 4 frames, the others 12): play each on its own
    timeline at a common tick and loop over the least common multiple."""
    seqs = {d: _timeline(rows[d], ms[d], tick) for d in DIRS}
    n = 1
    for v in seqs.values():
        n = n * len(v) // math.gcd(n, len(v))
    n = min(n, 400)
    pad = 4
    W = len(DIRS) * (64 * scale + pad) + pad
    frames = []
    for i in range(n):
        im = Image.new("RGBA", (W, 64 * scale + 2 * pad), BG)
        for j, d in enumerate(DIRS):
            f = seqs[d][i % len(seqs[d])].resize((64 * scale, 64 * scale), Image.NEAREST)
            im.alpha_composite(f, (pad + j * (64 * scale + pad), pad))
        frames.append(im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255))
    # merge identical consecutive frames back into longer durations
    out, durs = [], []
    for f in frames:
        if out and f.tobytes() == out[-1].tobytes():
            durs[-1] += tick
        else:
            out.append(f); durs.append(tick)
    out[0].save(path, save_all=True, append_images=out[1:], duration=durs, loop=0, disposal=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "assets_local" / "character_pack")
    ap.add_argument("--presets", default=",".join(PRESETS))
    ap.add_argument("--actions", default=",".join(ALL_ACTIONS))
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--no-gif", action="store_true")
    a = ap.parse_args(argv)
    jobs = []   # (folder, preset, base) — the plain base is exported for both sexes
    for p in (x for x in a.presets.split(",") if x):
        jobs += [("base_male", p, "male"), ("base_female", p, "female")] if p == "base" else [(p, p, None)]
    actions = [x for x in a.actions.split(",") if x]
    lineup = Image.new("RGBA", (64 * len(DIRS), 64 * len(jobs)))
    for pi, (folder, p, want) in enumerate(jobs):
        sex, outfit = outfit_for(p, want)
        out = a.out / folder
        out.mkdir(parents=True, exist_ok=True)
        meta = {"preset": p, "base": sex, "outfit": outfit, "frame_size": [64, 64], "pivot": list(FEET),
                "rows": DIRS, "actions": {}}
        for act in actions:
            frames, ms = render(p, act, sex)
            rows = {d: [flatten(g) for g in frames[d]] for d in DIRS}
            cols = max(len(v) for v in rows.values())
            sheet = Image.new("RGBA", (64 * cols, 64 * len(DIRS)))
            for r, d in enumerate(DIRS):
                for c, f in enumerate(rows[d]):
                    sheet.alpha_composite(f, (64 * c, 64 * r))
            sheet.save(out / f"{act}.png")
            if not a.no_gif:
                gif(out / f"{act}.gif", rows, ms, a.scale)
            meta["actions"][act] = {"frames": {d: len(rows[d]) for d in DIRS}, "durations": ms, "loop": is_loop(act)}
            if act == "Sword_Idle":
                for j, d in enumerate(DIRS):
                    lineup.alpha_composite(rows[d][0], (64 * j, 64 * pi))
        (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(f"{folder}: {len(actions)} actions → {out}")
    lineup.resize((lineup.width * a.scale, lineup.height * a.scale), Image.NEAREST).save(a.out / "lineup.png")


if __name__ == "__main__":
    main()
