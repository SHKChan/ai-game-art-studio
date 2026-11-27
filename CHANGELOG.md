# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/). The current version is in [VERSION](VERSION).

## [Unreleased]

## [0.7.0] — 2026-11-27

Pixel Forge gets a character kit: a 4-direction base character with five fantasy class costumes and a bow attack.

### Added
- **Character kit** (`artstudio/charkit/`, Pixel Forge builder `character_kit`, gallery group *Characters*): the Craftpix
  4-direction base character (male / female, 64×64, 13 actions with per-frame durations read from the .aseprite files)
  plus five class presets drawn on every frame — `knight`, `mage`, `ranger`, `priest`, `berserker` (helmets / hats /
  hoods / circlet, plate / leather / fur armour, robes with trim, tabard, belts, capes; sword recolour, axe, orb and
  cross staffs).
- **`Bow_Attack`**: synthesised bow shot on the sword-attack body poses (ready → nock → draw → full draw → release →
  follow-through → recover) for all four facings; right-handed archer (bow in the left hand), bow faces the viewer in
  the front view, no arms visible from the back.
- `scripts/setup_character_base.py` (unzip the packs into git-ignored `assets_local/craftpix-base/`, or set
  `ARTSTUDIO_CHARKIT_DIR`) and `scripts/make_character_pack.py` (sprite sheets, GIF previews, `meta.json`).
