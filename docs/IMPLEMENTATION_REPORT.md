# Implementation report — Stage A (offline engineering acceptance)

> **Update (reorganisation):** the Rust Atelier binary and the `upstream/` checkouts were removed. Engine A is now the
> studio's own Python engine with Atelier's call format (Atelier showcase recipes replay pixel-identical; builders render
> identically to the earlier Atelier-based frames). Used Pixel Atelier code lives in `artstudio/` with MIT notices.
> Encoding is UTF-8 throughout and the tool is bilingual (en / zh-CN). Current numbers: 63 automated tests, Playwright
> UI pass in both languages. Sections below describe the original Stage A run; see DEVELOPMENT_PROGRESS.md for the
> current state.

Date: 2026-11-25 · App 0.1.0 · Upstream: Atelier `8ac6adf`, Pixel Atelier `15d199f`

**Stage B (real ComfyUI inference, model compatibility, GPU performance, generated-art quality) has NOT been run
and is not claimed.** See docs/deployment-windows.md §5.

## 1. Features by origin

### Reused from Atelier (unmodified binary, via MCP/CLI)
Layered documents, palettes, frames, tags, `doc_paint_grid` painting, sheet export with standard JSON metadata,
persistent document store, `doc.recipe` + `atelier replay`, document inspection data (doc.json, cels). Drawing guides
adapted into skills.

### Reused from Pixel Atelier (imported unmodified)
`spritepipe` build/check (run as an additional technical verifier), production STEPS and Chinese sheet prompt
(`adapters.pixel_atelier_prompt`), Codex app-server client (optional provider), knight example art + manifest
(genuine Engine B sample), workflow rules (single scale, whole-character poses, no per-frame fitting, technical ≠ visual
≠ engine verification), review checklist and action brief content (skills).

### New in this studio
Service layer, provider abstraction + registry, ComfyUIProvider + stdlib WebSocket client, workflow template library
(import/derive/validate/bind), mock ComfyUI service, MockGenerationProvider, ExternalAssetProvider, 5 procedural
builders, versioned schemas + validator, workspace persistence (versions, backup/restore, migration hook), character
master system (side/4/8 directions, candidates, locked masters, explicit replace/unlock, optional mirroring),
12 action templates, frame editing, layers with independent timing + composite preview, shared pixel/HD processing,
background removal, slicing, GIF/APNG/video import, group normalization with anchors, deterministic QA + separate
visual review record, exporters (atlas packer, TexturePacker JSON-hash, Cocos plist, GIF/APNG, JSON, Godot script),
async job queue with budgets, web UI (7 workspaces), JSON CLI, 14 skills, Windows/Linux launchers, Stage B smoke test,
Cocos Creator TypeScript example.

## 2. Tests executed (all results read)

| Suite | Where | Result |
|---|---|---|
| Studio unit + integration (`scripts/run_tests.py`) | build sandbox (Py 3.13) | **43/43 OK** |
| Same | user's device VM (Py 3.10, no runnable Atelier) | **40 OK, 3 skipped** (Atelier) |
| Pixel Atelier upstream tests | both | **41/41 OK** |
| Atelier `cargo test --workspace` | build sandbox | **378 passed** |
| Atelier showcase replay verification | build sandbox | **100/100 GIFs byte-identical** |
| Atelier `tools/tests` (showcase tooling) | build sandbox | 1 pass / 4 fail — fake-binary harness cannot execute in sandbox; unrelated to studio |
| Playwright UI smoke (`tests/ui_playwright.py`) | build sandbox | **passed**, no console errors |
| Production smoke test, rehearsal vs mock (`--allow-mock`) | build sandbox | 8/8 PASS (rehearsal only — **not Stage B**) |
| Cocos TS example `tsc --strict` against an API stub | build sandbox | compiles (API stub, not Creator) |
| CLI import (MP4) + export | device VM | OK (ffmpeg 4.4) |

