# AI Game Art Studio

[简体中文](README.zh-CN.md) · Version **0.8.1** ([CHANGELOG](CHANGELOG.md)) · Licence MIT

A **local-first studio for 2D game art**: pixel art and HD illustration, from a single icon to animated character
sprites, exported straight into game engines. It is a self-contained Python app (Pillow + numpy) with a web UI in
English and Chinese. It needs no cloud service, database or paid API.

![chest opening](deliverables/poc/contact_sheets/A_chest_open.png)

## What it can do

The studio has three tools. They all produce the **same asset format**, so editing, QA and export work on everything.

| Tool | Use it for | How |
|---|---|---|
| **🔥 Pixel Forge** | Skill effects, items, icons, props, scenery, 4-direction class characters | Built-in pixel builders with a **live editor**: variant, size, speed, colours, outline, glow, flip, scale. Layered and replayable. Offline, no AI. |
| **🎬 Motion Studio** | A character's action frames: idle, walk, attack, custom moves | Reference image (uploaded or generated from a description) → actions → one sheet per action, drawn by the **Codex CLI** or your local **ComfyUI**; cut, aligned and cleaned locally; pixel-level sprite editor. |
| **📥 Asset Import** | Art you already have | PNG / sequences / sprite sheets / GIF / APNG / MP4 / WebM: remove the background, slice, align. |

Shared features:

- **Characters:** identity fields, side / 4 / 8 directions, candidate → approved **locked** master, history.
- **Animation editing:** playback, FPS, per-frame duration, onion skin, pivots, reorder / duplicate / replace frames,
  selective regeneration, events, effect layers, version snapshots.
- **Processing:** background removal, slicing, de-pixelation, group alignment (one scale per animation, ground anchors,
  airborne frames kept, canvas expanded instead of cropping weapons).
- **QA:** deterministic checks (size, clipping, background, jitter) kept separate from visual review.
- **Export:** PNG frames, sprite sheet, packed atlas, GIF / APNG, JSON, **Cocos Creator** plist, Phaser / PixiJS JSON,
  Godot helper, ZIP.
- **Look:** English / 中文, and System / Dark / Light theme (top bar).

### Built-in Pixel Forge builders

