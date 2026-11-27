# Asset packs and search tags

The studio can import third-party pixel-art packs that you have downloaded. The art stays on your computer in
`assets_local/packs/`, which git ignores. Every imported item becomes a normal asset (frames, pivot, timing,
QA, export) with **English search tags**.

## Supported packs

| Pack id | Pack | Items | Licence |
|---|---|---|---|
| `tiny-rpg` | Tiny RPG Character Asset Pack 01 + 02 (Zerie, free): Soldier, Orc, Demon_A, Blood Monster_A | One animation per character action (Idle, Walk, Attack01–03, Hurt, Death) plus the soldier's arrow. 100×100 cells, side view facing right. Each character gets a side-view character record. | Use in your games; **do not redistribute** |
| `craftpix-dungeon` | Craftpix *Free 2D Top-Down Pixel Dungeon Asset Pack* | 8 tilesets (16 px grid recorded on the asset), 15 animated props (torches, braziers, candles, 4 doors/gates, chests, lever, spike trap), and the sample map rendered from `Dungeon1.tmx` with animated water | Craftpix free licence: use in games; **do not redistribute** |
| `pvfx-foundry` | PVFX Foundry 1.x (CC0) | 253 effects: elemental spells, melee skills, hits, explosions, status auras, projectiles, ambient loops, UI feedback. Options: `tier` `lit` (soft glow) or `strict` (binary alpha), `variants` (81 recolours) | CC0, free to redistribute |

## Install

```powershell
python scripts/setup_asset_packs.py "Tiny RPG Character Asset Pack 01 v2.0 -Free Soldier&Orc.zip" `
    "Tiny RPG Character Asset Pack 02 v1.01-Free Demon_A&Blood Monster_A.zip" `
    free-2d-top-down-pixel-dungeon-asset-pack.zip pvfx-foundry-thirteen-spritesheets.zip
```

The script works out which pack each ZIP is from its contents, so the file names don't matter. It extracts only what
the importer needs: PNG strips, tilesets, the `.tmx` map, licences, and PVFX grid sheets with their manifests. Packs
go to `assets_local/packs/<pack-id>/`. To keep them somewhere else, set `ARTSTUDIO_PACKS_DIR`.

## Import

- **Web studio** → **Asset Import** → **Asset packs**:
  1. Choose a pack.
  2. Click tag chips to filter. An item must have every selected tag.
  3. Tick items, or use **Import all shown**.

  Items that are already in the project are skipped.
- **CLI**:

```bash
python -m artstudio packs list
python -m artstudio packs items  --pack pvfx-foundry --tag spell --tag ice
python -m artstudio packs import --project my-rpg --pack tiny-rpg                 # 4 characters, 26 animations
python -m artstudio packs import --project my-rpg --pack craftpix-dungeon --tag torch
python -m artstudio packs import --project my-rpg --pack pvfx-foundry --tag fire --options '{"tier":"strict"}'
```

What the importer keeps:

- **Cell layout**: the pack's own cells stay as they are (`anchor: source`, padding 0). All actions of a character
  share one canvas and one pivot at the feet, so they line up in an engine.
- **Timing**: per-frame durations come from the pack's manifests and Tiled data.
- **Loops**: idle, walk and fire loop; death and doors hold their last frame; the spike trap ping-pongs.
- **Soft alpha**: kept for shadows and `lit` glows. QA notes these as information, not as warnings.
- **Blank frames**: pauses inside effects are kept. QA reports them as information.

## Tags

- **English only**: tags are lower-case ASCII words joined with `-`. Any tag with other characters is dropped when the
  asset is saved, so search behaves the same in both UI languages.
- **Where to search**:
  - **Library**: tag chips plus a search box. Every word must match the name, id or tags.
  - **Pixel Forge**: the gallery search matches builder names and tags.
  - **Pack browser**: tag chips, as described under Import.

Main vocabulary:

| Area | Tags |
|---|---|
| Scenes / scenery | `scenery`, `scene`, `environment`, `dungeon`, `top-down`, `tileset`, `wall`, `floor`, `water`, `prop`, `torch`, `door`, `chest`, `trap`, `map` |
| Characters | `character`, `hero`, `human`, `humanoid`, `side-view`, `four-direction`, class words (`knight`, `mage`, `archer` …) |
| Monsters | `monster`, `enemy`, `undead`, `orc`, `demon`, `skeleton`, `necromancer`, `beast`, `dungeon` |
| Skills / spells | `skill`, `spell`, `magic`, `effect`, element (`fire`, `ice`, `lightning`, `holy`, `shadow`/`dark`, `water`, `wind`, `earth`, `poison`, `arcane`), role (`attack`, `aoe`, `projectile`, `buff`, `debuff`, `heal`, `support`, `control`, `dot`), shape (`grid`, `ground`, `nova`, `beam`, `slash`) |
| Actions | `action:idle`, `action:walk`, `action:attack01` … (`idle`, `walk`, `attack`, `hurt`, `death`) |
| Source | `procedural` + builder id, `pack` + pack id, `tiny-rpg`, `craftpix`, `pvfx` |

Assets saved before 0.9 get the new tags with `python -m artstudio retag --project <id>`. It only adds tags, so tags
you added by hand stay.

Builder tags are defined in `artstudio/tagging.py` (`BUILDER_TAGS`, `PRESET_TAGS`). Each saved builder asset gets
them. In the character kit, the `necromancer` and `skeleton` presets are tagged `monster`/`enemy`/`undead`, and the
other presets are tagged `hero`. Pack tags are defined in each pack module under `artstudio/packs/`.

## Adding a pack

Add a module to `artstudio/packs/` with these names:

- `ID`, `DIRNAME`, `TITLE`, `DESCRIPTION`, `LICENSE_NOTE`, `REDISTRIBUTABLE`, `OPTIONS`
- `available(root)`
- `items(root, options)`: each item is `{id, name, type, group, tags, frames, …}`
- `load(item, root, options)`: returns `{frames: [(RGBA, ms)], canvas, pivot, loop, hold_last?, ping_pong?, full_bleed?, source_file, source_rects?, binary_alpha?, extra?}`

Then register the module in `PACKS`, and teach `scripts/setup_asset_packs.py` how to recognise its ZIP.
