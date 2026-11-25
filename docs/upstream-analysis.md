# Upstream analysis

Both repositories were supplied locally under `upstream/` (the development computer has no GitHub
access). Everything below was verified by reading the source and running it, not taken from READMEs.

| | Atelier | Pixel Atelier |
|---|---|---|
| Path | `upstream/atelier` | `upstream/pixel-atelier` |
| Commit | `8ac6adfc784d1e3127060e4f5b58cde1e6c9bf85` (2026-11-19) | `15d199f68e6657af0873b3c950525c4bf28eed6f` (2026-11-22) |
| Licence | MIT © 2026 Marmik Shah | MIT © 2026 Pixel Character Pipeline contributors |
| Language | Rust 2024 (workspace of 4 crates), pinned toolchain 1.98 | Python ≥3.9 + Pillow; vanilla JS UI |
| Size | ~15 MB incl. showcase GIFs/recipes | ~1.8 MB incl. knight example |

## Atelier

**What it is.** An offline, headless, layered pixel-art editor driven by tool calls. Same 27 tools over
CLI (`atelier call TOOL '<json>'`, `--stdin`, `--file`, `--home DIR`) and MCP over stdio (`atelier` with no
arguments; also an HTTP server mode). Documents persist under `ATELIER_HOME`/`--home` (`documents/<uuid>/doc.json`,
`cels/L{layer}_F{frame}.png`, `doc.recipe`), with journaled atomic edits and checkpoints.

**Crates.** `atelier-core` (document model, draw/fx/palette/region/timeline/export, raster noise/colour/transform,
font export), `atelier-studio` (storage, transactions, journals, checkpoints, analysis), `atelier-mcp`
(tool registry/server), `atelier` (CLI: call, replay, library, init, connect, skills, service, uninstall).

**Tools (verified via `atelier tools`).** doc_new, doc_layer, doc_frame, doc_palette, doc_draw (pencil, line, rect,
ellipse, polyline, polygon, stroke, curve, stamp, fill, gradient, scatter, noise, text, fill_cel, clear_cel),
doc_paint_grid (char rows + legend, palette indices), doc_fx (blur, outline, drop_shadow, bevel, shade, form,
pixel_perfect, flip, shift, rotate, symmetry, adjust, dither, scale, quantize, replace_color, gradient_map),
doc_region, doc_rescale, doc_dither_ramp, doc_export (sheet with `atelier`/`standard` JSON meta, GIF/APNG, TTF font),
doc_look, doc_silhouette, doc_components, doc_critique, doc_anim_audit, doc_frame_diff, doc_contact_sheet,
doc_seam_report, doc_dump_region, doc_ref, doc_checkpoint, doc_add_tag, doc_font, doc_info, list_docs, delete_doc.

**Recipes.** Every document keeps `doc.recipe` — one JSON line per call — and `atelier replay` rebuilds it.
Recipes are tied to tool behaviour of a commit (no version field).

**Skills.** `crates/atelier/skills/{sprite,scene,review}.md`: layer-per-moving-part, silhouette first,
"fix the region, never the frame", look/measure/report review lenses, GIF 1-bit alpha caveats.

**Showcase.** 10 model runs × 10 briefs (alien, ball, beam, car, cat, explosion, person, potion, slash, torch),
each with recipe + GIF. Quality inspected visually: clean, readable 32×32 sprites/effects.

**Executed.**

| Check | Result |
|---|---|
| `cargo build --release --locked -p atelier` | Pinned 1.98 toolchain could not be downloaded (static.rust-lang.org blocked). Built with installed **rustc 1.97.0** using `--ignore-rust-version`: success, binary `atelier 0.2.0`. |
| `cargo test --release --workspace` | **378 passed, 0 failed** (15 test binaries incl. stdio/http smoke, storage recovery, archives). |
| `tools/showcase.py verify` (replays every showcase recipe, compares GIF bytes) | **all 100 replays match** their committed GIFs. |
| `tools/tests` (Python tests for the showcase tooling) | 1 passed, 4 failed/errored in this sandbox: they build a fake `atelier` wrapper script that fails to execute here (Python 3.13 / sandbox). Not used by the studio; recorded as an environment limitation. |
| Manual CLI + MCP session | doc_new/draw/frame/export via CLI and via stdio MCP (`initialize` → `tools/call`) both work; `structuredContent` returned. |

