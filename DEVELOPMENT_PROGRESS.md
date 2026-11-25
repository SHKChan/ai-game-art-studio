# Development progress

Labels: **implemented** (code exists) · **offline-tested** (automated/manual test executed here with real data) ·
**mock-tested** (exercised only against mock providers) · **production-verified** (Stage B on a real ComfyUI — none yet).

## Environment of this run (2026-11-25)

- Upstream repos supplied locally: Atelier `8ac6adf`, Pixel Atelier `15d199f`. No GitHub access.
- Build/test host: Linux sandbox with Python 3.13, Pillow 12.3, numpy 2.5, ffmpeg, Rust 1.97, Chromium/Playwright.
- User's computer (device VM): Python 3.10, Pillow 12.3, numpy 2.2, ffmpeg, **no Rust**.
- No GPU, no ComfyUI, no Codex CLI anywhere → AI generation is mock-tested only.

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | Upstream research (source, tests, showcase, examples) | done | docs/upstream-analysis.md; Atelier 378 Rust tests pass, 100/100 showcase replays byte-identical; Pixel Atelier 41 tests pass; workbench starts |
| 2 | Research documents | done | docs/upstream-analysis.md, feature-mapping.md, integration-architecture.md, upstream-limitations.md |
| 3 | Schemas + workspace persistence | offline-tested | asset/character/workflow JSON Schemas, atomic writes, versions, backup/restore (tests) |
| 4 | Engine A — Atelier provider (MCP + CLI), 5 builders | offline-tested | tests/test_integration.AtelierTests; recipe replay pixel-identical; spritepipe TECHNICAL_VERIFIED on chest_open |
| 5 | Engine C — import/processing (PNG, sheet grid/auto, sequence, GIF/APNG, MP4 via ffmpeg, bg removal, depixelate, normalize) | offline-tested | tests/test_core.ProcessingTests; POC Test C (GIF, sheet, MP4 round-trip exact visible size) |
| 6 | Animation system (templates, frame ops, events, phases, layers, versions) | offline-tested | test_core.WorkspaceTests; UI duplicate/delete test |
| 7 | Character master system (directions, candidates, lock, replace/unlock, mirroring, report) | offline-tested | test_core master tests; POC knight + chibi records |
| 8 | Dual processing modes (pixel/HD) | offline-tested | HD partial alpha preserved (tests + POC knight run HD) |
| 9 | QA deterministic + visual record + export checks | offline-tested | QATests; POC reports |
| 10 | Export (frames, sheets, atlas, GIF, APNG, JSON, Cocos plist, Phaser/Pixi JSON, Godot README/script, zip, composite preview) | offline-tested | ExportTests (plistlib parse, atlas rects, GIF frames); POC exports |
| 11 | ComfyUIProvider (HTTP, WS, upload, validation, queue, cancel, timeout, metadata) + workflow library/import | mock-tested | ComfyTests (ok/missing model/missing nodes/invalid values/execution error/timeout/WS disconnect/cancel/unreachable) |
| 12 | Mock ComfyUI service | implemented + used by tests | mock_comfyui/server.py |
| 13 | Job queue (progress, cancel, retry, resume, budget) | offline-tested | JobTests (budget stops batch at 2/3); cancel via mock |
| 14 | Web UI (7 workspaces, jobs dock, dark/light) | offline-tested | tests/ui_playwright.py passed (screens in tests/ui_screens, git-ignored) |
| 15 | Agent CLI + 14 skills | offline-tested (CLI) / written (skills) | ServerAndCliTests.test_cli |
| 16 | Proof-of-concept project | done (offline parts) | deliverables/poc (POC_REPORT.json, exports, contact sheets) |
| 17 | Windows scripts, config examples, deployment & Stage B guide, smoke test | implemented | smoke test rehearsed against mock with `--allow-mock` (8/8 PASS incl. cancel with slow scenario); start.ps1 NOT executed (no Windows here) |
| 18 | Cocos Creator TS example | implemented | `tsc --strict` compiles against an API stub; not run in Creator |

## Verified functionality (commands actually executed)

- `python scripts/run_tests.py` → 43 tests OK (21 core + 22 integration, incl. 3 Atelier, 11 mock-ComfyUI).
- `python scripts/run_tests.py --upstream` → studio tests + Pixel Atelier 41 tests OK.
- `cargo test --release --workspace` (upstream Atelier) → 378 passed.
- `python tools/showcase.py verify` (upstream Atelier) → all 100 replays match.
- `python tests/ui_playwright.py` → passed (project creation, Atelier run + inspector, knight import, playback,
  onion skin, QA, frame comparison, duplicate/delete, GIF import with before/after, character creation, generation
  tab, export with previews, reload persistence, theme toggle; no console errors).
