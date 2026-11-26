# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/). The current version is in [VERSION](VERSION).

## [Unreleased]

## [0.4.0] — 2026-11-26

Tools get names, Pixel Forge gets a live editor and six skill effects, and the UI gets a theme choice.

### Added
- **Names for the three tools:** Engine A → **Pixel Forge** (像素工坊), Engine B → **Motion Studio** (动作工作室),
  Engine C → **Asset Import** (素材导入) — in the UI, docs, skills and code comments. Older entries below keep the old names.
- **Pixel Forge editor** (`web/forge.js`): builder gallery with thumbnails, live animated preview (zoom, background,
  frame stepping), and controls for variant options, speed (0.25×–3×), loop, per-colour palette editing, hue /
  saturation / brightness, outline 0–3 px + colour, dithered glow 0–4 px + colour, flip, output scale 1×–4×; save to
  the library or save & export; reopen saved assets ("Saved in this project").
- **Edits are replayable** (`procedural/edits.py`): stored on the asset (`procedural.edits`) and recorded as engine calls.
  CLI: `artstudio procedural <builder> --edits '{...}'`. API: `/api/forge/builders`, `/api/forge/preview`, `/api/forge/thumb/<b>.png`.
- **Six skill effects** (64×64, 8 frames, colour variants): `heal`, `buff_aura`, `lightning_strike`, `shield_barrier`,
  `frost_nova`, `poison_cloud` (+ shared helpers `procedural/_fx.py`).
- `thickness` option for `sword_slash` and `lightning_strike`; builders declare `LOOP`.
- **Theme selector:** System / Dark / Light, remembered per browser; System follows the OS setting.
- Tests: `tests/test_forge.py` (6); Playwright covers the Forge editor (variant, speed, colours, outline, glow, save &
  export), the theme selector and the renamed navigation in English and Chinese.

### Changed
- Navigation: Home · Motion Studio · Pixel Forge · Asset Import · Library · Export; the former Procedural Studio is
  **More tools → Pixel documents** (recipes, layers, cels).
- `docs/engine-a-guide.md` → `docs/pixel-forge-guide.md`.

## [0.3.0] — 2026-11-26

Engine B becomes the character-animation engine; the UI becomes a guided flow.

### Added
- **Animate a character** (guided flow): Character (one reference image) → Actions → Prompts → Generate → Review & export.
- **Action plans** (`artstudio/actions.py`, `characters/<id>/action_plan.json`): preset actions (idle, walk, run, attack,
  combo, cast, dodge, dash, jump, hit, death, interact) or custom actions described in one line; frames, loop, facing.
- **Prompt writing**: Codex CLI reads the reference image and writes the character description + frame-by-frame poses
  + one strip prompt per action (`codex exec`, `artstudio/codex_cli.py`); built-in template fallback (English / Chinese).
  Everything is editable before generation.
- **Strip generation** — every frame of an action in one image, then sliced, aligned and stored as an animation:
  - Codex CLI (`codex app-server` built-in image generation, reference attached).
  - Local ComfyUI: the reference repeated across the strip and redrawn per pose (img2img, `sd-character-reference`).
  - Slicing falls back to an even grid (with a warning) when sprites are not separated.
- Redo a single frame from the review screen (action-aware frame prompt); export presets for Cocos / Godot / Phaser / PNG.
- Home page with three entry points (Animate character, Pixel assets, Import) and "Continue" for each character.
- API: `/api/action-presets`, `characters/from-reference`, `characters/<id>/reference`, `characters/<id>/plan[/prompts|/generate]`.
- CLI: `artstudio animate new|add|remove|show|prompts|generate`.
- Config: `codex_bin`, `codex_timeout` (env `ARTSTUDIO_CODEX`).
- Tests: `tests/test_actions.py` (13), `tests/fake_codex.py` (Codex CLI test double); Playwright test drives the whole guided flow.

### Changed
- Navigation: Home · Animate character · Pixel assets · Import · Library · Export; the expert tabs (Animation editor,
  Character details, Generation & workflows) moved under **More tools**.
