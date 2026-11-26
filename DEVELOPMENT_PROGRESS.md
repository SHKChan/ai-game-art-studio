# Development progress

Labels: **implemented** · **offline-tested** (executed here with real data) · **mock-tested** (only against mock providers) ·
**production-verified** (Stage B on a real ComfyUI — none yet).

## Current state (2026-11-26, v0.3.0)

| Area | State | Evidence |
|---|---|---|
| Engine A — own Python pixel engine (`artstudio/engine`), Atelier-compatible call format | offline-tested | tests/test_engine.py: tool semantics, persistence, determinism; **Atelier showcase recipes potion/slash replay pixel-identical to Atelier's GIFs**; all builders identical to the earlier Atelier-rendered POC frames |
| Builders: potion, chest, chest_open, fireball, sword_slash, **ice_spear** (3 elements), **hero_shrine** (96×96, animated) + `artstudio draw` call lists | offline-tested | EngineATests; contact sheets inspected |
| Engine A authoring guide + skill | done | docs/engine-a-guide.md, skills/procedural-builder-authoring |
| Pixel Atelier code moved in: spritepipe, Chinese sheet prompts, Codex client, knight sample | offline-tested | tests/test_spritepipe.py (14 upstream tests ported, pass); POC spritepipe TECHNICAL_VERIFIED |
| Encoding (GBK/cp936/cp1252/C locale) | offline-tested | tests/test_encoding.py: no locale-default I/O in code; full Chinese CLI flow under C locale with UTF-8 mode OFF and no relaunch; POSIX argv recovery |
| Bilingual en / zh-CN | offline-tested | UI dictionary + observer; server/CLI localized errors; zh prompts; README/deployment in Chinese; Playwright zh pass over all 7 workspaces |
| Engine C import/processing, character masters, animation editing, QA, export, job queue, server, CLI | offline-tested | 78 tests total |
| Engine B guided flow: reference → action plan → prompts → one strip per action → slice/align → review/redo frame → export | offline-tested (pipeline) / mock-tested (AI) | tests/test_actions.py (13): plan model, template prompts en/zh, Codex prompt writing + failure, Codex strip generation + failure, budget, grid fallback, strip reference, ComfyUI strip via mock server, HTTP API flow; Playwright drives all 5 steps in English + Chinese review |
| Codex CLI integration (`codex exec` prompt writing, `codex app-server` image generation, Windows `codex.cmd`) | mock-tested | only against `tests/fake_codex.py`; **real Codex not run** (no account/network here) |
| Guided UI (Home, Animate character, More tools) | offline-tested | tests/ui_playwright.py |
| ComfyUI provider + workflow library + mock service | mock-tested | ComfyTests (ok, missing model/nodes, invalid values, failure, timeout, WS disconnect, cancel, unreachable) |
| Proof of concept | done (offline parts) | deliverables/poc/POC_REPORT.json |
| Stage B | **not run** | needs the ComfyUI PC |

## Commands executed (results read)

- `python scripts/run_tests.py` → 63 tests OK (build sandbox, Python 3.13, before hero_shrine). Device VM results below.
- `python tests/ui_playwright.py` → passed in English and Chinese, no console errors.
- `python demo/build_poc.py` → tests A–D + mock pipeline regenerated with Engine A.

## Decisions

- Owner approved rewriting: dropped the Rust Atelier dependency and the `upstream/` checkouts; kept compatibility by
  re-implementing Atelier's call format and testing against its showcase recipes.
- Derived code keeps MIT notices (file headers + THIRD_PARTY_NOTICES.md).
- Knight sample art kept for demos/tests only (its authors released it for demonstration/reproduction).
- Translation scope: UI, CLI/API messages, generation prompts, README + deployment guide. Agent docs/skills English.
- Prompt language default English (model reliability); per-project switch to Chinese.

## History

- c25b33e — Stage A implementation integrating Atelier (Rust binary via MCP/CLI) and Pixel Atelier (as libraries).
- Session 2 — encoding issue reproduced (Pixel Atelier locale-default I/O); `artstudio draw` added.
- 0a8b4d9 — reorganisation into a self-contained codebase, Engine A rewrite, i18n, ice_spear builder, guide.
- 724107c — Engine A parity fixes (brush anchoring, inclusive region rects); 0 differing pixels vs Atelier on 10 samples.
- 0f1773c — hero_shrine builder.
- v0.2.0 — README (features, usage, upstreams), CHANGELOG, VERSION, AGENTS.md facts/gotchas, version consistency test.
- v0.3.0 — Engine B = character animation (action plans, Codex/ComfyUI strips), guided UI, `artstudio animate` CLI.

## Blockers

0. Real Codex CLI run (prompt writing + image generation) needs the owner's logged-in Codex on Windows. First check: Animate
   character with one preset action; confirm the strip slices into the requested frame count.

1. Real AI generation (Test B chibi adventurer): no ComfyUI/GPU/Codex here. Prompt packs (en + zh) prepared.
2. Windows scripts not executed here; Cocos/Godot/Phaser runtimes unavailable.
3. Bundled ComfyUI workflows unverified until Stage B.

## Remaining tasks

- Stage B smoke test + reduced Test B on the ComfyUI PC; mark verified workflows.
- Verify Cocos Creator import and TS components in a real project; Godot script.
- More builders (weapons/armour icons, tiles, ice/lightning/heal/smoke effects) via docs/engine-a-guide.md.
- Optional local vision model for `qa/visual.py`.

## Device verification

- User's computer (Linux VM, Python 3.10, Pillow 12.3, numpy 2.2): `python3 scripts/run_tests.py` → **63 tests OK, 0 skipped**
  (Engine A now runs everywhere — previously the Rust binary could not run there).
