# Development progress

Labels: **implemented** · **offline-tested** (executed here with real data) · **mock-tested** (only against mock providers) ·
**production-verified** (Stage B on a real ComfyUI — none yet).

## Current state (2026-11-27, v0.9.0)

Tool names: **Pixel Forge** (procedural pixel engine, was Engine A), **Motion Studio** (character animation, was Engine B),
**Asset Import** (import, was Engine C).


| Area | State | Evidence |
|---|---|---|
| Pixel Forge — own Python pixel engine (`artstudio/engine`), Atelier-compatible call format | offline-tested | tests/test_engine.py: tool semantics, persistence, determinism; **Atelier showcase recipes potion/slash replay pixel-identical to Atelier's GIFs**; all builders identical to the earlier Atelier-rendered POC frames |
| Builders: potion, chest, chest_open, fireball, sword_slash, **ice_spear** (3 elements), **hero_shrine** (96×96, animated) + `artstudio draw` call lists | offline-tested | PixelForgeTests; contact sheets inspected |
| JRPG kit (v0.6): 10 top-down grid skills (lava_burn …), lit icon renderer (32/48/64) with tiered weapon/armor/consumable/material/skill/status icons, UI kit (panels, buttons, bars, frames, menu icons × 4 themes), `scripts/make_jrpg_pack.py` | offline-tested | tests/test_jrpg_assets.py; every variant rendered and contact sheets inspected |
| Character kit (v0.7): Craftpix 4-direction base (male/female, 13 actions) + knight / mage / ranger / priest / berserker costumes, synthesised `Bow_Attack`, `character_kit` builder, setup + export scripts | offline-tested | tests/test_character_kit.py (needs the local pack; all 6 presets × 14 actions × 4 facings pass QA); lineup, death and bow sheets inspected |
| Character kit v0.8: `Cast_Spell` (mage / priest / necromancer attack), bow string follows the draw hand, distinct caster costumes, `necromancer` + see-through `skeleton` (spine pole, thin bones, skull, wooden shield, stiff timing, short chop), `Summon_Rise` | offline-tested | tests/test_character_kit.py (10 tests incl. string-follows-hand, casters cast, skeleton body / shield / stiffness / rise QA); 112 tests pass on the PC; all presets × bow / cast / rise and necromancer / skeleton × 16 actions stay off the canvas edge; sheets inspected |
| Asset packs v0.9: `tiny-rpg` (Soldier, Orc, Demon A, Blood Monster A → characters + 26 actions + arrow), `craftpix-dungeon` (8 tilesets, 15 animated props, `Dungeon1.tmx` rendered with animated tiles), `pvfx-foundry` (253 CC0 effects, lit/strict, variants); setup script, `import_pack` job, pack browser UI, `packs` CLI, API | offline-tested | tests/test_packs.py (synthetic fixture packs + real-pack test); on the PC all three real packs installed in `assets_local/packs/` and imported into workspace project `asset-library` (4 characters, 303 assets); Tiny RPG strips, props, map and effects inspected on contact sheets; Playwright screenshots of the pack browser, Library tag chips and Forge tag search (en + zh) |
| Search tags v0.9: English-only normalisation on save, `BUILDER_TAGS` for every builder + character-kit preset tags (monster / undead), Library tag chips, Forge tag search, `retag` command | offline-tested | tests/test_packs.py TagTests (every builder tagged, non-English dropped, retag) |
| Pixel Forge authoring guide + skill | done | docs/pixel-forge-guide.md, skills/procedural-builder-authoring |
| Pixel Atelier code moved in: spritepipe, Chinese sheet prompts, Codex client, knight sample | offline-tested | tests/test_spritepipe.py (14 upstream tests ported, pass); POC spritepipe TECHNICAL_VERIFIED |
| Encoding (GBK/cp936/cp1252/C locale) | offline-tested | tests/test_encoding.py: no locale-default I/O in code; full Chinese CLI flow under C locale with UTF-8 mode OFF and no relaunch; POSIX argv recovery |
| Bilingual en / zh-CN | offline-tested | UI dictionary + observer; server/CLI localized errors; zh prompts; README/deployment in Chinese; Playwright zh pass over all 7 workspaces |
| Asset Import import/processing, character masters, animation editing, QA, export, job queue, server, CLI | offline-tested | 98 tests total |
| Motion Studio guided flow: reference → action plan → prompts → one strip per action → slice/align → review/redo frame → export | offline-tested (pipeline) / mock-tested (AI) | tests/test_actions.py (13): plan model, template prompts en/zh, Codex prompt writing + failure, Codex strip generation + failure, budget, grid fallback, strip reference, ComfyUI strip via mock server, HTTP API flow; Playwright drives all 5 steps in English + Chinese review |
| Motion Studio v0.5: description → 4 reference candidates → pick; core set walk/attack/hit; one grid sheet per action; local cutting (cells, pseudo-pixel step, height 64, ground line, reference palette, halo/speck cleanup); QA + automatic regeneration (≤2); re-cut | offline-tested (processing, mock sheets) / mock-tested (AI) | tests/test_sprite_edit.py, tests/test_actions.py (bad sheet → regenerated, retry cap); mock knight sheets cut to 64 px on one ground line (inspected) |
| Sprite editor (pixel inspector, tools, selection, frames, onion skin, undo/redo) + patch layer that survives reprocess / re-cut | offline-tested | tests/test_sprite_edit.py; Playwright: inspect → recolour → delete → undo/redo → pencil → save → "hand-edited" badge; zh screenshot checked |
| Codex CLI integration (`codex exec` prompt writing, `codex app-server` image generation, Windows `codex.cmd`) | mock-tested | only against `tests/fake_codex.py`; **real Codex not run** (no account/network here) |
| Guided UI (Home, Motion Studio, More tools), theme System/Dark/Light | offline-tested | tests/ui_playwright.py |
| Pixel Forge editor (live preview; variant, speed, palette/HSV, outline, glow, flip, scale; save/export; replayable edits) | offline-tested | tests/test_forge.py (6) + Playwright |
| Skill effects: heal, buff_aura, lightning_strike, shield_barrier, frost_nova, poison_cloud (+ colour variants, thickness) | offline-tested | PixelForgeTests (QA passed), test_forge variants; contact sheets inspected |
| ComfyUI provider + workflow library + mock service | mock-tested | ComfyTests (ok, missing model/nodes, invalid values, failure, timeout, WS disconnect, cancel, unreachable) |
| Proof of concept | done (offline parts) | deliverables/poc/POC_REPORT.json |
| Stage B | **not run** | needs the ComfyUI PC |