## Pixel Atelier

**What it is.** A local character-animation workbench for whole-character, frame-by-frame pixel sprites
(side view), built around one blonde greatsword knight case study, plus `spritepipe`, a portable
build-and-check CLI.

**Components.**
- `spritepipe/core.py` (340 lines): profile.json schema 0.1 (`route: whole_character`, frozen palette,
  per-action grid, fixed `source_scale`, integer whole-frame `offsets`, pivot, durations in 10 ms units,
  events.strikes), `build_action` (grid crop → refuse poses touching cell edges → one nearest scale →
  palette map with alpha threshold → integer offset → atlas + indexed transparent GIF + animation.json with
  source SHA-256), `check_action` (re-derives every guarantee: palette, binary alpha, margins, atlas pixels,
  GIF pixel/timing timeline) → `TECHNICAL_VERIFIED | FAIL`, always with `visual/engine/user: pending`.
- `bridge/server.py` (stdlib HTTP, loopback, cookie token, Host/Origin checks), `bridge/rpc.py` (native
  `codex app-server` JSON-RPC client for built-in image generation — no API keys), `bridge/production.py`
  (8 ordered actions idle→run→dash→light→heavy→jump→hurt→knockdown with Chinese motion briefs, durations, a
  4×2 sheet prompt template, `fit_sheet` single-scale fitting, managed/guided modes), `bridge/projects.py`
  (character project format `pixel-atelier-character/1`, revisions/history, palette freeze, ZIP export),
  `bridge/editor.py` (GIF frame sampling, export_animation, events strikes/releases).
- UI: `bridge/workbench.html` + JS modules (beginner, character, atelier editor, delivery, production).
- Docs/templates: workflow.md (master locking, semantic alignment, failure → rework table), action-brief,
  review-checklist, engine-integration (pivot/root drawing, events, hit windows).
- Example: `examples/knight` — 8 actions, 80 poses, atlases + manifest (frame rects, durations, pivots).

**Executed.**

| Check | Result |
|---|---|
| `python -m unittest discover -s tests` | **41 passed** (Pillow 12.3 on Python 3.13; requirement pin `<12` is stricter than needed). |
| `python -m spritepipe demo` | `TECHNICAL_VERIFIED` on its synthetic calibration fixture. |
| `python bridge/server.py` | Starts; `/health` OK; workbench HTML served. Generation needs a logged-in Codex CLI (not available). |
| Knight example inspection | Genuine high-quality whole-character pixel sprites (see docs/feature-mapping.md); 160–224 px canvases with pivots. |

## Reusable components (used by this studio)

- Atelier binary, unmodified, as Engine A (CLI + MCP). Recipes, layers, checkpoints, exports, analysis tools.
- Atelier skills → adapted into `skills/procedural-pixel-art`, `game-icon-generation`, `tileset-generation`,
  `skill-effect-animation`, `animation-consistency-inspection`.
- Pixel Atelier `spritepipe` → imported unmodified by `artstudio/adapters.py` and run as an extra technical
  verifier (`qa --spritepipe`).
- Pixel Atelier `bridge/production.py` STEPS + `generation_prompt` → exposed via adapters; its structure
  (single action per sheet, fixed cell order, transparent, margins, whole character) shapes `artstudio/prompts.py`.
- Pixel Atelier `bridge/rpc.py` CodexClient → optional `CodexImageProvider`.
- Pixel Atelier knight example → genuine Engine B input for offline tests (labelled with provenance).
- Pixel Atelier rules (single scale per sheet, never per-frame bbox fitting, never auto-align lowest foot,
  canvas expansion, technical ≠ visual ≠ engine verification) → encoded in `processing/frames.py`, `qa`.
