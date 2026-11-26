# AI Game Art Studio

[简体中文](README.zh-CN.md) · Version **0.4.0** ([CHANGELOG](CHANGELOG.md)) · Licence MIT

A **local-first studio for 2D game art**: pixel art and HD illustration, from a single icon to animated character
sprites, exported straight into game engines. It is a self-contained Python app (Pillow + numpy) with a web UI in
English and Chinese. It needs no cloud service, database or paid API.

![chest opening](deliverables/poc/contact_sheets/A_chest_open.png)

## What it can do

The studio has three tools. They all produce the **same asset format**, so editing, QA and export work on everything.

| Tool | Use it for | How |
|---|---|---|
| **🔥 Pixel Forge** | Skill effects, items, icons, props, scenery | Built-in pixel builders with a **live editor**: variant, size, speed, colours, outline, glow, flip, scale. Layered and replayable. Offline, no AI. |
| **🎬 Motion Studio** | A character's action frames: idle, walk, attack, custom moves | One reference image → actions → prompts → one sprite strip per action, drawn by the **Codex CLI** or your local **ComfyUI**. |
| **📥 Asset Import** | Art you already have | PNG / sequences / sprite sheets / GIF / APNG / MP4 / WebM: remove the background, slice, align. |

Shared features:

- **Characters:** identity fields, side / 4 / 8 directions, candidate → approved **locked** master, history.
- **Animation editing:** playback, FPS, per-frame duration, onion skin, pivots, reorder / duplicate / replace frames,
  selective regeneration, events, effect layers, version snapshots.
- **Processing:** background removal, slicing, de-pixelation, group alignment (one scale per animation, ground anchors,
  airborne frames kept, canvas expanded instead of cropping weapons).
- **QA:** deterministic checks (size, clipping, background, jitter) kept separate from visual review.
- **Export:** PNG frames, sprite sheet, packed atlas, GIF / APNG, JSON, **Cocos Creator** plist, Phaser / PixiJS JSON,
  Godot helper, ZIP.
- **Look:** English / 中文, and System / Dark / Light theme (top bar).

### Built-in Pixel Forge builders

