# AI Game Art Studio

[简体中文](README.zh-CN.md) · Version **0.2.0** ([CHANGELOG](CHANGELOG.md)) · Licence MIT

A **local-first studio for 2D game art**: pixel art and HD illustration, from a single icon to animated character
sprites, exported straight into game engines. It is a self-contained Python app (Pillow + numpy) with a web UI in
English and Chinese. It needs no cloud service, database or paid API.

![chest opening](deliverables/poc/contact_sheets/A_chest_open.png)

## What it can do

| Engine | Use it for | How |
|---|---|---|
| **A — Pixel engine** | Items, icons, skill effects, tiles, props, buildings, small animated sprites | Layered, deterministic, replayable drawing. Built-in builders or agent-written call lists. Runs offline. |
| **B — AI generation** | Detailed characters: master designs, directional views, action keyframes | Reference-driven generation through **ComfyUI** (your models and workflows). Codex optional. |
| **C — External assets** | Art you already have | Import PNG / sequences / sprite sheets / GIF / APNG / MP4 / WebM, then clean and align it. |

All three engines produce the **same asset format**, so everything below works on any asset:

- **Characters:** identity fields, side / 4 / 8 directions, candidate → approved **locked** master, history.
- **Animation editing:** playback, FPS, per-frame duration, onion skin, pivots, reorder / duplicate / replace frames,
  selective regeneration, events, effect layers, version snapshots.
- **Processing:** background removal, slicing, de-pixelation, group alignment (one scale per animation, ground anchors,
  airborne frames kept, canvas expanded instead of cropping weapons).
- **QA:** deterministic checks (size, clipping, background, jitter) kept separate from visual review.
- **Export:** PNG frames, sprite sheet, packed atlas, GIF / APNG, JSON, **Cocos Creator** plist, Phaser / PixiJS JSON,
  Godot helper, ZIP.

### Built-in Engine A builders

| Builder | Output | Params |
|---|---|---|
| `potion` | Fantasy potion flask (item) | `size`, `frames`, `liquid` red/blue/green/purple |
| `chest` / `chest_open` | Treasure chest; 8-frame opening animation | `size` |
| `fireball` | Looping projectile effect | `size`, `frames` |
| `sword_slash` | 8-frame slash effect | `size`, `color` azure/gold/crimson |
| `ice_spear` | Round skill icon | `size`, `element` ice/lightning/poison |
| `hero_shrine` | 96×96 Shrine of Heroes with animated braziers | `frames`, `banner` red/blue/green |

New assets don't need new code: an agent can write a call list and run `artstudio draw`. See
[docs/engine-a-guide.md](docs/engine-a-guide.md).

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

1. **Library:** create a project and pick its prompt language (English default, or Chinese).
2. Make art with one engine:
   - **Procedural Studio:** pick a builder, set params, run. Or replay a `.recipe`.
   - **Generation:** connect ComfyUI, import or check a workflow, create a character master, then generate keyframes.
   - **Import & Processing:** drop in files, slice, remove backgrounds, align the group.
3. **Animation Studio:** review frames, fix timing and pivots, run QA, approve.
4. **Export Studio:** choose formats (e.g. Cocos atlas + GIF) and download the ZIP.

The language switch (English / 中文) is in the top bar.

### From the command line (JSON output, for scripts and agents)

```bash
python -m artstudio project create "My RPG" --id my-rpg
python -m artstudio builders                                       # list builders and animation templates
python -m artstudio procedural hero_shrine --project my-rpg --params '{"banner":"blue"}'
python -m artstudio draw my_gem.jsonl --project my-rpg --name "Red Gem" --type icon
python -m artstudio import hero_walk.png --project my-rpg --opts '{"slicing":{"method":"grid","cols":8,"rows":1},"background":{"method":"auto"}}'
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --params '{"checkpoint":"<file>.safetensors"}'
python -m artstudio export --project my-rpg --assets <ids…> --formats atlas cocos gif json zip
```

- CLI messages in Chinese: `--lang zh-CN` or `ARTSTUDIO_LANG=zh-CN`.
- Config: `studio.config.example.json`, `.env.example`.
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

- ✅ **Offline (Stage A):** 65 automated tests (engine, pipeline, encoding, ComfyUI mock, server, CLI), Playwright UI
  test in English and Chinese, proof-of-concept build. Details in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).
- 🧪 **AI generation is mock-tested only.** Mock output is labelled TEST FIXTURE and is not AI art.
- ⛔ **Stage B (real ComfyUI inference) has not been run.** Run `scripts/production_smoke_test.py` on the ComfyUI PC.

## Layout

```
artstudio/    app: engine (Engine A), procedural (builders), pipeline, providers, processing, qa, export, server, web, schema
samples/      knight sample art (demonstration only, see samples/knight/NOTICE.md)
mock_comfyui/ offline ComfyUI API simulator (labelled test fixtures)
workflows/    ComfyUI templates · skills/ agent skills · examples/ Cocos Creator TS, Godot script
demo/         proof-of-concept builder · deliverables/ curated outputs · docs/ · scripts/ · tests/
```

## For contributors and agents

- Rules and gotchas: [AGENTS.md](AGENTS.md). Requirements: [SPECIFICATION.md](SPECIFICATION.md).
- Run tests: `python scripts/run_tests.py`.
- Release history: [CHANGELOG.md](CHANGELOG.md). Current version: [VERSION](VERSION).