- Jobs panel folds away when nothing is running, so it no longer covers buttons.
- Codex provider: resolves `codex.cmd` on Windows, configurable command, errors reported as generation errors.
- Selective frame regeneration works for custom actions (no preset template needed).

## [0.2.0] — 2026-11-26

Self-contained studio: no upstream checkouts, own pixel engine, bilingual UI.

### Added
- **Engine A**: own Python pixel engine (`artstudio/engine`) with Atelier's tool-call format. Atelier showcase recipes
  and reference renders replay pixel-identical.
- `artstudio draw`: run agent-written call lists (JSON array or JSONL, `"$DOC"` placeholder) without writing a builder.
- Builders `ice_spear` (ice / lightning / poison skill icon) and `hero_shrine` (96×96 Shrine of Heroes, animated
  braziers, banner colour).
- **Chinese / English** support: UI dictionary and language switch, localized server and CLI errors (`--lang`,
  `ARTSTUDIO_LANG`), per-project prompt language, Chinese README and Windows deployment guide.
- `docs/engine-a-guide.md` and `skills/procedural-builder-authoring` for authoring new Engine A assets.
- Encoding tests (`tests/test_encoding.py`): no locale-default I/O; full Chinese CLI flow under the C locale.
- 14 Pixel Atelier pipeline tests ported (`tests/test_spritepipe.py`).
- `VERSION`, `CHANGELOG.md`; README sections on features, usage and upstream projects.

### Changed
- Pixel Atelier code moved in as our own modules (`pipeline/spritepipe.py`, `prompts_zh_sheet.py`,
  `providers/codex_rpc.py`, `samples/knight/`) with MIT headers.
- Provider `atelier` replaced by `procedural` (always available). Config `atelier_bin` removed; `language` and
  `prompt_language` added. Workspace `atelier_home` → `engine_home`. Server route `/atelier` → `/document`.
- Schema `procedural.engine` accepts `"atelier"` (old assets) or `"artstudio-pixel"`.
- Engine A brush anchoring (`size // 2`) and inclusive `doc_region` rects now match Atelier exactly.
- `detect_background` treats a mostly transparent border as transparent (fixes false QA warnings on round icons).

### Removed
- `upstream/` git checkouts, Rust Atelier binary dependency, `scripts/build-atelier.*`, `start-pixel-atelier.*`.

### Fixed
- Crashes on Windows GBK / cp936 / cp1252 and POSIX C locales: every read, write and subprocess pipe is UTF-8;
  POSIX argv surrogates recovered; UTF-8-mode relaunch as a safety net.

## [0.1.0] — 2026-11-25

First Stage A (offline) implementation of SPECIFICATION.md.

### Added
- Unified studio: Library, Character, Animation, Procedural, Import & Processing, Generation and Export workspaces.
- Providers: Atelier (Rust binary via MCP/CLI), ComfyUI (primary AI provider), External asset import, Mock, Codex (optional).
- ComfyUI client (`/object_info` validation, upload, `/prompt`, WebSocket progress, history, cancel) and bundled
  workflow templates (unverified).
- Offline mock ComfyUI server with failure scenarios (fail, timeout, disconnect, slow).
- Asset manifests with JSON schemas, preserved source frames, versions; group normalization; deterministic QA;
  job queue with budget, cancel, retry, resume.
- Exports: frames, sheet, atlas, GIF/APNG, JSON, Cocos Creator plist, Phaser/PixiJS, Godot helper, ZIP.
- Builders: potion, chest, chest_open, fireball, sword_slash. Proof-of-concept deliverables.
- Windows start script and deployment guide; `AGENTS.md`, `DEVELOPMENT_PROGRESS.md`.

### Known limitations
- Stage B (real ComfyUI inference) not run. AI generation is mock-tested only.

[Unreleased]: #unreleased
[0.4.0]: #040--2026-11-26
[0.3.0]: #030--2026-11-26
[0.2.0]: #020--2026-11-26
[0.1.0]: #010--2026-11-25
