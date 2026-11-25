# AI Game Art Studio

A local-first production studio for 2D game art — pixel art and HD illustration — that integrates two
open-source projects through adapters:

- **[Atelier](upstream/atelier)** (Rust, MIT) — headless, layered, agent-driven pixel-art editor → *Engine A: procedural art*
- **[Pixel Atelier](upstream/pixel-atelier)** (Python, MIT) — whole-character animation workflow and checker → *rules, prompts, verifier and sample art for Engine B*

plus **ComfyUI** as the primary AI image backend (Engine B) and a full **external-asset pipeline** (Engine C).

![procedural assets](deliverables/poc/contact_sheets/A_chest_open.png)

## What you can do

| Workspace | Functions |
|---|---|
| Library | projects, characters, assets with filters, status/fixture badges, Pixel Atelier knight sample |
| Character Studio | identity (description, proportions, clothing, weapon, palette, must-keep / negative constraints), side/4/8 directions, optional mirroring, candidates → approve → **locked** masters, explicit replace/unlock with reason, history, direction-matrix check |
| Animation Studio | playback, FPS, per-frame durations, loop, stepping, zoom, backgrounds/checkerboard, onion skin, ground line, pivot editing, frame comparison & before/after, drag-reorder, duplicate, delete, reject/restore, nudge, airborne, phases, events, manual replacement, selective regeneration, effect layers, QA, visual review, approve/reject, version restore |
| Procedural Studio | run Atelier builders (potion, chest, chest opening, fireball, sword slash), replay `.recipe` files, inspect the Atelier document (palette, layers, frames, cels, call log) |
| Import & Processing | drag-and-drop PNG / sequences / sprite sheets (grid or auto) / GIF / APNG / MP4 / WebM, background removal (solid, checkerboard; pixel or soft HD), de-pixelation, group normalization with anchors, before/after |
| Generation | runtime provider status, ComfyUI workflow templates (check against server, import API-format JSON), keyframe generation, prompt preview, batches with an explicit budget |
| Export Studio | PNG frames, sprite sheets, packed atlas, GIF + APNG previews, composite layer preview, JSON metadata, Cocos Creator 3.x plist, Phaser/PixiJS atlas JSON, Godot helper, ZIP |

Agents get the same features through a JSON CLI (`python -m artstudio …`) and 14 production skills in `skills/`.

## Install & launch

Requirements: Python 3.10+, optional Rust (to build Atelier) and ffmpeg (video import). No cloud service, database or
paid API is required; the app works fully with ComfyUI offline.

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-atelier.ps1   # once, needs Rust (https://rustup.rs)
powershell -ExecutionPolicy Bypass -File .\start.ps1                    # creates .venv, installs, opens http://127.0.0.1:8870
```

**Linux / macOS**
```bash
./scripts/build-atelier.sh      # once
./start.sh                      # --port 8870 --workspace DIR --comfy http://127.0.0.1:8188
```

Manual: `python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m artstudio serve`.

Configuration: `studio.config.example.json`, `.env.example` (workspace path, port, ComfyUI URL/timeout, Atelier and
ffmpeg paths). Generated assets live in the workspace (default `./workspace`, git-ignored; point it elsewhere for production).
Full Windows/ComfyUI guide: **[docs/deployment-windows.md](docs/deployment-windows.md)**.

## Using it

1. **Create a project** (Library) — pick pixel or HD as default style.
2. **Procedural assets**: Procedural Studio → choose a builder → *Run with Atelier*. The layered Atelier document and its
   replayable recipe are kept with the asset.
3. **Characters**: Character Studio → new character (directions, style, identity) → upload or generate candidates →
   approve per direction (locks the master).
4. **Animations**: Generation (ComfyUI) or Import a sheet/GIF/video → Animation Studio to review, align, mark events,
   fix frames, attach effect layers → approve.
5. **Export**: Export Studio → select animations and formats → download ZIP. For Cocos Creator use the `cocos/` folder
   with `examples/cocos-creator/DirectionalSpriteAnimator.ts`.

CLI examples:
```bash
python -m artstudio project create "My RPG" --id my-rpg
python -m artstudio procedural fireball --project my-rpg
python -m artstudio import hero_walk.png --project my-rpg --opts '{"slicing":{"method":"grid","cols":8,"rows":1},"background":{"method":"auto"},"anim_name":"walk","direction":"east"}'
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --params '{"checkpoint":"<file>.safetensors"}'
python -m artstudio draw my_icon_calls.jsonl --project my-rpg --name "Ice Spear Icon" --type icon   # any agent-authored Atelier drawing
python -m artstudio export --project my-rpg --assets <ids…> --formats atlas cocos gif json zip
```

## ComfyUI

Primary generation backend, model-agnostic. Import any workflow exported in **API format**; the studio derives
parameter mappings, validates nodes and model files against the live server (`/object_info`) before each run, uploads
references, streams progress over the WebSocket (falls back to polling), retrieves outputs, supports cancel/timeouts,
and stores full generation metadata. Bundled core-node templates: text-to-image, image-to-image, character reference,
pose keyframe (ControlNet), inpainting, image-to-video (SVD) and background removal (custom node). **All are
`unverified` until tested on a real server (Stage B).** For offline development, `mock_comfyui/server.py` implements
the same API with clearly labelled test fixtures.

## Verification status (honest summary)

- ✅ Offline engineering acceptance (Stage A): 43 studio tests, 41 Pixel Atelier tests, 378 Atelier Rust tests,
  100/100 Atelier showcase replays, Playwright UI smoke test, proof-of-concept build — see
  [docs/IMPLEMENTATION_REPORT.md](docs/IMPLEMENTATION_REPORT.md) and [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).
- 🧪 AI generation paths are **mock-tested only**. ⛔ **Stage B (real ComfyUI inference) has not been run.**
- Proof-of-concept deliverables: [deliverables/poc](deliverables/poc) (Atelier assets with editable documents and recipes,
  processed genuine AI-generated knight animations from Pixel Atelier, external GIF/sheet/video processing, hybrid
  character + effect, engine exports).

## Repository layout

```
artstudio/            application (service, providers, processing, qa, export, server, web UI, schemas, procedural builders)
mock_comfyui/         offline ComfyUI API simulator (test fixtures only)
workflows/comfyui/    bundled workflow templates (generated by scripts/make_workflow_templates.py)
skills/               14 agent skills
examples/             Cocos Creator TypeScript, Godot 4 script
demo/build_poc.py     builds the proof-of-concept project
deliverables/poc/     proof-of-concept outputs (exports, contact sheets, report)
docs/                 research, architecture, schema, deployment, implementation report
scripts/              build-atelier, run_tests, production_smoke_test, make_workflow_templates
tests/                unit, integration and Playwright UI tests
upstream/             Atelier and Pixel Atelier (unmodified)
```

## Licences

Studio code: MIT (see `LICENSE`). Upstream projects keep their own MIT licences — see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Sample art from upstream (knight, showcase GIFs) is used for
demonstration under those licences and is attributed wherever it appears.