| Builder | Output | Options (besides the editor's speed / colours / outline / glow / flip / scale) |
|---|---|---|
| `heal` | Healing: ground glow, light column, rising plus motes (loop) | `color` green/blue/gold, `frames` |
| `buff_aura` | Power-up ring at the feet, rising streaks and chevrons (loop) | `color` gold/red/purple, `frames` |
| `lightning_strike` | Bolt from the sky, impact flash, shock ring, sparks | `color` blue/purple/yellow, `thickness` 1–3 |
| `shield_barrier` | Hexagon bubble forms, shimmers, dissolves (see-through) | `color` azure/gold/green |
| `frost_nova` | Centre flash, outward ring of ice shards, snow | `color` ice/arcane/toxic |
| `poison_cloud` | Churning toxic cloud with popping bubbles and drips (loop) | `color` green/purple/orange, `frames` |
| `fireball` | Looping projectile | `size`, `frames` |
| `sword_slash` | 8-frame crescent slash | `color` azure/gold/crimson, `thickness` 0.5–1.6 |
| `ice_spear` | Round skill icon | `size`, `element` ice/lightning/poison |
| `potion` | Fantasy potion flask (item) | `size`, `frames`, `liquid` red/blue/green/purple |
| `chest` / `chest_open` | Treasure chest; 8-frame opening animation | `size` |
| `hero_shrine` | 96×96 Shrine of Heroes with animated braziers | `frames`, `banner` red/blue/green |

New assets don't need new code: an agent can write a call list and run `artstudio draw`. See
[docs/pixel-forge-guide.md](docs/pixel-forge-guide.md).

## Quick start

Requirements: **Python 3.10+**. Optional: **ffmpeg** (video import), **ComfyUI** (AI generation).

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\start.ps1      # creates .venv, installs, opens http://127.0.0.1:8870
```
```bash
# Linux / macOS
./start.sh                                                # --port 8870 --workspace DIR --comfy http://127.0.0.1:8188
```

Manual install: `python -m venv .venv`, then `.venv/bin/pip install -r requirements.txt`, then
`.venv/bin/python -m artstudio serve`.

## How to use

### In the web studio (http://127.0.0.1:8870)

The home page has three entry points, one per tool.

**🎬 Motion Studio** — animate a character in five steps:

1. **Character**: name, art style, side or top-down view, and **one reference image** (locked as the master).
2. **Actions**: click presets (idle, walk, run, attack, cast, jump, hit, death …) or add a **custom action** and
   describe it in one line, e.g. "swings the sword overhead and slams it down". Set frames, loop and facing.
3. **Prompts**: **✨ Write with Codex** looks at the reference image and writes the character description, the
   frame-by-frame poses and a prompt per action. Or use the built-in template. Everything is editable.
4. **Generate**: pick **Codex CLI** or **Local ComfyUI** (workflow, checkpoint, denoise). Each action becomes one
   sprite strip, which is sliced into frames and aligned (one scale, one ground line).
5. **Review & export**: watch each animation, click a frame to redo just that frame, approve, and export for
   Cocos Creator, Godot, Phaser/PixiJS or plain PNG/GIF.

**🔥 Pixel Forge** — pick a builder on the left, watch the live preview, adjust on the right:

| Section | Controls |
|---|---|
| Variant | the builder's own options (colour scheme, size, frames, thickness …) |
| Timing | speed 0.25×–3×, loop |
| Colours | edit any palette colour, or shift hue / saturation / brightness of the whole palette |
| Outline & glow | outline 0–3 px + colour, dithered glow 0–4 px + colour, flip, output scale 1×–4× |
| Save | save to the library, or save & export (PNG frames, sheet, GIF, JSON, Cocos, ZIP) |

Edits are stored with the asset and recorded as pixel-engine calls, so saved assets replay exactly and can be
reopened in the Forge ("Saved in this project").

**📥 Asset Import** — drop files, choose slicing / background / alignment, import.

Expert tools are under **More tools**: frame-level **Animation editor**, **Character details**, **Generation &
workflows** (ComfyUI) and **Pixel documents** (recipes, layers, cels).

### From the command line (JSON output, for scripts and agents)

```bash
python -m artstudio project create "My RPG" --id my-rpg
python -m artstudio builders                                       # list builders and animation templates
python -m artstudio procedural hero_shrine --project my-rpg --params '{"banner":"blue"}'
python -m artstudio procedural heal --project my-rpg --params '{"color":"gold"}' --edits '{"speed":1.5,"outline":1,"glow":2}'
# Motion Studio (character animation)
python -m artstudio animate new --project my-rpg --name "Fire Knight" --image knight.png --view side
python -m artstudio animate add --project my-rpg --character <cid> --preset attack
python -m artstudio animate add --project my-rpg --character <cid> --name "Spin slash" --description "spins once with the sword out" --frames 6
python -m artstudio animate prompts --project my-rpg --character <cid> --method codex      # or --method template
python -m artstudio animate generate --project my-rpg --character <cid> --provider codex   # or comfyui --params '{"checkpoint":"<file>"}'
python -m artstudio draw my_gem.jsonl --project my-rpg --name "Red Gem" --type icon
python -m artstudio import hero_walk.png --project my-rpg --opts '{"slicing":{"method":"grid","cols":8,"rows":1},"background":{"method":"auto"}}'
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --params '{"checkpoint":"<file>.safetensors"}'
python -m artstudio export --project my-rpg --assets <ids…> --formats atlas cocos gif json zip
```

- CLI messages in Chinese: `--lang zh-CN` or `ARTSTUDIO_LANG=zh-CN`.
- Config: `studio.config.example.json`, `.env.example`. Codex CLI: install, `codex login`, and it is found on PATH
  (or set `codex_bin`).
- Windows + ComfyUI setup: [docs/deployment-windows.md](docs/deployment-windows.md).

### Bundled ComfyUI workflow templates

`workflows/comfyui/`: text-to-image, image-to-image, character reference, pose keyframe, inpaint, SVD image-to-video,
background removal (rembg). They are **unverified** until tested on a real ComfyUI server (Stage B). You can import
your own workflows from the UI or CLI.

## Based on

This repo is self-contained: it holds no other project's git checkout. It builds on two MIT projects:

| Upstream | What we took | Where it lives now |
|---|---|---|
| **[Atelier](https://github.com/marmikshah/atelier)** (Marmik Shah), commit `8ac6adf` | Tool-call format, document / recipe layout, drawing semantics | `artstudio/engine`: our own Python re-implementation (no Rust). Atelier recipes replay **pixel-identical**. |
| **[Pixel Atelier](https://github.com/jinxingtaire/pixel-atelier)** (Pixel Character Pipeline contributors), commit `15d199f` | Sprite pipeline, Chinese sheet prompts, Codex client, knight sample | `artstudio/pipeline/spritepipe.py`, `artstudio/prompts_zh_sheet.py`, `artstudio/providers/codex_rpc.py`, `samples/knight/`. Rewritten for UTF-8 on GBK/cp936 systems. |

AI generation talks to the **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** server API. No ComfyUI code is
included. Licences and derived-file list: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Verification status

- ✅ **Offline (Stage A):** 84 automated tests (engine, pipeline, encoding, action plans, ComfyUI mock, Codex test double, server,
  CLI), Playwright UI test of the whole guided flow in English and Chinese, proof-of-concept build. Details in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).
- 🧪 **AI generation is mock-tested only**: ComfyUI against `mock_comfyui/`, Codex against a test double
  (`tests/fake_codex.py`). Mock output is labelled TEST FIXTURE and is not AI art. The real Codex CLI has not been run here.
- ⛔ **Stage B (real ComfyUI inference) has not been run.** Run `scripts/production_smoke_test.py` on the ComfyUI PC.

## Layout

```
artstudio/    app: engine (Pixel Forge), procedural (builders), pipeline, providers, processing, qa, export, server, web, schema
samples/      knight sample art (demonstration only, see samples/knight/NOTICE.md)
mock_comfyui/ offline ComfyUI API simulator (labelled test fixtures)
workflows/    ComfyUI templates · skills/ agent skills · examples/ Cocos Creator TS, Godot script
demo/         proof-of-concept builder · deliverables/ curated outputs · docs/ · scripts/ · tests/
```

## For contributors and agents

- Rules and gotchas: [AGENTS.md](AGENTS.md). Requirements: [SPECIFICATION.md](SPECIFICATION.md).
- Run tests: `python scripts/run_tests.py`.
- Release history: [CHANGELOG.md](CHANGELOG.md). Current version: [VERSION](VERSION).
