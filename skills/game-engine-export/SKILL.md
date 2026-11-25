---
name: game-engine-export
description: Export animations to Cocos Creator 3.x (priority), Phaser/PixiJS, Godot and Unity-ready files.
---

# Game Engine Export

Export animations to Cocos Creator 3.x (priority), Phaser/PixiJS, Godot and Unity-ready files.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Approved animation assets; character id (for direction map/mirroring); formats; preview scale; padding/extrude.

## Recommended workflow
1. `export --project P --assets A1 A2 ... --character C --formats frames sheet atlas gif apng json cocos phaser godot zip`.
2. Check the export QA (missing files, atlas coordinates) and `contains_test_fixtures` (must be false for production).
3. Cocos: copy `cocos/<name>.plist/.png/.anim.json` into assets; add examples/cocos-creator/*.ts; set the JsonAsset and SpriteAtlas on DirectionalSpriteAnimator.
4. Phaser 3: `this.load.atlas(key, '<name>_atlas.png', '<name>_atlas.json')`; PixiJS: `Assets.load('<name>_atlas.json')` (TexturePacker JSON-hash, `animations` included).
5. Godot 4: run examples/godot/build_sprite_frames.gd. Unity: read `<name>.anim.json` + atlas rects.

## Tool-selection rules
Export Studio / CLI; QA check_export.

## Prompt templates
n/a.

## Quality criteria
All files present; atlas rects inside the texture; pivots in px and normalised (y-up); event times = cumulative durations; directional map complete.

## Common failure modes
Trimmed frames without offsets (jumping sprites); per-engine pivot convention mix-ups; exporting fixtures.

## Recovery strategies
Use the provided `trim_offset`/`sourceColorRect`; set Sprite.trim=false + RAW size in Cocos; re-export without fixture assets.

## Output specification
Export folder with frames/, sheets/, <name>_atlas.png/.json, cocos/, previews/ (GIF/APNG/composite), <name>.anim.json, export_manifest.json, zip.