- Builder `LOOP` may be a function of the params (character idle / walk / run loop, attacks don't); the Forge loop
  checkbox follows the variant.
- `tests/test_character_kit.py` (7 tests; the 5 render tests skip without the local pack).

### Fixed
- Near-side weapon layering: facing right, a right-handed character's sword is drawn over the face and headgear;
  facing left it stays behind the body.
- Death frames: no cape or long hair on the lying body; a staff falls flat instead of standing upright.

### Notes
- The Craftpix art is **not** committed (`assets_local/` is git-ignored): its free licence forbids redistribution.
  Exports made from it are for use in your own games only.

## [0.6.0] — 2026-11-27

Pixel Forge gets a JRPG kit for tactics / idle-dungeon games: top-down grid skills, item / skill / status icons and a
themed UI kit.

### Added
- **Top-down grid skills** (`procedural/_ground.py` convention: width `tiles*32`, the bottom square is the ground cells,
  headroom above; pivot = cell centre): `lava_burn` (熔岩灼地 — cracks glow, magma floods the cells, burning loop, cools;
  tags cast/burn/fade, `phase` param), `meteor`, `fire_pillar`, `earth_spike`, `whirlpool`, `gale`, `ice_field`,
  `holy_judgment`, `dark_vortex`, `life_drain`. Each has colour variants and a `tiles` size.
- **Icon renderer** (`procedural/_icon.py`): icons are designed on a 32-unit grid and drawn at **32 / 48 / 64 px**
  (`size`, default 48); every part is lit per pixel like the original potion builder — height field from the distance to
  the part edge → normal → top-left light → 5-tone hue-shifted ramp with ordered dithering, plus styles (metal, blade,
  gem with internal glow, glass, wood grain, soft cloth) and specular highlights; selective outline; rarity slot.
- **Icon kits** built on it: `weapon_icon` (8 kinds × 5 tiers), `armor_icon` (8 × 5) — each tier (bronze → iron →
  mithril → gold → dark) changes the **design** (fullers, guards, wings, horns, serration, trident, kite shield, crowned
  helm …), not just the colour; `consumable_icon` (8 kinds × 3 grades: different bottles, feathers, seals, bombs);
  `material_icon` (8 × 6 colours, each colour its own design: gem cuts, herbs, mushrooms, key bows …);
  `skill_icon` (18 skills, lit bevelled element frames); `status_icon` (20 × 16-px badges).
- **UI kit** (`procedural/_ui.py`, themes classic_blue / wood_gold / stone_iron / parchment, 9-slice friendly):
  `ui_panel` (window, dialog with bobbing next-arrow, tooltip, title banner, tab active/inactive), `ui_button`
  (rect / square / round; frames normal / hover / pressed / disabled), `ui_bar` (HP / MP / EXP / stamina / ATB, `fill`,
  `part` = bar / frame / fill), `ui_frame` (portrait, item slot, skill slot; normal / selected / locked),
  `ui_icon` (20 menu icons incl. cursor hand, colour or white `mono`). Gallery group "UI".
- `scripts/make_jrpg_pack.py` renders every variant to PNGs, sprite strips + `meta.json`, GIF previews and contact sheets;
  the rendered pack is in `deliverables/jrpg_pack/`.
- Builder attributes `GROUP` (gallery groups "Skill icons", "UI"), `FULL_BLEED` (QA accepts edge-to-edge art for
  tile-aligned effects, framed icons and UI) and `pivot(**params)` (stored as the asset pivot). Such builders are placed
  1:1 on their canvas (`source_pivot`), so saved assets keep exactly the drawn size; recipe replays do the same for art
  that touches the canvas edge.

### Changed
- Ground skills: textured, lit rock spikes (earth_spike / ice_field crystals), gradient meteor flash, thicker life-drain
  ribbons, faster lava/ice rendering (cached outline noise).

### Fixed
- `README.md` was 18 MB (one Motion Studio block repeated 10,840 times, title lost) — rebuilt.
- Chinese UI strings for all new builders and options; tests `tests/test_jrpg_assets.py`.

## [0.5.0] — 2026-11-26

Motion Studio becomes a production line for action frames, and gets a sprite editor.

### Added
- **Start from a description** (second start option): describe the character, generate **4 reference candidates**
  with Codex or local ComfyUI (text-to-image), pick one — it is locked as the reference. "Generate 4 more" with a
  change note. API `characters/from-description`, `…/reference-candidates`, `…/pick-reference`; job `reference_candidates`;
  CLI `animate describe | candidates | pick`.
- **Core set** walk (8 frames) · attack (8) · hit (4) with written motion briefs (en/zh); UI button and `animate core`.
- **One sheet per action in a fixed grid** (`processing/sheet.grid_for`: 8 → 4×2, 4 → 2×2, 5–6 → 3×2 …), following Pixel
  Atelier's proven 4×2 knight sheet. Prompts (template and Codex) ask for the grid; ComfyUI gets the reference repeated in
  the same grid.
- **Local sheet processing** (`artstudio/processing/sheet.py`): background removal → components assigned to grid cells →
  pseudo-pixel grid detection → **one sampling step per sheet** so the reference pose reaches the character height
  (default 64 px) → cleanup (binary alpha, background-coloured halo, stray specks, 1-px holes) → snap to the palette of the
  reference image → QA (empty cell, merged sprites across cells, size drift, border contact). Frames are placed on a fixed
  per-character canvas with the feet on one ground line (`ground`, or `ground_torso` for loops).
- **Automatic regeneration**: a sheet that fails QA is regenerated up to `settings.max_retries` times (default 2) with a
  note describing what failed; attempts are recorded on the asset. Batch budget defaults to actions × (1 + retries).
- Plan **settings** (character height, palette size, retries) in the Generate step; **Re-cut** an action at another
  height from its preserved sheet (`POST …/recut`, `Studio.recut_action`).
- **Sprite editor** (`web/sprite.js`), opened from the review step, the Library (✎ on a card) and the Animation editor:
  pixel inspector (click a pixel → coordinates, colour, usage count; recolour, delete, use colour, replace that colour in
  this frame / all frames, remove a colour; arrow keys walk pixels, Enter paints, Delete removes), pencil, eraser, picker,
  fill (Alt: global), line, rectangle (Shift: filled), selection with move / Alt-copy / copy-paste between frames / flip /
  clear, mirror frame, brush size 1–3, palette from the animation, two colours (X swaps), zoom / fit / pan, pixel grid,
  ground line + pivot, onion skin, playback, per-frame duration, duplicate / move / delete frames, undo / redo, Ctrl+S.
- **Patch layer**: hand edits are stored per frame (`patches/<fid>.png` + `_erase.png`, anchored to the pivot) over the
  processed frame (`frames_base/`). Reprocessing or re-cutting keeps them; a scale change flags them `stale`.
  API `POST …/pixels`, `…/pixels/clear`. Versions snapshot patches too.
- Tests: `tests/test_sprite_edit.py` (5) + new cases in `tests/test_actions.py` (regeneration, retry cap, core presets);
  Playwright covers the sprite editor and the description start.

### Changed
- `strip_layout` (auto/even-grid guessing) replaced by grid-based cutting; `action.layout` is now `grid CxR`.
- The mock provider builds a labelled test sheet from the knight sample in the requested grid.
- Review step: "Fine-tune…" → "Timing & events…"; new "✎ Edit pixels".

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
