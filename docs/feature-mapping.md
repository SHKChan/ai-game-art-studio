# Feature mapping

Legend — **A**: Atelier-compatible (own re-implementation of its call format) · **P**: derived from Pixel Atelier code (moved into `artstudio/`) · **N**: new ·
Status: ✅ implemented & tested offline · 🧪 mock-tested only · ⛔ blocked here (needs Stage B) · ⚠ experimental/unverified

| Spec area | Feature | Source | Where | Status |
|---|---|---|---|---|
| Engine A | Layered procedural drawing, palette, frames, export | A | `artstudio/engine` (own Python engine) | ✅ Atelier recipes replay pixel-identical |
| Engine A | Deterministic builders: potion, chest, chest_open, fireball, sword_slash, ice_spear | N | `procedural/*.py` | ✅ |
| Engine A | Agent call lists (`artstudio draw`) + authoring guide | N | `docs/engine-a-guide.md` | ✅ |
| Engine A | Replayable recipes / editable documents | A | `doc.recipe`, `replay` command | ✅ pixel-identical replay tested |
| Engine A | Document inspector (layers, cels, palette, calls) | N | Procedural Studio | ✅ |
| Engine B | Reference-driven generation with identity constraints | N (rules from P) | `prompts.py`, `service.generate` | 🧪 (mock ComfyUI) |
| Engine B | ComfyUI provider (HTTP+WS, upload, validation, queue, cancel, timeouts) | N | `providers/comfyui.py`, `comfy/` | 🧪 |
| Engine B | Codex image bridge | P | `providers/codex_rpc.py` | ⛔ optional, codex CLI absent |
| Engine B | Candidates / rejected versions / approved & locked masters | N (concept from P) | `workspace.py` | ✅ |
| Engine B | Selective regeneration of one frame | N | `service.regenerate_frame` | 🧪 |
| Engine B | Real AI art through the pipeline | P (knight sample) | `import_knight_sample` | ✅ (sample art, not generated here) |
| Engine C | PNG, PNG sequence, sprite sheet (grid/auto), GIF/APNG/WebP | N | `processing/importers.py`, `frames.py` | ✅ |
| Engine C | MP4/WebM via ffmpeg | N | `extract_video` | ✅ (ffmpeg present in test envs) |
| Engine C | Background removal (solid/checker, pixel binary / HD soft) | N | `remove_background` | ✅ |
| Engine C | Complex-background matting | N (ComfyUI workflow) | `rembg-inspyrenet` template | ⚠ unverified custom node |
| Providers | Runtime availability, no silent substitution | N | `providers/__init__.py` | ✅ |
| Providers | Mock provider (fixtures, labelled) | N | `MockGenerationProvider`, `mock_comfyui/` | ✅ |
| Characters | ID, identity fields, palette, constraints, negatives, history | N | `schema/character.schema.json` | ✅ |
| Characters | side2 / four / eight directions; optional mirroring | N | `workspace.DIRECTION_SETS` | ✅ |
| Animation | 12 action templates with poses/phases/events | N (phases from P workflow) | `animation.TEMPLATES` | ✅ |
| Animation | reorder/duplicate/delete/replace/durations/loop/events/phase/airborne/nudge | N | `animation.edit_frames` | ✅ |
| Animation | Body/weapon/effect layers with independent timing | N | `add_layer`, composite preview | ✅ |
| Modes | Pixel: nearest, palette, binary alpha, integer placement | N (P rules) | `normalize_group`, `apply_palette` | ✅ |
| Modes | HD: Lanczos premultiplied, partial alpha, no quantization | N | `resample`, HD keying | ✅ |
| Alignment | One group scale; source/ground/support-foot/torso anchors; airborne; canvas expansion; offsets recorded | N (rules from P) | `processing/frames.py` | ✅ |
| UI | Library, Character, Animation, Procedural, Import, Generation, Export studios; jobs dock; dark/light | N | `artstudio/web/` | ✅ Playwright |
| Schema | Versioned asset/character/workflow JSON Schemas + validator | N | `artstudio/schema/` | ✅ |
| Persistence | Atomic JSON, version snapshots, backup/restore, migration hook | N | `workspace.py` | ✅ |
| Agents | 14 skills | N (adapted from A skills + P docs) | `skills/` | ✅ written |
| Agents | CLI with JSON output | N | `artstudio/cli.py` | ✅ |
| Jobs | Async queue, progress, cancel, retry, resume, budget | N | `jobs.py` | ✅ |
| QA | 13 deterministic checks + export checks | N (+P spritepipe) | `qa/`, `pipeline/spritepipe.py` | ✅ |
| i18n | English / Chinese UI, CLI/API messages, prompts, user docs | N | `web/i18n.js`, `i18n.py`, `prompts.py` | ✅ Playwright zh pass |
| Encoding | UTF-8 everywhere; GBK/cp1252/C-locale safe | N | all modules | ✅ test_encoding |
| QA | Probabilistic visual review (recorded separately) | N | `qa/visual.py` | ✅ manual; no model bundled |
| Export | PNG frames, sheets, packed atlas, GIF, APNG, JSON | N | `export/` | ✅ |
| Export | Cocos Creator 3.x plist + TS animator/controller | N | `export`, `examples/cocos-creator` | ✅ files; ⚠ TS not run in Creator |
| Export | Phaser/PixiJS (TexturePacker JSON-hash), Godot script, Unity JSON | N | `export`, `examples/godot` | ✅ files; ⚠ not run in engines |
