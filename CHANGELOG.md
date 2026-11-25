# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/). The current version is in [VERSION](VERSION).

## [Unreleased]

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
[0.2.0]: #020--2026-11-26
[0.1.0]: #010--2026-11-25