## Commands executed (results read)

- `python scripts/run_tests.py` → 63 tests OK (build sandbox, Python 3.13, before hero_shrine). Device VM results below.
- `python tests/ui_playwright.py` → passed in English and Chinese, no console errors.
- v0.5.0 (cloud sandbox, Python 3.13): `pytest tests` → 91 passed; `tests/ui_playwright.py` → passed (incl. sprite editor and description start).
- `python demo/build_poc.py` → tests A–D + mock pipeline regenerated with Pixel Forge.

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
- 0a8b4d9 — reorganisation into a self-contained codebase, Pixel Forge rewrite, i18n, ice_spear builder, guide.
- 724107c — Pixel Forge parity fixes (brush anchoring, inclusive region rects); 0 differing pixels vs Atelier on 10 samples.
- 0f1773c — hero_shrine builder.
- v0.2.0 — README (features, usage, upstreams), CHANGELOG, VERSION, AGENTS.md facts/gotchas, version consistency test.
- v0.4.0 — tool names, Pixel Forge editor + six skill effects, theme selector.
- v0.5.0 — reference from description, core action set, grid sheets + local processing + automatic regeneration, sprite editor with patch layer.
- v0.9.0 — asset packs (Tiny RPG, Craftpix dungeon, PVFX Foundry) + English search tags.
- v0.3.0 — Motion Studio = character animation (action plans, Codex/ComfyUI strips), guided UI, `artstudio animate` CLI.

## Blockers

0. Real Codex CLI run (prompt writing + image generation) needs the owner's logged-in Codex on Windows. First check: Motion
   Studio → Core set → Run pipeline; confirm each sheet comes back in the requested grid and passes the sheet QA.

1. Real AI generation (Test B chibi adventurer): no ComfyUI/GPU/Codex here. Prompt packs (en + zh) prepared.
2. Windows scripts not executed here; Cocos/Godot/Phaser runtimes unavailable.
3. Bundled ComfyUI workflows unverified until Stage B.

## Remaining tasks

- Stage B smoke test + reduced Test B on the ComfyUI PC; mark verified workflows.
- Verify Cocos Creator import and TS components in a real project; Godot script.
- More builders (terrain tiles, characters' hit sparks, more weapon kinds) via docs/pixel-forge-guide.md.
- Optional local vision model for `qa/visual.py`.

## Device verification

- v0.9.0 on the user's computer (Linux VM): `python3 scripts/run_tests.py` → **128 tests OK, 0 skipped** (Craftpix base
  and the three asset packs installed locally). Note: importing through the VM's mounted folder takes ~4 s per asset;
  run imports from the studio on Windows for speed.

- User's computer (Linux VM, Python 3.10, Pillow 12.3, numpy 2.2): `python3 scripts/run_tests.py` → **63 tests OK, 0 skipped**
  (Pixel Forge now runs everywhere — previously the Rust binary could not run there).