- `python demo/build_poc.py` → all four POC tests produced real outputs (see deliverables/poc/POC_REPORT.json).
- Device VM (Python 3.10): see "Device verification" below.

## Follow-up (2026-11-25, session 2)

- **Encoding (GBK/cp936/cp1252) fix — offline-tested.** Reproduced: upstream Pixel Atelier reads/writes its Chinese
  project JSON with the locale default encoding and crashes (UnicodeDecodeError) on non-UTF-8 locales; on Chinese Windows
  it silently writes GBK files. Fix without editing upstream: `python -m artstudio` re-launches itself in Python UTF-8
  mode; `start.ps1`/`start.sh` set `PYTHONUTF8=1`; new `scripts/start-pixel-atelier.ps1|.sh` run the original workbench
  in UTF-8 mode; all studio subprocess/file text I/O has explicit UTF-8; Codex provider refuses to run outside UTF-8 mode.
  `tests/test_encoding.py` reproduces the upstream failure and verifies the fix (C locale simulation). 45/45 tests pass
  (build sandbox); 42 + 3 skipped on the device VM.
- **Engine A beyond the five builders — offline-tested.** New `python -m artstudio draw calls.jsonl --project P --name N
  --type icon|item|effect|tileset|...` runs any agent-authored Atelier call list into a normal asset (recipe kept,
  QA, export). Verified with a hand-written 32×32 sword icon.

## Technical decisions

- New UI on Pixel Atelier's stack instead of extending its workbench (rationale: docs/integration-architecture.md §1).
- Atelier via persistent MCP stdio session (CLI fallback); per-project Atelier stores.
- Builders compute instructions; Atelier paints them with palette-indexed `doc_paint_grid` on separate layers.
- One asset model with an animation block for all images; sources preserved; processed frames reproducible.
- QA motion heuristics only for character animations (props/effects legitimately change extent).
- ComfyUI templates: core nodes only, model files are required parameters, validated against `/object_info`.
- stdlib WebSocket client/server (no extra dependency).

## Blockers (precise)

1. **Real AI generation (Engine B / Test B chibi adventurer):** no ComfyUI, GPU or Codex on the development computer.
   Prepared: 4-direction character record, prompt packs (deliverables/poc/test_b_prompt_pack_chibi_adventurer.json),
   workflows, smoke test. Needs Stage B.
2. **Windows execution of start.ps1 / build-atelier.ps1:** not executable here (no Windows/PowerShell).
3. **Atelier on the device VM:** no Rust toolchain there; Atelier was built/tested in the Linux build sandbox (rustc 1.97,
   `--ignore-rust-version`, because the pinned 1.98 toolchain could not be downloaded).
4. **Engine runtimes:** Cocos Creator / Godot / Phaser not available; export files validated structurally only.
5. **Background-removal custom node and SVD video workflow:** unverified (mock has no such nodes → correctly reported missing).

## Remaining tasks

- Stage B: run `scripts/production_smoke_test.py` on the ComfyUI PC; then Test B reduced run (walk east, attack east),
  then full 4-direction set with a budget; mark verified workflows.
- Verify Cocos Creator import of `cocos/*.plist` + TS components in a real project; same for Godot script.
- Optional: plug a local vision model into `qa/visual.py` (`VisualAssessor`) for probabilistic checks.
- More builders (tiles, weapons/armour icons, ice/lightning/smoke variants) — skills describe the manual route today.
- Pillow 14 will remove `Image.getdata` (used in upstream Pixel Atelier and a few studio helpers) — switch to numpy.

## Device verification (user's computer, Linux VM, Python 3.10)

- `python3 scripts/run_tests.py --upstream` → studio 43 tests: 40 OK, 3 skipped (Atelier not runnable); Pixel Atelier 41 OK.
- The Linux Atelier build from the sandbox needs glibc 2.39 (VM has 2.35) → provider correctly reports
  `atelier --version failed` and the Procedural Studio shows it as unavailable (no silent fallback).
- CLI: `status`, `project create`, `import` of the POC MP4 (ffmpeg 4.4 extraction + keying + de-pixelation) and
  `export` → QA passed, 21 files.
