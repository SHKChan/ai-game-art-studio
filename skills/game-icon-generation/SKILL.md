---
name: game-icon-generation
description: Produce inventory/equipment/UI icons (potions, chests, weapons, armour) as layered Atelier documents at a fixed grid size.
---

# Game Icon Generation

Produce inventory/equipment/UI icons (potions, chests, weapons, armour) as layered Atelier documents at a fixed grid size.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Atelier tools are reached through the `atelier` provider — never re-implement drawing in Python image code.

## Required inputs
Icon list; size (16/24/32/48/64); shared palette; style rules (outline colour, light direction top-left); background policy (transparent).

## Recommended workflow
1. Freeze one palette for the whole icon set (doc_palette op=set) — reuse it across documents.
2. Use builders `potion`, `chest` (params: size, liquid colour) or author calls per icon: outline layer, base, shading, highlight layers.
3. Same light direction and outline weight on every icon; check side-by-side with contact sheets.
4. Run `qa`; export with `export --formats atlas json cocos phaser` so all icons share one atlas.

## Tool-selection rules
Atelier only. External/AI art only if the user supplies it (import → pixel mode → palette snap).

## Prompt templates
'64x64 fantasy health potion: round flask, red liquid with sphere shading, cork, gold tie, white specular arc top-left, 1px dark outline, transparent background.'

## Quality criteria
Readable at native size; silhouettes distinct between icons; ≤ palette colours; centred with ≥1px margin; consistent light/outline across set.

## Common failure modes
Different light directions across icons; muddy mid-tones; icon touching edges; inconsistent sizes in one atlas.

## Recovery strategies
Re-snap to the set palette (doc_palette op=snap); move/clear regions (doc_region); rescale only by integer factors (doc_rescale).

## Output specification
One asset per icon (1 frame), shared atlas + TexturePacker JSON + Cocos plist from Export Studio.