| Builder | Output | Options (besides the editor's speed / colours / outline / glow / flip / scale) |
|---|---|---|
| `heal` | Healing: ground glow, light column, rising plus motes (loop) | `color` green/blue/gold, `frames` |
| `buff_aura` | Power-up ring at the feet, rising streaks and chevrons (loop) | `color` gold/red/purple, `frames` |
| `lightning_strike` | Bolt from the sky, impact flash, shock ring, sparks | `color` blue/purple/yellow, `thickness` 1–3 |
| `shield_barrier` | Hexagon bubble forms, shimmers, dissolves (see-through) | `color` azure/gold/green |
| `frost_nova` | Centre flash, outward ring of ice shards, snow | `color` ice/arcane/toxic |
| `poison_cloud` | Churning toxic cloud with popping bubbles and drips (loop) | `color` green/purple/orange, `frames` |
| `fireball` | Looping projectile | `size`, `frames` |
| `sword_slash` | 8-frame crescent slash | `color` azure/gold/crimson, `thickness` 0.5–1.6 |
| `ice_spear` | Round skill icon | `size`, `element` ice/lightning/poison |
| `potion` | Fantasy potion flask (item) | `size`, `frames`, `liquid` red/blue/green/purple |
| `chest` / `chest_open` | Treasure chest; 8-frame opening animation | `size` |
| `hero_shrine` | 96×96 Shrine of Heroes with animated braziers | `frames`, `banner` red/blue/green |

**Grid skills for tactics / dungeon games** (v0.6): width = `tiles × 32`; the **bottom `tiles×32` square is the ground
area** that covers the target cells, the space above is headroom for flames and pillars; the pivot is the cell centre.

| Builder | Output | Options |
|---|---|---|
| `lava_burn` | **Lava burn**: cracks glow → magma floods the cells → burning loop → cools to scorched rock. Tags cast / burn / fade | `tiles` 1–5, `color` lava/soulfire/acid, `phase` all/cast/burn/fade |
| `meteor` | Warning ring, flaming rock falls, fire-dome explosion, smoking crater | `tiles`, `color` fire/arcane/frost |
| `fire_pillar` | Rune circle → roaring column of fire (loop) → embers | `tiles` 1–3, `color` fire/azure/violet |
| `earth_spike` | Rock spikes burst up on every cell, dust ring, crumble | `tiles`, `color` earth/crystal/ice |
| `whirlpool` | Spiralling vortex with foam and spray (loop) | `tiles`, `frames`, `color` water/abyss/sand |
| `gale` | Tornado with dust ring and orbiting leaves (loop) | `tiles` 1–3, `frames`, `color` wind/sand/storm |
| `ice_field` | Frost spreads, crystal clusters, glints (loop), shatters | `tiles`, `color` ice/crystal |
| `holy_judgment` | Magic circle, pillar of light, cross flash, rising motes | `tiles`, `color` holy/sun/moon |
| `dark_vortex` | Curse field: rune ring, shadow tendrils, void core (loop) | `tiles`, `frames`, `color` dark/blood/void |
| `life_drain` | Curse sigil, essence spirals up into an orb that darts away | `tiles` 1–3, `color` blood/soul/mana |

**JRPG icons** (v0.6, 32 / 48 / 64 px, default 48, lit per pixel; optional rarity slot common … legendary):

| Builder | Kinds | Variants |
|---|---|---|
| `weapon_icon` | sword, katana, dagger, axe, spear, staff, bow, hammer | `material` tiers bronze (plain) → iron (fuller, flared guard) → mithril (runes, gems) → gold (ornate, wings) → dark (serrated, horns) — **different shapes**, not just colours |
| `armor_icon` | helmet, armor, shield, gauntlet, boots, cloak, ring, amulet | `material` tiers as above |
| `consumable_icon` | HP potion, MP ether, antidote, elixir, phoenix feather, scroll, bomb, onigiri | `grade` minor / normal / greater (different bottles and details) |
| `material_icon` | ore, ingot, gem, crystal, herb, mushroom, key, coin pouch | `color` × 6, each its own design (gem cuts, herbs, mushrooms, key bows …) |
| `skill_icon` | 18 skills (the 10 above + revive, curse, heal, barrier, haste, slash, thunder, poison) | `element` auto or any frame element |
| `status_icon` | 16×16 badges: ATK/DEF/SPD/MAG up & down, poison, burn, freeze, paralysis, sleep, petrify, curse, silence, blind, stun, regen, charm | — |

**UI kit** (v0.6, themes classic_blue / wood_gold / stone_iron / parchment, 9-slice friendly):

| Builder | Output |
|---|---|
| `ui_panel` | window, dialog (name plate + bobbing next-arrow), tooltip, title banner, tab (active / inactive) |
| `ui_button` | rect / square / round; frames normal / hover / pressed / disabled |
| `ui_bar` | HP / MP / EXP / stamina / ATB gauge, `fill` 0–1, `part` bar / frame / fill |
| `ui_frame` | portrait frame, item slot, skill slot (normal / selected / locked) |
| `ui_icon` | 20 menu icons (bag, equipment, skills, map, quest, shop, settings, save, home, mail, battle, auto, speed, confirm, close, back, gold, gem, stamina, cursor hand); `style` color / mono |

The rendered kit (PNGs, sprite strips + `meta.json`, GIFs, contact sheets) is in [deliverables/jrpg_pack](deliverables/jrpg_pack).

**Character kit** (v0.7, `character_kit`, group *Characters*): a 4-direction 64×64 base character with paper-doll
costumes drawn on top of every frame, so clothes, hair, headgear and weapons follow the animation.

| Preset | Head | Body | Weapon |
|---|---|---|---|
| `base` | — (plain Craftpix base; `base` = male / female) | — | sword |
| `knight` | steel helmet (rim, nose guard, cheek guards, ridge) | plate armour, pauldrons, red tabard, belt, red cape | steel sword |
| `mage` | purple wizard hat (brim, gold band, bent tip), long purple hair | blue robe with gold stars, red sash | staff with a blue orb; attack = **spell cast** |
| `ranger` | green hood (pointed tail, falls over the shoulders) | leather vest, belt, green cloak | short sword; **bow attack** |
| `priest` | white hood + mitre with a gold cross | white robe, gold stole, shoulder mantle | gold cross staff; attack = **spell cast** (holy gold) |
| `berserker` | horned helmet | fur pauldrons over leather | axe |
| `necromancer` | black hood, face in shadow, glowing green eyes | bone-spike collar, skull pauldrons, tattered dark robe and black cape | skull staff; attack = **spell cast** (green) |
| `skeleton` | skull (big dark sockets, glowing pupils, teeth, cracked cranium, pinched temples, narrow jaw) | see-through: the torso is a single spine pole with collarbone and pelvis bars, every limb one thin bone; stiff, jerky, slow movement | old iron sword + small wooden round shield with a metal band; **`Summon_Rise`** |

Options: `action` = the pack's 13 actions (Unarmed / Sword × Idle, Walk, Run, Hurt, Death, Sword Attack, Walk/Run
Attack) **+ `Bow_Attack`** (synthesised on the sword-attack body poses: nock → draw → release → follow-through; in the side
views the arms are re-drawn and the string is pulled by the draw hand) **+ `Cast_Spell`** (staff held upright: rune
circle → motes gather → staff raised, head glows → burst / bolt → recover; mage, priest and necromancer play it for
`Sword_Attack`) **+ `Summon_Rise`** (climbs out of the ground in a necromantic circle — meant for the skeleton);
`facing` front / left / right / rear; `base` auto / male / female. Layers: shadow, back, body, gear, front, flash —
the near-side weapon of a right-handed character is drawn over the face. Pivot = feet (32, 44); idle / walk / run loop.

