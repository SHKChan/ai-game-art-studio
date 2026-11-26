---
name: procedural-builder-authoring
description: Add a new Pixel Forge asset type (item, icon, skill effect, tile) as a call list or a reusable builder, and verify it.
---

# Procedural Builder Authoring

Full reference: `docs/pixel-forge-guide.md`. Worked example: `artstudio/procedural/ice_spear.py`.

## Required inputs
Asset brief (subject, size, frame count, timing); palette or colour intent; variants to support (params); target asset type.

## Recommended workflow
1. Decide the route: one-off → JSONL call list + `python -m artstudio draw`; repeatable → builder module.
2. Lock the palette (`doc_palette op=set`), plan layers (one per moving/glowing/recolourable part).
3. Builder: compute pixels with `raster.Grid` (shapes, `ramp_pick` shading, `vnoise`), paint with `DocBuilder.paint`.
4. Register the builder in `artstudio/procedural/__init__.py`; add a Chinese description to `artstudio/web/i18n.js`.
5. Render, contact-sheet, look, fix one region at a time, re-render.
6. QA + replay check + add to `tests/test_integration.py`.

## Tool-selection rules
Pixel Forge tools only (doc_paint_grid with palette indices preferred). No external image libraries for final pixels.
Complex characters → Motion Studio/C instead.

## Prompt templates
The builder's params are the prompt. Brief format: "Skill icon 32x32: diagonal ice spear, pointed head, lit from top-left, round dark frame, 3 sparkle pixels, 9-colour palette, transparent outside the frame."

## Quality criteria
Reads at 1× in silhouette; consistent light direction; ≥2 layers; no edge contact; QA `passed`; replay pixel-identical; visually reviewed.

## Common failure modes
Blob-like heads (too much highlight), parts touching the frame, alpha-based fades, shading noise from dithering everywhere.

## Recovery strategies
Reduce the light ramp share, shrink geometry to leave margin, replace alpha with pixel changes, limit dithering to band edges.

## Output specification
`artstudio/procedural/<name>.py` with DESCRIPTION/PARAMS/ASSET_TYPE/build(); test entry; an asset with `procedural.doc_id` + `source/doc.recipe`.