Coverage of the spec's acceptance list (§17): 1 ✅ · 2 ✅ · 3 ✅ (server start, UI) · 4 ✅ · 5 ✅ (spritepipe, prompts,
knight pipeline) · 6 ✅ · 7 ✅ (UI playback) · 8 ✅ (UI reload + backup/restore test) · 9 ✅ frame editing; regeneration
🧪 mock · 10 ✅ (PNG/GIF/atlas/JSON/plist parsed) · 11 ✅ contact sheets inspected (below) · 12 ✅ (unavailable,
unreachable, missing models/nodes, failures, timeouts, disconnects) · 13 ✅ upstream suites still pass, upstream untouched.

## 3. Proof-of-concept results (`deliverables/poc`)

| Test | Outcome |
|---|---|
| A — Atelier | 64×64 potion, 64×64 chest, 8-frame chest opening, 8-frame fireball (loop), 8-frame sword slash. All deterministic QA *passed*; fireball recipe replay pixel-identical; chest opening `TECHNICAL_VERIFIED` by Pixel Atelier spritepipe. Editable Atelier documents + recipes in `test_a_procedural/atelier_sources/`. |
| B — character | Genuine AI-generated knight (Pixel Atelier sample) processed as character "knight": master locked from idle frame 0; idle/run/light/heavy imported with exact upstream canvases/pivots; hit/release/footstep events marked; run re-processed in **HD mode** (1.5× Lanczos, partial alpha preserved) without regeneration; spritepipe `TECHNICAL_VERIFIED` on run. Direction report correctly flags missing `left` (no mirroring of the asymmetric greatsword). **Chibi adventurer generation: BLOCKED** (no generator) — 4-direction character record + master/idle/walk/attack prompt packs prepared. |
| C — external | Atelier showcase `torch.gif` (10 frames); knight run sheet auto-sliced with support-foot anchoring; MP4 built from showcase `cat.gif` on a green screen → ffmpeg extraction (10/10 frames), colour key, de-pixelation; visible size round-trips exactly (124×124). Exported with previews. |
| D — hybrid | Knight heavy attack + Atelier gold sword-slash (2× integer scale) as an independent layer anchored to the `hit` event (−180 ms lead so the effect's impact lands on the hit); separate atlas entries and timing, composite preview GIF. |
| Mock pipeline | Separate project "TEST FIXTURE — mock ComfyUI pipeline": master candidate, walk east sheet, selective regeneration, export — every artefact flagged `is_test_fixture`, export `contains_test_fixtures: true`. |

## 4. Visual inspection notes (human-style review of contact sheets)

- Potion: readable silhouette, consistent top-left light, specular arc; inner glow blob slightly square. Acceptable.
- Chest / opening: 3/4 oblique chest with iron trim and lock; anticipation rattle, overshoot and settle read well;
  light beams are stylised vertical shafts (could be softer); lid underside reads as dark boards.
- Fireball: hot core, banded flame, flickering tongues, embers; loops; core slightly large.
- Sword slash: clear crescent with taper, impact flash, shard dissipation.
- Knight (upstream art): high quality; deterministic QA flags `anchor_discontinuity` on run (flight frames lift the
  lowest pixel — expected; mark them airborne if desired) and jitter/scale warnings on the light combo (large lunge and
  raised blade — expected). These are warnings, not defects.
- Hybrid: the gold crescent follows the blade sweep and lands on the impact; it overlaps the knight's own baked cyan
  slash (the upstream art already contains VFX) — a design choice for the demo, not ideal for production.
- Video round-trip: green cape pixels inside the outline survive keying (connected keying); no fringe.

## 5. Blocked / experimental

| Item | Status |
|---|---|
| Real AI generation via ComfyUI | 🧪 mock-tested; ⛔ Stage B pending |
| Codex image provider | optional; ⛔ codex CLI absent |
| Bundled workflows | all `unverified`; `svd-image-to-video` and `rembg-inspyrenet` need nodes absent from the mock |
| Visual-model-assisted QA | interface + manual record only; no model bundled |
| Cocos/Godot/Phaser integration | files produced and structurally validated; not run in engines |
| Windows launch scripts | written; not executed (no Windows host) |
| Atelier on the user's VM | Linux build needs glibc 2.39; VM has 2.35 → Atelier correctly reported unavailable there |

## 6. Known limitations / future work

See DEVELOPMENT_PROGRESS.md "Remaining tasks" and docs/upstream-limitations.md.