> **The base art is not in this repo.** It is Craftpix's free *Base 4-Direction Male / Female Character* pack, whose
> licence allows use in games but not redistribution. Download both zips from craftpix.net, then
> `python scripts/setup_character_base.py <male.zip> <female.zip>` (unzips into the git-ignored `assets_local/`;
> or set `ARTSTUDIO_CHARKIT_DIR`). `python scripts/make_character_pack.py` exports every preset × action as sprite
> sheets (rows = front, side_left, side_right, back), GIF previews and `meta.json` into `assets_local/character_pack/`.

New assets don't need new code: an agent can write a call list and run `artstudio draw`. See
[docs/pixel-forge-guide.md](docs/pixel-forge-guide.md).

## Quick start

Requirements: **Python 3.10+**. Optional: **ffmpeg** (video import), **ComfyUI** (AI generation).

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\start.ps1      # creates .venv, installs, opens http://127.0.0.1:8870
```
```bash
# Linux / macOS
./start.sh                                                # --port 8870 --workspace DIR --comfy http://127.0.0.1:8188
```

Manual install: `python -m venv .venv`, then `.venv/bin/pip install -r requirements.txt`, then
`.venv/bin/python -m artstudio serve`.

## How to use

### In the web studio (http://127.0.0.1:8870)

The home page has three entry points, one per tool.

**🎬 Motion Studio** — a production line for a character's action frames:

1. **Character**: either upload **one reference image**, or **describe the character** and let Codex / ComfyUI draw
   4 candidates — pick one. The chosen image is locked as the reference every action must match.
2. **Actions**: **★ Core set** adds walk (8 frames), attack (8) and hit (4); other presets and one-line custom actions
   are available. Each action is drawn as one sheet in a fixed grid (8 frames → 4×2, 4 → 2×2).
3. **Prompts**: **✨ Write with Codex** looks at the reference and writes the description, poses and prompts; or use the
   built-in template. Everything is editable.
4. **Generate** (▶ Run pipeline): pick **Codex CLI** or **Local ComfyUI**; the actions run as a queue. Each sheet is cut
   into frames, scaled once to the **character height** (default 64 px), put on one ground line, snapped to the
   reference palette and cleaned. A sheet that fails the checks is **regenerated automatically** (default up to 2 times).
5. **Review & export**: play each action, **✎ Edit pixels** in the sprite editor, redo single frames, re-cut at another
   height, approve and export for Cocos Creator, Godot, Phaser/PixiJS or PNG/GIF.

**✎ Sprite editor** — click any pixel to see its colour and change it, delete it, or replace that colour in the frame or
the whole animation; pencil, eraser, picker, fill, line, rectangle, selection (move / copy / paste / flip), mirror, onion
skin, playback, frame duplicate / move / delete, undo / redo. Hand edits are saved as a patch layer, so re-processing
the action keeps them. Shortcuts: P B E I G L R M (tools), arrows + Enter / Delete (pixel), Ctrl+Z / Ctrl+S, , and . (frames).

#

**🔥 Pixel Forge** — pick a builder on the left, watch the live preview, adjust on the right:

| Section | Controls |
|---|---|
| Variant | the builder's own options (colour scheme, size, frames, thickness …) |
| Timing | speed 0.25×–3×, loop |
| Colours | edit any palette colour, or shift hue / saturation / brightness of the whole palette |
| Outline & glow | outline 0–3 px + colour, dithered glow 0–4 px + colour, flip, output scale 1×–4× |
| Save | save to the library, or save & export (PNG frames, sheet, GIF, JSON, Cocos, ZIP) |

Edits are stored with the asset and recorded as pixel-engine calls, so saved assets replay exactly and can be
reopened in the Forge ("Saved in this project").

**📥 Asset Import** — drop files, choose slicing / background / alignment, import.

Expert tools are under **More tools**: frame-level **Animation editor**, **Character details**, **Generation &
workflows** (ComfyUI) and **Pixel documents** (recipes, layers, cels).

### From the command line (JSON output, for scripts and agents)

```bash
python -m artstudio project create "My RPG" --id my-rpg
python -m artstudio builders                                       # list builders and animation templates
python -m artstudio procedural hero_shrine --project my-rpg --params '{"banner":"blue"}'
python -m artstudio procedural heal --project my-rpg --params '{"color":"gold"}' --edits '{"speed":1.5,"outline":1,"glow":2}'
python -m artstudio procedural lava_burn --project my-rpg --params '{"tiles":3,"phase":"burn"}'     # grid skill, burning loop only
python -m artstudio procedural weapon_icon --project my-rpg --params '{"kind":"katana","material":"mithril","frame":"epic"}'
python scripts/make_jrpg_pack.py --out deliverables/jrpg_pack                                     # render the whole JRPG kit
# Motion Studio (character animation)
python -m artstudio animate new --project my-rpg --name "Fire Knight" --image knight.png --view side
#   …or describe it: 4 candidates, then lock one
python -m artstudio animate describe --project my-rpg --name "Fire Knight" --description "chibi knight, red cape, big sword" --provider codex
python -m artstudio animate pick --project my-rpg --character <cid> --candidate <candidate-id>
python -m artstudio animate core --project my-rpg --character <cid>                       # walk + attack + hit
python -m artstudio animate add --project my-rpg --character <cid> --preset attack
python -m artstudio animate add --project my-rpg --character <cid> --name "Spin slash" --description "spins once with the sword out" --frames 6
python -m artstudio animate prompts --project my-rpg --character <cid> --method codex      # or --method template
python -m artstudio animate generate --project my-rpg --character <cid> --provider codex --height 64 --retries 2   # or comfyui
python -m artstudio draw my_gem.jsonl --project my-rpg --name "Red Gem" --type icon
python -m artstudio import hero_walk.png --project my-rpg --opts '{"slicing":{"method":"grid","cols":8,"rows":1},"background":{"method":"auto"}}'
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --params '{"checkpoint":"<file>.safetensors"}'
python -m artstudio export --project my-rpg --assets <ids…> --formats atlas cocos gif json zip
```

- CLI messages in Chinese: `--lang zh-CN` or `ARTSTUDIO_LANG=zh-CN`.
- Config: `studio.config.example.json`, `.env.example`. Codex CLI: install, `codex login`, and it is found on PATH
  (or set `codex_bin`).
- Windows + ComfyUI setup: [docs/deployment-windows.md](docs/deployment-windows.md).

### Bundled ComfyUI workflow templates

`workflows/comfyui/`: text-to-image, image-to-image, character reference, pose keyframe, inpaint, SVD image-to-video,
background removal (rembg). They are **unverified** until tested on a real ComfyUI server (Stage B). You can import
your own workflows from the UI or CLI.

## Based on

This repo is self-contained: it holds no other project's git checkout. It builds on two MIT projects:

| Upstream | What we took | Where it lives now |
|---|---|---|
| **[Atelier](https://github.com/marmikshah/atelier)** (Marmik Shah), commit `8ac6adf` | Tool-call format, document / recipe layout, drawing semantics | `artstudio/engine`: our own Python re-implementation (no Rust). Atelier recipes replay **pixel-identical**. |
| **[Pixel Atelier](https://github.com/jinxingtaire/pixel-atelier)** (Pixel Character Pipeline contributors), commit `15d199f` | Sprite pipeline, Chinese sheet prompts, Codex client, knight sample | `artstudio/pipeline/spritepipe.py`, `artstudio/prompts_zh_sheet.py`, `artstudio/providers/codex_rpc.py`, `samples/knight/`. Rewritten for UTF-8 on GBK/cp936 systems. |

AI generation talks to the **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** server API. No ComfyUI code is
included. Licences and derived-file list: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Verification status

- ✅ **Offline (Stage A):** 107 automated tests (5 character-kit tests need the local Craftpix pack and skip without it) (engine, pipeline, encoding, action plans, ComfyUI mock, Codex test double, server,
  CLI), Playwright UI test of the whole guided flow in English and Chinese, proof-of-concept build. Details in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).
- 🧪 **AI generation is mock-tested only**: ComfyUI against `mock_comfyui/`, Codex against a test double
  (`tests/fake_codex.py`). Mock output is labelled TEST FIXTURE and is not AI art. The real Codex CLI has not been run here.
- ⛔ **Stage B (real ComfyUI inference) has not been run.** Run `scripts/production_smoke_test.py` on the ComfyUI PC.

## Layout

```
artstudio/    app: engine (Pixel Forge), procedural (builders), pipeline, providers, processing, qa, export, server, web, schema
samples/      knight sample art (demonstration only, see samples/knight/NOTICE.md)
mock_comfyui/ offline ComfyUI API simulator (labelled test fixtures)
workflows/    ComfyUI templates · skills/ agent skills · examples/ Cocos Creator TS, Godot script
demo/         proof-of-concept builder · deliverables/ curated outputs · docs/ · scripts/ · tests/
```

## For contributors and agents

- Rules and gotchas: [AGENTS.md](AGENTS.md). Requirements: [SPECIFICATION.md](SPECIFICATION.md).
- Run tests: `python scripts/run_tests.py`.
- Release history: [CHANGELOG.md](CHANGELOG.md). Current version: [VERSION](VERSION).
